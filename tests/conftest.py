import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


def pytest_configure():
    """Add the src directory to the Python path before any tests run."""
    import sys
    from pathlib import Path

    # Add src directory to Python path
    src_dir = Path(__file__).parent.parent / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


class SystemExitCalled(Exception):
    """Custom exception to simulate sys.exit behavior in tests"""

    def __init__(self, code):
        self.code = code
        super().__init__(f"sys.exit({code}) called")


@pytest.fixture
def mock_system_exit(mocker):
    """
    Fixture to mock sys.exit for testing exit behavior.

    Usage:
        def test_exit_behavior(mock_system_exit):
            with pytest.raises(SystemExitCalled) as exc_info:
                function_that_calls_sys_exit()
            assert exc_info.value.code == 1
    """

    def side_effect(code):
        raise SystemExitCalled(code)

    return mocker.patch("sys.exit", side_effect=side_effect)


@pytest.fixture
def mock_integration_setup(mocker):
    """
    Fixture to set up common mocking for integration tests.

    Provides mocked versions of command execution, command building, print functions,
    and other core components for comprehensive integration testing.

    Usage:
        def test_integration_scenario(mock_integration_setup):
            # Access mocked components
            mock_run = mock_integration_setup["run_nonblocking"]
            mock_build = mock_integration_setup["build_command"]
            mock_print = mock_integration_setup["print"]
            mock_profile_merge = mock_integration_setup["merge_arguments"]
            mock_config_load = mock_integration_setup["load_config"]

            # Test your integration scenario
            result = function_under_test()

            # Verify mocks were called correctly
            mock_run.assert_called_once()
            mock_build.assert_called()
    """
    mock_run_nonblocking = mocker.patch(
        "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
    )
    mock_build = mocker.patch(
        "nscb.command_executor.CommandExecutor.build_command",
        side_effect=lambda x: "; ".join(x),
    )
    mock_print = mocker.patch("builtins.print")
    mock_profile_merge = mocker.patch(
        "nscb.profile_manager.ProfileManager.merge_arguments"
    )
    mock_config_load = mocker.patch(
        "nscb.config_manager.ConfigManager.load_config"
    )

    return {
        "run_nonblocking": mock_run_nonblocking,
        "build_command": mock_build,
        "print": mock_print,
        "merge_arguments": mock_profile_merge,
        "load_config": mock_config_load,
    }


@pytest.fixture
def temp_config_file():
    """Fixture for temporary config files."""
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / "nscb.conf"
    yield config_path
    # Cleanup after test
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_config_with_content():
    """Fixture for temporary config files with various content types."""

    def _create_config(content):
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / "nscb.conf"
        with open(config_path, "w") as f:
            f.write(content)
        return config_path

    yield _create_config


@pytest.fixture
def mock_gamescope(mocker):
    """Fixture for mock gamescope executable."""
    return mocker.patch(
        "nscb.system_detector.SystemDetector.find_executable", return_value=True
    )


@pytest.fixture
def mock_config_file(mocker, temp_config_file):
    """Fixture that creates a config file and mocks find_config_file to return it."""

    def _setup_config(content):
        with open(temp_config_file, "w") as f:
            f.write(content)
        return mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file",
            return_value=temp_config_file,
        )

    return _setup_config


@pytest.fixture
def mock_system_detection_scenarios(mocker):
    """
    Fixture for testing system detection scenarios.

    Provides predefined system detection configurations for testing.

    Usage:
        def test_system_detection(mock_system_detection_scenarios):
            scenarios = mock_system_detection_scenarios
            
            # Test gamescope active detection
            scenarios["gamescope_active"]()
            assert is_gamescope_active() == True
            
            # Test gamescope inactive detection
            scenarios["gamescope_inactive"]()
            assert is_gamescope_active() == False
    """
    
    def _gamescope_active():
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=True
        )
    
    def _gamescope_inactive():
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False
        )
    
    def _executable_found():
        mocker.patch(
            "nscb.system_detector.SystemDetector.find_executable",
            return_value=True
        )
    
    def _executable_not_found():
        mocker.patch(
            "nscb.system_detector.SystemDetector.find_executable",
            return_value=False
        )
    
    return {
        "gamescope_active": _gamescope_active,
        "gamescope_inactive": _gamescope_inactive,
        "executable_found": _executable_found,
        "executable_not_found": _executable_not_found
    }


@pytest.fixture
def mock_execution_scenarios(mocker):
    """
    Fixture for testing execution scenarios.

    Provides predefined execution configurations and expected command building results.

    Usage:
        def test_execution_scenarios(mock_execution_scenarios):
            scenarios = mock_execution_scenarios
            
            # Test basic execution
            args = scenarios["basic"]["args"]
            expected_cmd = scenarios["basic"]["expected_command"]
            
            result = build_command(args)
            assert result == expected_cmd
    """
    return {
        "basic": {
            "args": ["gamescope", "-f", "-W", "1920", "--", "/bin/game"],
            "expected_command": "gamescope -f -W 1920 -- /bin/game"
        },
        "with_ld_preload": {
            "args": ["env", "-u", "LD_PRELOAD", "gamescope", "-f", "--", "env", "LD_PRELOAD=/path/to/lib.so", "/bin/game"],
            "expected_command": "env -u LD_PRELOAD gamescope -f -- env LD_PRELOAD=/path/to/lib.so /bin/game"
        },
        "with_pre_post": {
            "args": ["echo 'pre'", "gamescope", "-f", "--", "/bin/game", "echo 'post'"],
            "expected_command": "echo 'pre'; gamescope -f -- /bin/game; echo 'post'"
        },
        "complex": {
            "args": [
                "echo 'pre'",
                "env", "-u", "LD_PRELOAD", "gamescope", "-f", "-W", "1920",
                "--", "env", "DISPLAY=:0", "LD_PRELOAD=/path/to/lib.so", "/bin/game",
                "echo 'post'"
            ],
            "expected_command": (
                "echo 'pre'; env -u LD_PRELOAD gamescope -f -W 1920 -- "
                "env DISPLAY=:0 LD_PRELOAD=/path/to/lib.so /bin/game; echo 'post'"
            )
        }
    }


@pytest.fixture
def mock_is_gamescope_active(mocker):
    """Fixture to mock is_gamescope_active function."""
    return mocker.patch("nscb.system_detector.SystemDetector.is_gamescope_active")


@pytest.fixture
def mock_env_commands(mocker):
    """Fixture to mock environment commands."""

    def _setup_env(pre="", post=""):
        return mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=(pre, post),
        )

    return _setup_env


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """
    Fixture to set up common environment variable scenarios.

    Provides predefined environment variable configurations for testing.

    Usage:
        def test_env_scenarios(mock_environment_variables):
            # Get predefined scenarios
            scenarios = mock_environment_variables
            
            # Use in tests
            for scenario_name, env_vars in scenarios.items():
                for var, value in env_vars.items():
                    monkeypatch.setenv(var, value)
    """
    return {
        "basic": {"NSCB_DEBUG": "1", "DISPLAY": ":0"},
        "ld_preload": {"LD_PRELOAD": "/path/to/lib.so"},
        "gamescope_active": {"XDG_CURRENT_DESKTOP": "gamescope"},
        "faugus_launcher": {"FAUGUS_LOG": "1"},
        "pre_post_commands": {
            "NSCB_PRE_CMD": "echo 'pre command'",
            "NSCB_POST_CMD": "echo 'post command'"
        },
        "complex": {
            "NSCB_DEBUG": "1",
            "LD_PRELOAD": "/path/to/lib.so",
            "XDG_CURRENT_DESKTOP": "gamescope",
            "NSCB_PRE_CMD": "echo 'pre'",
            "NSCB_POST_CMD": "echo 'post'"
        }
    }


@pytest.fixture
def mock_ld_preload_scenarios(monkeypatch):
    """
    Fixture for testing LD_PRELOAD handling scenarios.

    Provides different LD_PRELOAD configurations for comprehensive testing.

    Usage:
        def test_ld_preload_handling(mock_ld_preload_scenarios):
            # Test with LD_PRELOAD set
            mock_ld_preload_scenarios["with_ld_preload"]()
            
            # Test with LD_PRELOAD disabled
            mock_ld_preload_scenarios["disabled"]()
    """
    
    def _with_ld_preload():
        monkeypatch.setenv("LD_PRELOAD", "/usr/lib/libtest.so")
        monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
        monkeypatch.delenv("FAUGUS_LOG", raising=False)
    
    def _disabled_by_env():
        monkeypatch.setenv("LD_PRELOAD", "/usr/lib/libtest.so")
        monkeypatch.setenv("NSCB_DISABLE_LD_PRELOAD_WRAP", "1")
        monkeypatch.delenv("FAUGUS_LOG", raising=False)
    
    def _disabled_by_faugus():
        monkeypatch.setenv("LD_PRELOAD", "/usr/lib/libtest.so")
        monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
        monkeypatch.setenv("FAUGUS_LOG", "1")
    
    def _no_ld_preload():
        monkeypatch.delenv("LD_PRELOAD", raising=False)
        monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
        monkeypatch.delenv("FAUGUS_LOG", raising=False)
    
    return {
        "with_ld_preload": _with_ld_preload,
        "disabled_by_env": _disabled_by_env,
        "disabled_by_faugus": _disabled_by_faugus,
        "no_ld_preload": _no_ld_preload
    }


@pytest.fixture
def complex_args_scenario():
    """
    Fixture for complex argument scenarios.

    Provides predefined argument patterns for testing various scenarios including:
    - Simple profile arguments
    - Conflicting flag scenarios
    - Mixed arguments with separators
    - Edge cases (empty args, positionals only)

    Usage:
        def test_complex_scenarios(complex_args_scenario):
            scenarios = complex_args_scenario
            # Test simple profile
            result = function_under_test(scenarios["simple_profile"])
            assert result == expected_simple_result

            # Test conflicting profile
            result = function_under_test(scenarios["conflicting_profile"])
            assert result == expected_conflict_result
    """
    return {
        "simple_profile": ["-f", "-W", "1920", "-H", "1080"],
        "conflicting_profile": ["--borderless", "-W", "2560"],
        "mixed_args": ["-f", "--mangoapp", "app.exe", "--", "game.exe"],
        "empty_args": [],
        "only_positionals": ["app.exe", "arg1", "arg2"],
        "fullscreen_vs_borderless": ["-f", "--borderless", "-W", "1920"],
        "multiple_profiles": ["-p", "profile1", "-p", "profile2", "--", "game.exe"],
        "override_scenario": [
            "-p",
            "base",
            "-W",
            "3840",
            "-H",
            "2160",
            "--",
            "game.exe",
        ],
    }


@pytest.fixture
def profile_scenarios():
    """
    Fixture for profile-based testing scenarios.

    Provides predefined profile configurations and their expected merge results.

    Usage:
        def test_profile_merging(profile_scenarios):
            scenarios = profile_scenarios
            
            # Test basic profile merge
            profile_args = scenarios["basic"]["profiles"]
            override_args = scenarios["basic"]["overrides"]
            expected = scenarios["basic"]["expected"]
            
            result = merge_arguments(profile_args, override_args)
            assert result == expected
    """
    return {
        "basic": {
            "profiles": ["-f", "-W", "1920", "-H", "1080"],
            "overrides": ["-W", "3840"],
            "expected": ["-f", "-W", "3840", "-H", "1080"]
        },
        "conflict_resolution": {
            "profiles": ["-f", "-W", "1920"],
            "overrides": ["--borderless", "-W", "2560"],
            "expected": ["--borderless", "-W", "2560"]
        },
        "multiple_profiles": {
            "profiles": [
                ["-f", "-W", "1920"],
                ["-H", "1080", "--framerate-limit", "60"]
            ],
            "overrides": ["--framerate-limit", "120"],
            "expected": ["-f", "-W", "1920", "-H", "1080", "--framerate-limit", "120"]
        },
        "empty_profile": {
            "profiles": [],
            "overrides": ["-f", "-W", "1920"],
            "expected": ["-f", "-W", "1920"]
        },
        "empty_override": {
            "profiles": ["-f", "-W", "1920"],
            "overrides": [],
            "expected": ["-f", "-W", "1920"]
        }
    }


@pytest.fixture
def config_scenarios():
    """
    Fixture for configuration file testing scenarios.

    Provides predefined configuration content and expected parsing results.

    Usage:
        def test_config_parsing(config_scenarios):
            scenarios = config_scenarios
            
            # Test basic config parsing
            config_content = scenarios["basic"]["content"]
            expected_profiles = scenarios["basic"]["expected_profiles"]
            expected_exports = scenarios["basic"]["expected_exports"]
            
            result = load_config(config_content)
            assert result.profiles == expected_profiles
            assert result.exports == expected_exports
    """
    return {
        "basic": {
            "content": "gaming=-f -W 1920 -H 1080\nstreaming=--borderless -W 1280 -H 720\n",
            "expected_profiles": {
                "gaming": "-f -W 1920 -H 1080",
                "streaming": "--borderless -W 1280 -H 720"
            },
            "expected_exports": {}
        },
        "with_exports": {
            "content": "gaming=-f -W 1920 -H 1080\nexport DISPLAY=:0\nexport MANGOHUD=1\n",
            "expected_profiles": {
                "gaming": "-f -W 1920 -H 1080"
            },
            "expected_exports": {
                "DISPLAY": ":0",
                "MANGOHUD": "1"
            }
        },
        "complex": {
            "content": "# This is a comment\ngaming=-f -W 1920 -H 1080\nstreaming=--borderless -W 1280 -H 720\nportable=\"--fsr-sharpness 5 --framerate-limit 60\"\nexport DISPLAY=:0\nexport MANGOHUD=1\nexport CUSTOM_VAR=\"value with spaces\"\n",
            "expected_profiles": {
                "gaming": "-f -W 1920 -H 1080",
                "streaming": "--borderless -W 1280 -H 720",
                "portable": "--fsr-sharpness 5 --framerate-limit 60"
            },
            "expected_exports": {
                "DISPLAY": ":0",
                "MANGOHUD": "1",
                "CUSTOM_VAR": "value with spaces"
            }
        }
    }


@pytest.fixture
def error_simulation():
    """
    Fixture for error simulation.

    Provides common error objects for testing error handling scenarios.

    Usage:
        def test_error_handling(error_simulation):
            # Test permission error handling
            with pytest.raises(PermissionError):
                raise error_simulation["permission_error"]

            # Test file not found error handling
            with pytest.raises(FileNotFoundError):
                raise error_simulation["file_not_found"]
    """
    return {
        "permission_error": PermissionError("Permission denied"),
        "file_not_found": FileNotFoundError("File not found"),
        "value_error": ValueError("Invalid value"),
        "key_error": KeyError("Missing key"),
        "config_not_found": Exception("Config file not found"),
        "profile_not_found": Exception("Profile not found"),
        "executable_not_found": Exception("Executable not found"),
        "invalid_argument": ValueError("Invalid argument format"),
    }


@pytest.fixture
def mock_subprocess_success(mocker):
    """
    Fixture for mocking successful subprocess operations.

    Provides a mocked subprocess that returns success status.

    Usage:
        def test_successful_execution(mock_subprocess_success):
            # The subprocess is already mocked to return success
            result = function_that_runs_subprocess()
            assert result == 0
    """
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_process.stderr = Mock()
    mock_process.wait.return_value = 0

    mocker.patch.object(
        mock_process.stdout, "readline", side_effect=["success output\n", ""]
    )
    mocker.patch.object(mock_process.stderr, "readline", side_effect=["", ""])

    mock_selector = Mock()
    mock_selector.get_map.return_value = [Mock()]
    mock_selector.get_map.return_value = []
    mock_selector.select.return_value = [(Mock(fileobj=mock_process.stdout), None)]

    mocker.patch("subprocess.Popen", return_value=mock_process)
    mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

    return mock_process


@pytest.fixture
def mock_subprocess_failure(mocker):
    """
    Fixture for mocking failed subprocess operations.

    Provides a mocked subprocess that returns failure status.

    Usage:
        def test_failed_execution(mock_subprocess_failure):
            # The subprocess is already mocked to return failure
            result = function_that_runs_subprocess()
            assert result == 1
    """
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_process.stderr = Mock()
    mock_process.wait.return_value = 1

    mocker.patch.object(mock_process.stdout, "readline", side_effect=["", ""])
    mocker.patch.object(
        mock_process.stderr, "readline", side_effect=["error output\n", ""]
    )

    mock_selector = Mock()
    mock_selector.get_map.return_value = [Mock()]
    mock_selector.get_map.return_value = []
    mock_selector.select.return_value = [(Mock(fileobj=mock_process.stderr), None)]

    mocker.patch("subprocess.Popen", return_value=mock_process)
    mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

    return mock_process


@pytest.fixture
def test_config_content():
    """
    Fixture providing standard test configuration content.

    Provides predefined configuration content for testing config parsing.

    Usage:
        def test_config_parsing(test_config_content):
            config_text = test_config_content["basic"]
            # Test config parsing with basic content
    """
    return {
        "basic": """gaming=-f -W 1920 -H 1080
streaming=--borderless -W 1280 -H 720
""",
        "with_exports": """gaming=-f -W 1920 -H 1080
export DISPLAY=:0
export MANGOHUD=1
""",
        "complex": """# This is a comment
gaming=-f -W 1920 -H 1080
streaming=--borderless -W 1280 -H 720
portable="--fsr-sharpness 5 --framerate-limit 60"
export DISPLAY=:0
export MANGOHUD=1
export CUSTOM_VAR="value with spaces"
""",
        "empty": "",
        "invalid": "invalid-line-without-equals\nanother-invalid",
    }


@pytest.fixture
def mock_subprocess(mocker):
    """Fixture to mock subprocess operations."""
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_process.stderr = Mock()
    mock_process.wait.return_value = 0

    mocker.patch.object(
        mock_process.stdout, "readline", side_effect=["test output\n", ""]
    )
    mocker.patch.object(
        mock_process.stderr, "readline", side_effect=["error output\n", ""]
    )

    mock_selector = Mock()
    mock_selector.get_map.return_value = [Mock()]
    mock_selector.get_map.return_value = []
    mock_selector.select.return_value = [(Mock(fileobj=mock_process.stdout), None)]

    mocker.patch("subprocess.Popen", return_value=mock_process)
    mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

    return mock_process


@pytest.fixture
def mock_application_workflow(mocker, temp_config_file):
    """
    Fixture for comprehensive application workflow testing.

    Sets up a complete mock environment for testing the full application workflow
    including configuration loading, profile merging, and command execution.

    Usage:
        def test_full_workflow(mock_application_workflow):
            # Setup test configuration
            config_content = "gaming=-f -W 1920 -H 1080\n"
            config_path = mock_application_workflow.setup_config(config_content)
            
            # Mock system detection
            mock_application_workflow.mock_gamescope_inactive()
            
            # Test application execution
            app = Application()
            result = app.run(["-p", "gaming", "--", "/bin/test_game"])
            
            # Verify execution
            assert result == 0
            mock_application_workflow.verify_execution()
    """
    
    class ApplicationWorkflowMock:
        def __init__(self):
            self.config_path = temp_config_file
            self.mock_gamescope = mocker.patch(
                "nscb.system_detector.SystemDetector.find_executable", return_value=True
            )
            self.mock_is_active = mocker.patch(
                "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=False
            )
            self.mock_run = mocker.patch(
                "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
            )
            self.mock_build = mocker.patch(
                "nscb.command_executor.CommandExecutor.build_command",
                side_effect=lambda x: "; ".join(x)
            )
            self.mock_find_config = mocker.patch(
                "nscb.config_manager.ConfigManager.find_config_file",
                return_value=self.config_path
            )
        
        def setup_config(self, content):
            """Setup test configuration file."""
            with open(self.config_path, "w") as f:
                f.write(content)
            return self.config_path
        
        def mock_gamescope_active(self):
            """Mock gamescope as active."""
            self.mock_is_active.return_value = True
        
        def mock_gamescope_inactive(self):
            """Mock gamescope as inactive."""
            self.mock_is_active.return_value = False
        
        def mock_execution_success(self):
            """Mock successful execution."""
            self.mock_run.return_value = 0
        
        def mock_execution_failure(self):
            """Mock failed execution."""
            self.mock_run.return_value = 1
        
        def verify_execution(self):
            """Verify that execution was attempted."""
            self.mock_run.assert_called_once()
            self.mock_build.assert_called()
        
        def verify_config_loading(self):
            """Verify that config loading was attempted."""
            self.mock_find_config.assert_called_once()
    
    return ApplicationWorkflowMock()


@pytest.fixture
def xdg_config_scenarios(monkeypatch, temp_config_file):
    """
    Fixture for XDG configuration path testing scenarios.

    Provides predefined XDG configuration scenarios for testing config file location
    logic with different XDG_CONFIG_HOME and HOME environment variable combinations.

    Usage:
        def test_xdg_config_scenarios(xdg_config_scenarios):
            scenarios = xdg_config_scenarios
            
            # Test XDG config exists scenario
            config_path = scenarios["xdg_exists"]()
            result = ConfigManager.find_config_file()
            assert result == config_path
            
            # Test fallback to HOME scenario
            config_path = scenarios["home_fallback"]()
            result = ConfigManager.find_config_file()
            assert result == config_path
    """
    
    def _xdg_exists():
        """Scenario: XDG_CONFIG_HOME exists with config file."""
        with open(temp_config_file, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")
        
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_file.parent))
        monkeypatch.delenv("HOME", raising=False)
        return temp_config_file
    
    def _home_fallback():
        """Scenario: XDG_CONFIG_HOME missing, fallback to HOME/.config."""
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")
        
        monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent")
        monkeypatch.setenv("HOME", str(home_config_dir))
        return config_path
    
    def _home_only():
        """Scenario: Only HOME/.config exists."""
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")
        
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_config_dir))
        return config_path
    
    def _no_config():
        """Scenario: No config file exists."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)
        return None
    
    return {
        "xdg_exists": _xdg_exists,
        "home_fallback": _home_fallback,
        "home_only": _home_only,
        "no_config": _no_config
    }


@pytest.fixture
def system_detection_comprehensive(mocker):
    """
    Fixture for comprehensive system detection mocking.

    Provides a more comprehensive and easier-to-use interface for mocking
    system detection functionality including gamescope active state and
    executable detection.

    Usage:
        def test_system_detection_comprehensive(system_detection_comprehensive):
            detection = system_detection_comprehensive
            
            # Setup gamescope as active with executable found
            detection.gamescope_active(True).executable_found(True)
            
            # Test detection
            assert SystemDetector.is_gamescope_active() == True
            assert SystemDetector.find_executable("gamescope") == True
    """
    
    class SystemDetectionMock:
        def __init__(self):
            self.mock_is_active = mocker.patch(
                "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=False
            )
            self.mock_find_exec = mocker.patch(
                "nscb.system_detector.SystemDetector.find_executable", return_value=True
            )
        
        def gamescope_active(self, active=True):
            """Set gamescope active state."""
            self.mock_is_active.return_value = active
            return self
        
        def executable_found(self, found=True):
            """Set executable found state."""
            self.mock_find_exec.return_value = found
            return self
        
        def reset(self):
            """Reset all mocks to default values."""
            self.mock_is_active.return_value = False
            self.mock_find_exec.return_value = True
            return self
    
    return SystemDetectionMock()


@pytest.fixture
def argument_processing_patterns():
    """
    Fixture for common argument processing patterns.

    Provides standardized argument patterns for testing argument parsing,
    separation, and processing functionality.

    Usage:
        def test_argument_processing(argument_processing_patterns):
            patterns = argument_processing_patterns
            
            # Test simple profile arguments
            result = process_args(patterns["simple_profile"])
            assert result == expected_simple_result
    """
    return {
        "simple_profile": ["-f", "-W", "1920", "-H", "1080"],
        "conflicting_flags": ["-f", "--borderless", "-W", "1920"],
        "with_separator": ["-f", "-W", "1920", "--", "app.exe", "arg1"],
        "mixed_args": ["-p", "profile1", "-W", "3840", "--", "game.exe"],
        "empty_args": [],
        "only_positionals": ["app.exe", "arg1", "arg2"],
        "complex_profile": ["-f", "-W", "1920", "-H", "1080", "--framerate-limit", "60"],
        "override_scenario": ["-p", "base", "-W", "3840", "-H", "2160", "--", "game.exe"]
    }


@pytest.fixture
def error_simulation_comprehensive():
    """
    Fixture for comprehensive error simulation.

    Provides a wide range of error objects and scenarios for testing
    error handling and exception propagation throughout the application.

    Usage:
        def test_error_handling(error_simulation_comprehensive):
            errors = error_simulation_comprehensive
            
            # Test file system errors
            with pytest.raises(PermissionError):
                raise errors["file_system"]["permission_denied"]
            
            # Test configuration errors
            with pytest.raises(ValueError):
                raise errors["configuration"]["invalid_format"]
    """
    return {
        "file_system": {
            "permission_denied": PermissionError("Permission denied"),
            "file_not_found": FileNotFoundError("File not found"),
            "directory_not_found": NotADirectoryError("Not a directory"),
            "file_exists": FileExistsError("File already exists")
        },
        "configuration": {
            "invalid_format": ValueError("Invalid configuration format"),
            "missing_key": KeyError("Missing required key"),
            "invalid_value": ValueError("Invalid value in configuration"),
            "parse_error": ValueError("Failed to parse configuration")
        },
        "execution": {
            "command_failed": RuntimeError("Command execution failed"),
            "timeout": TimeoutError("Command timed out"),
            "subprocess_error": RuntimeError("Subprocess error occurred"),
            "exit_code_error": RuntimeError("Unexpected exit code")
        },
        "system": {
            "executable_not_found": RuntimeError("Executable not found"),
            "gamescope_active": RuntimeError("Gamescope already active"),
            "environment_error": RuntimeError("Environment variable error"),
            "platform_error": RuntimeError("Unsupported platform")
        },
        "network": {
            "connection_error": ConnectionError("Connection failed"),
            "timeout": TimeoutError("Network timeout"),
            "ssl_error": RuntimeError("SSL certificate error")
        }
    }


@pytest.fixture
def integration_test_setup(mocker):
    """
    Fixture for comprehensive integration test setup.

    Provides a complete mock environment for integration testing with
    all major components mocked and ready for testing complex workflows.

    Usage:
        def test_integration_workflow(integration_test_setup):
            setup = integration_test_setup
            
            # Setup mocks
            setup.mock_config_loading({"gaming": "-f -W 1920"})
            setup.mock_system_detection(gamescope_active=False)
            setup.mock_execution_success()
            
            # Test application workflow
            app = Application()
            result = app.run(["-p", "gaming", "--", "/bin/game"])
            
            # Verify results
            assert result == 0
            setup.verify_config_loaded()
            setup.verify_execution_attempted()
    """
    
    class IntegrationTestSetup:
        def __init__(self):
            # Mock core components
            self.mock_find_config = mocker.patch(
                "nscb.config_manager.ConfigManager.find_config_file", return_value=None
            )
            self.mock_load_config = mocker.patch(
                "nscb.config_manager.ConfigManager.load_config", return_value=None
            )
            self.mock_is_active = mocker.patch(
                "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=False
            )
            self.mock_find_exec = mocker.patch(
                "nscb.system_detector.SystemDetector.find_executable", return_value=True
            )
            self.mock_run = mocker.patch(
                "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
            )
            self.mock_build = mocker.patch(
                "nscb.command_executor.CommandExecutor.build_command",
                side_effect=lambda x: "; ".join(x)
            )
            self.mock_merge = mocker.patch(
                "nscb.profile_manager.ProfileManager.merge_arguments"
            )
        
        def mock_config_loading(self, profiles=None, exports=None):
            """Mock configuration loading with specified profiles and exports."""
            from nscb.config_result import ConfigResult
            
            config_result = ConfigResult(profiles or {}, exports or {})
            self.mock_load_config.return_value = config_result
            return self
        
        def mock_system_detection(self, gamescope_active=False, executable_found=True):
            """Mock system detection with specified states."""
            self.mock_is_active.return_value = gamescope_active
            self.mock_find_exec.return_value = executable_found
            return self
        
        def mock_execution_success(self):
            """Mock successful execution."""
            self.mock_run.return_value = 0
            return self
        
        def mock_execution_failure(self, exit_code=1):
            """Mock failed execution with specified exit code."""
            self.mock_run.return_value = exit_code
            return self
        
        def mock_argument_merging(self, return_value):
            """Mock argument merging with specified return value."""
            self.mock_merge.return_value = return_value
            return self
        
        def verify_config_loaded(self):
            """Verify that config loading was attempted."""
            self.mock_load_config.assert_called()
            return self
        
        def verify_execution_attempted(self):
            """Verify that execution was attempted."""
            self.mock_run.assert_called()
            return self
        
        def verify_command_built(self):
            """Verify that command building was attempted."""
            self.mock_build.assert_called()
            return self
        
        def verify_argument_merging(self):
            """Verify that argument merging was attempted."""
            self.mock_merge.assert_called()
            return self
    
    return IntegrationTestSetup()


@pytest.fixture
def profile_test_scenarios():
    """
    Fixture for profile-based testing scenarios.

    Provides comprehensive profile configurations and expected merge results
    for testing profile management functionality.

    Usage:
        def test_profile_management(profile_test_scenarios):
            scenarios = profile_test_scenarios
            
            # Test basic profile merge
            profile_args = scenarios["basic"]["profiles"]
            override_args = scenarios["basic"]["overrides"]
            expected = scenarios["basic"]["expected"]
            
            result = merge_arguments(profile_args, override_args)
            assert result == expected
    """
    return {
        "basic": {
            "profiles": ["-f", "-W", "1920", "-H", "1080"],
            "overrides": ["-W", "3840"],
            "expected": ["-f", "-W", "3840", "-H", "1080"]
        },
        "conflict_resolution": {
            "profiles": ["-f", "-W", "1920"],
            "overrides": ["--borderless", "-W", "2560"],
            "expected": ["--borderless", "-W", "2560"]
        },
        "multiple_profiles": {
            "profiles": [
                ["-f", "-W", "1920"],
                ["-H", "1080", "--framerate-limit", "60"]
            ],
            "overrides": ["--framerate-limit", "120"],
            "expected": ["-f", "-W", "1920", "-H", "1080", "--framerate-limit", "120"]
        },
        "empty_profile": {
            "profiles": [],
            "overrides": ["-f", "-W", "1920"],
            "expected": ["-f", "-W", "1920"]
        },
        "empty_override": {
            "profiles": ["-f", "-W", "1920"],
            "overrides": [],
            "expected": ["-f", "-W", "1920"]
        },
        "complex_conflict": {
            "profiles": ["-f", "-W", "1920", "-H", "1080", "-C", "5"],
            "overrides": ["--borderless", "-W", "2560", "--framerate-limit", "120"],
            "expected": ["--borderless", "-W", "2560", "-H", "1080", "-C", "5", "--framerate-limit", "120"]
        }
    }
