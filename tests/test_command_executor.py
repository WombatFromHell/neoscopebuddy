"""Tests for the command execution functionality in NeoscopeBuddy."""

import pytest

from nscb.command_executor import CommandExecutor
from nscb.system_detector import SystemDetector


class TestCommandExecutorUnit:
    """Unit tests for the CommandExecutor class."""

    def test_run_nonblocking_signature(self):
        import inspect

        sig = inspect.signature(CommandExecutor.run_nonblocking)
        assert len(sig.parameters) == 2
        assert "cmd" in sig.parameters
        assert "extra_env" in sig.parameters

    def test_run_nonblocking_with_mocked_subprocess(self, mocker):
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)

        result = CommandExecutor.run_nonblocking("echo test")
        assert result == 0


class TestCommandExecutorErrorHandling:
    """Test error handling in command executor using error simulation fixtures."""

    def test_command_execution_error_handling(
        self, error_simulation_comprehensive, mocker
    ):
        """
        Test command execution error handling using error_simulation_comprehensive fixture.

        This demonstrates how to use the error_simulation_comprehensive fixture to test
        various error scenarios in command execution.
        """
        # Test subprocess execution failure
        mock_result = mocker.MagicMock()
        mock_result.returncode = 1
        mocker.patch("subprocess.run", return_value=mock_result)

        result = CommandExecutor.run_nonblocking("nonexistent_command")
        assert result == 1

        # Test successful execution
        mock_result.returncode = 0
        result = CommandExecutor.run_nonblocking("test_command")
        assert result == 0

    def test_environment_command_error_handling(self, mock_env_commands, mocker):
        """
        Test environment command handling using mock_env_commands fixture.

        This demonstrates how to use the mock_env_commands fixture to test
        pre/post command execution scenarios.
        """
        # Setup environment commands
        mock_env_commands("echo 'pre-command'", "echo 'post-command'")

        # Mock subprocess.run
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)

        # Test that environment commands are handled properly
        result = CommandExecutor.run_nonblocking("test_command")
        assert result == 0

        # Verify that the environment commands were set up correctly
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()
        assert pre_cmd == "echo 'pre-command'"
        assert post_cmd == "echo 'post-command'"


class TestCommandExecutorIntegration:
    """Integration tests for command executor using integration fixtures."""

    def test_integration_with_mock_integration_setup(
        self, mock_integration_setup, mocker
    ):
        """
        Test command executor integration using mock_integration_setup fixture.

        This demonstrates how to use the mock_integration_setup fixture to test
        complex workflows involving command execution.
        """
        from nscb.command_executor import CommandExecutor

        # Access the mocked components from the integration setup
        mock_run = mock_integration_setup["run_nonblocking"]
        mock_build = mock_integration_setup["build_command"]

        # Test command building
        test_args = ["gamescope", "-f", "-W", "1920", "--", "/bin/game"]
        result = CommandExecutor.build_command(test_args)

        # Verify the mock was called
        mock_build.assert_called_once()

        # Test command execution
        result = CommandExecutor.run_nonblocking("test_command")
        mock_run.assert_called_once()

        assert result == 0


class TestCommandExecutorFixtureUtilization:
    """Test class demonstrating utilization of command executor fixtures."""

    def test_execution_scenarios_with_fixtures(
        self, mock_execution_scenarios, mocker, system_detection_comprehensive
    ):
        """
        Test execution scenarios using mock_execution_scenarios fixture.

        This demonstrates how to use the execution scenarios fixture to test
        various command building scenarios in a standardized way.
        """
        from nscb.command_executor import CommandExecutor

        # Setup system detection for testing
        system_detection_comprehensive.gamescope_active(False).executable_found(True)

        # Test basic execution scenario
        basic_scenario = mock_execution_scenarios["basic"]
        result = CommandExecutor.build_command(basic_scenario["args"])
        # Note: build_command joins with semicolons, so we need to adjust the expected result
        expected_with_semicolons = "; ".join(basic_scenario["args"])
        assert result == expected_with_semicolons

        # Test LD_PRELOAD execution scenario
        ld_preload_scenario = mock_execution_scenarios["with_ld_preload"]
        result = CommandExecutor.build_command(ld_preload_scenario["args"])
        expected_with_semicolons = "; ".join(ld_preload_scenario["args"])
        assert result == expected_with_semicolons

        # Test pre/post command execution scenario
        pre_post_scenario = mock_execution_scenarios["with_pre_post"]
        result = CommandExecutor.build_command(pre_post_scenario["args"])
        expected_with_semicolons = "; ".join(pre_post_scenario["args"])
        assert result == expected_with_semicolons

        # Test complex execution scenario
        complex_scenario = mock_execution_scenarios["complex"]
        result = CommandExecutor.build_command(complex_scenario["args"])
        expected_with_semicolons = "; ".join(complex_scenario["args"])
        assert result == expected_with_semicolons

    def test_run_nonblocking_with_empty_output(self, mocker):
        """Test run_nonblocking with command that produces no output."""
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)

        result = CommandExecutor.run_nonblocking("echo ''")
        assert result == 0

    def test_run_nonblocking_with_immediate_failure(self, mocker):
        """Test run_nonblocking with command that fails immediately."""
        mock_result = mocker.MagicMock()
        mock_result.returncode = 1
        mocker.patch("subprocess.run", return_value=mock_result)

        result = CommandExecutor.run_nonblocking("false")
        assert result == 1

    @pytest.mark.parametrize(
        "env_vars,expected",
        [
            (
                {"NSCB_PRE_CMD": "before_cmd", "NSCB_POST_CMD": "after_cmd"},
                ("before_cmd", "after_cmd"),
            ),
            (
                {"NSCB_PRECMD": "legacy_before", "NSCB_POSTCMD": "legacy_after"},
                ("legacy_before", "legacy_after"),
            ),
            (
                {
                    "NSCB_PRE_CMD": "new_before",
                    "NSCB_POST_CMD": "new_after",
                    "NSCB_PRECMD": "legacy_before",
                    "NSCB_POSTCMD": "legacy_after",
                },
                ("new_before", "new_after"),
            ),
            (
                {"NSCB_PRE_CMD": "new_before", "NSCB_POSTCMD": "legacy_after"},
                ("new_before", "legacy_after"),
            ),
            ({}, ("", "")),
            ({"NSCB_PRE_CMD": "", "NSCB_POST_CMD": ""}, ("", "")),
        ],
    )
    def test_get_env_commands_variations(self, monkeypatch, env_vars, expected):
        # Clear all env vars first
        for var in ["NSCB_PRE_CMD", "NSCB_POST_CMD", "NSCB_PRECMD", "NSCB_POSTCMD"]:
            monkeypatch.delenv(var, raising=False)

        # Set the test vars
        for var, value in env_vars.items():
            monkeypatch.setenv(var, value)

        pre, post = CommandExecutor.get_env_commands()
        assert pre == expected[0]
        assert post == expected[1]

    @pytest.mark.parametrize(
        "parts,expected",
        [
            (["pre_cmd", "app_cmd", "post_cmd"], "pre_cmd; app_cmd; post_cmd"),
            (["single_cmd"], "single_cmd"),
            (["pre_cmd", "", "post_cmd"], "pre_cmd; post_cmd"),
            (["", "cmd1", "", "", "cmd2", ""], "cmd1; cmd2"),
            (["", "", ""], ""),
            ([], ""),
        ],
    )
    def test_build_command_variations(self, parts, expected):
        result = CommandExecutor.build_command(parts)
        assert result == expected


class TestCommandExecutorModuleIntegration:
    """Integration tests for the CommandExecutor with other modules."""

    def test_command_executor_environment_helper_integration(self, mocker):
        """Test CommandExecutor working with EnvironmentHelper for pre/post commands."""
        # Test the get_env_commands method which integrates with EnvironmentHelper
        test_cases = [
            (
                {"NSCB_PRE_CMD": "new_pre", "NSCB_POST_CMD": "new_post"},
                ("new_pre", "new_post"),
            ),
            (
                {"NSCB_PRECMD": "old_pre", "NSCB_POSTCMD": "old_post"},
                ("old_pre", "old_post"),
            ),
            (
                {
                    "NSCB_PRE_CMD": "new_pre",
                    "NSCB_POST_CMD": "new_post",
                    "NSCB_PRECMD": "old_pre",
                    "NSCB_POSTCMD": "old_post",
                },
                ("new_pre", "new_post"),
            ),
            (
                {"NSCB_PRE_CMD": "new_pre", "NSCB_POSTCMD": "old_post"},
                ("new_pre", "old_post"),
            ),
        ]

        for env_vars, expected in test_cases:
            mocker.patch.dict("os.environ", env_vars, clear=True)
            result = CommandExecutor.get_env_commands()
            assert result == expected

    def test_command_executor_system_detection_integration(self, mocker):
        """Test CommandExecutor execution with SystemDetector for gamescope detection."""
        # Mock environment detection
        mocker.patch.dict(
            "os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True
        )

        # Verify that gamescope detection works
        assert SystemDetector.is_gamescope_active() is True

    def test_command_execution_full_integration(self, mocker):
        """Test full command execution workflow with mocked components."""
        # Mock all necessary components
        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "echo start", "NSCB_POST_CMD": "echo end"},
            clear=True,
        )
        mocker.patch(
            "nscb.system_detector.EnvironmentHelper.is_gamescope_active",
            return_value=False,
        )

        # Mock subprocess.run to prevent actual execution
        mock_result = mocker.MagicMock()
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)

        # Test build_command functionality
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()
        parts = [pre_cmd, "gamescope -f -- myapp", post_cmd]
        built_cmd = CommandExecutor.build_command(parts)

        assert "echo start" in built_cmd
        assert "gamescope -f -- myapp" in built_cmd
        assert "echo end" in built_cmd

        # Test full execution
        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 0


class TestCommandExecutorEndToEnd:
    """End-to-end tests for CommandExecutor functionality."""

    @pytest.fixture(autouse=True)
    def _disable_auto_res(self, mocker):
        # These tests assert exact commands and shouldn't hit a real display backend.
        mocker.patch(
            "nscb.command_executor.DisplayDetector.get_resolution", return_value=None
        )

    def test_execute_gamescope_command_normal_execution(self, mocker):
        mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=("", ""),
        )
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.build_command",
            side_effect=lambda x: " ".join(filter(None, x)),
        )
        mocker.patch("builtins.print")
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        final_args = ["-f", "-W", "1920", "--", "mygame.exe"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gamescope" in call_args
        assert "-f" in call_args
        assert "1920" in call_args
        assert "mygame.exe" in call_args
        assert result == 0  # Should return exit code

    def test_execute_gamescope_command_under_gamescope_with_separator(self, mocker):
        mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=("", ""),
        )
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=True
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.build_command",
            side_effect=lambda x: " ".join(filter(None, x)),
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        final_args = ["-f", "-W", "1920", "--", "mygame.exe"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gamescope" not in call_args
        assert "mygame.exe" in call_args
        # Check that -f is not present as a standalone flag (not substring in other arguments)
        import re

        assert not re.search(r"-f(\s|;|$)", call_args)
        assert result == 0  # Should return exit code

    def test_execute_gamescope_command_force_nested_under_gamescope(
        self, mocker, monkeypatch
    ):
        """NSCB_FORCE_NESTED=1 launches a nested gamescope even when one is active."""
        mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=("", ""),
        )
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=True
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.build_command",
            side_effect=lambda x: " ".join(filter(None, x)),
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        monkeypatch.setenv("NSCB_FORCE_NESTED", "1")
        monkeypatch.delenv("LD_PRELOAD", raising=False)
        monkeypatch.delenv("NSCB_FRAMELIMIT", raising=False)

        final_args = ["-f", "-W", "1920", "--", "mygame.exe"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gamescope" in call_args
        assert "mygame.exe" in call_args
        assert result == 0

    def test_execute_gamescope_command_with_pre_post_commands(self, mocker):
        mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=("echo pre", "echo post"),
        )
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.build_command",
            side_effect=lambda x: "; ".join(filter(None, x)),
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        final_args = ["-f", "--", "mygame.exe"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "echo pre" in call_args
        assert "echo post" in call_args
        assert "gamescope" in call_args
        assert "mygame.exe" in call_args
        assert result == 0  # Should return exit code

    def test_execution_full_command_building(self, mocker):
        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "echo start", "NSCB_POST_CMD": "echo end"},
            clear=True,
        )
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()

        parts = [pre_cmd, "gamescope -f -- myapp", post_cmd]
        built_cmd = CommandExecutor.build_command(parts)

        assert "echo start" in built_cmd
        assert "gamescope -f -- myapp" in built_cmd
        assert "echo end" in built_cmd
        assert "start; gamescope" in built_cmd or "start;gamescope" in built_cmd

    def test_execution_environment_command_integration(self, mocker):
        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "export VAR=test", "NSCB_POST_CMD": "echo done"},
            clear=True,
        )

        pre_cmd, post_cmd = CommandExecutor.get_env_commands()
        command_parts = [pre_cmd, "gamescope test", post_cmd]
        full_cmd = CommandExecutor.build_command(command_parts)

        assert "export VAR=test" in full_cmd
        assert "echo done" in full_cmd
        assert "gamescope test" in full_cmd

    def test_execution_command_execution_variations(self, mocker):
        # Test with gamescope not active
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 0

        # Test with gamescope active
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=True
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 0

    def test_execution_error_handling_in_engine(self, mocker):
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=1
        )
        mocker.patch("builtins.print")

        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 1

    def test_env_pre_post_command_flow(self, mocker):
        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "echo 'starting'", "NSCB_POST_CMD": "echo 'finished'"},
            clear=True,
        )
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()

        command_parts = [pre_cmd, "gamescope -f -- testapp", post_cmd]
        full_cmd = CommandExecutor.build_command(command_parts)

        assert "echo 'starting'" in full_cmd
        assert "echo 'finished'" in full_cmd
        assert "gamescope -f -- testapp" in full_cmd

    def test_build_inactive_gamescope_command_no_separator(self, mocker, monkeypatch):
        """Test _build_inactive_gamescope_command when no -- separator is found."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        # Mock LD_PRELOAD functions to return False
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )

        # Use monkeypatch to properly mock os.environ.get
        def mock_environ_get(key, default=None):
            if key == "LD_PRELOAD":
                return None
            elif key == "NSCB_DEBUG":
                return ""  # So debug_log doesn't output anything
            else:
                # For all other keys, return the default value
                return default if default is not None else ""

        monkeypatch.setattr("os.environ.get", mock_environ_get)

        args = ["-f", "-W", "1920"]  # No -- separator
        result = CommandExecutor._build_inactive_gamescope_command(args, "", "")

        # Should build a command with gamescope and the args directly
        assert "gamescope -f -W 1920" in result
        assert "--" not in result  # No separator should be present

    def test_build_inactive_gamescope_command_no_separator_with_exports(
        self, mocker, monkeypatch
    ):
        """Test _build_inactive_gamescope_command when no -- separator but with exports."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        # Mock LD_PRELOAD functions to return False
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )

        # Use monkeypatch to properly mock os.environ.get
        def mock_environ_get(key, default=None):
            if key == "LD_PRELOAD":
                return None
            elif key == "NSCB_DEBUG":
                return ""  # So debug_log doesn't output anything
            else:
                # For all other keys, return the default value
                return default if default is not None else ""

        monkeypatch.setattr("os.environ.get", mock_environ_get)

        args = ["-f", "-W", "1920"]  # No -- separator
        result = CommandExecutor._build_inactive_gamescope_command(args, "", "")

        # Should build a command with gamescope and the args directly
        assert "gamescope -f -W 1920" in result

    def test_build_inactive_gamescope_command_framelimit_injects(
        self, mocker, monkeypatch
    ):
        """NSCB_FRAMELIMIT injects -r into the gamescope launch args."""
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )
        monkeypatch.setenv("NSCB_FRAMELIMIT", "60")

        monkeypatch.delenv("LD_PRELOAD", raising=False)
        monkeypatch.delenv("NSCB_DEBUG", raising=False)

        result = CommandExecutor._build_inactive_gamescope_command(
            ["-f", "-W", "1920"], "", ""
        )
        assert "gamescope -r 60 -f -W 1920" in result

    def test_build_inactive_gamescope_command_framelimit_overrides_existing_r(
        self, mocker, monkeypatch
    ):
        """NSCB_FRAMELIMIT overrides a profile/explicit -r."""
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )
        monkeypatch.setenv("NSCB_FRAMELIMIT", "60")

        monkeypatch.delenv("LD_PRELOAD", raising=False)
        monkeypatch.delenv("NSCB_DEBUG", raising=False)

        result = CommandExecutor._build_inactive_gamescope_command(
            ["-r", "144", "-f"], "", ""
        )
        assert "gamescope -r 60 -f" in result
        assert "-r 144" not in result

    def test_build_inactive_gamescope_command_framelimit_with_separator(
        self, mocker, monkeypatch
    ):
        """NSCB_FRAMELIMIT only affects gamescope args before --, not the app."""
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )
        monkeypatch.setenv("NSCB_FRAMELIMIT", "60")

        monkeypatch.delenv("LD_PRELOAD", raising=False)
        monkeypatch.delenv("NSCB_DEBUG", raising=False)

        result = CommandExecutor._build_inactive_gamescope_command(
            ["-f", "--", "/bin/mygame"], "", ""
        )
        assert "gamescope -r 60 -f -- /bin/mygame" in result

    def test_build_active_gamescope_command_ignores_framelimit(
        self, mocker, monkeypatch
    ):
        """NSCB_FRAMELIMIT is ignored when gamescope is already active."""
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=True,
        )
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )
        monkeypatch.setenv("NSCB_FRAMELIMIT", "60")

        monkeypatch.delenv("LD_PRELOAD", raising=False)
        monkeypatch.delenv("NSCB_DEBUG", raising=False)

        result = CommandExecutor._build_active_gamescope_command(
            ["-f", "-W", "1920"], "", ""
        )
        assert "gamescope -r 60" not in result

    def test_build_active_gamescope_command_no_separator(self, mocker, monkeypatch):
        """Test _build_active_gamescope_command when no -- separator is found."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=True
        )
        # Mock LD_PRELOAD functions to return False
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )

        # Use monkeypatch to properly mock os.environ.get
        def mock_environ_get(key, default=None):
            if key == "LD_PRELOAD":
                return None
            elif key == "NSCB_DEBUG":
                return ""  # So debug_log doesn't output anything
            else:
                # For all other keys, return the default value
                return default if default is not None else ""

        monkeypatch.setattr("os.environ.get", mock_environ_get)

        args = ["-f", "-W", "1920"]  # No -- separator
        result = CommandExecutor._build_active_gamescope_command(args, "", "")

        # Should return empty string when no pre/post commands and no app args
        assert result == ""

    def test_build_active_gamescope_command_no_separator_with_exports(
        self, mocker, monkeypatch
    ):
        """Test _build_active_gamescope_command when no -- separator but with exports."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=True
        )
        # Mock LD_PRELOAD functions to return False
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )

        # Use monkeypatch to properly mock os.environ.get
        def mock_environ_get(key, default=None):
            if key == "LD_PRELOAD":
                return None
            elif key == "NSCB_DEBUG":
                return ""  # So debug_log doesn't output anything
            else:
                # For all other keys, return the default value
                return default if default is not None else ""

        monkeypatch.setattr("os.environ.get", mock_environ_get)

        args = ["-f", "-W", "1920"]  # No -- separator
        result = CommandExecutor._build_active_gamescope_command(args, "", "")

        # Should return empty string when no pre/post commands and no app args
        assert result == ""

    def test_execute_gamescope_command_empty_scenario(self, mocker):
        """Test execute_gamescope_command when no command to execute is built."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=True
        )
        # Mock build command to return empty string
        mocker.patch(
            "nscb.command_executor.CommandExecutor._build_active_gamescope_command",
            return_value="",
        )

        result = CommandExecutor.execute_gamescope_command(["-f", "-W", "1920"])

        # Should return 0 when no command to execute
        assert result == 0

    def test_execute_gamescope_command_with_ld_preload(self, mocker, monkeypatch):
        """Test execute_gamescope_command when LD_PRELOAD is present and should be handled."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        # Mock LD_PRELOAD functions to return True so LD_PRELOAD is handled
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=False,
        )

        # Use monkeypatch to mock os.environ.get to return an LD_PRELOAD value
        def mock_environ_get(key, default=None):
            if key == "LD_PRELOAD":
                return "/path/to/library.so"  # Simulate LD_PRELOAD being set
            elif key == "NSCB_DEBUG":
                return ""  # So debug_log doesn't output anything
            else:
                return default if default is not None else ""

        monkeypatch.setattr("os.environ.get", mock_environ_get)

        # Mock run_nonblocking to capture the command that would be executed
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        args = ["-f", "--", "testapp"]
        result = CommandExecutor.execute_gamescope_command(args)

        # Verify run_nonblocking was called and check that LD_PRELOAD handling was included
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]  # Get the command string argument

        # Should include env -u LD_PRELOAD for gamescope and preserve LD_PRELOAD for app (LD_LIBRARY_PATH is passthrough)
        assert "env -u LD_PRELOAD gamescope" in call_args
        assert "env LD_PRELOAD=/path/to/library.so testapp" in call_args
        assert "-u LD_LIBRARY_PATH" not in call_args

        assert result == 0

    def test_execute_gamescope_command_with_ld_preload_disabled_by_env(
        self, mocker, monkeypatch
    ):
        """Test execute_gamescope_command when LD_PRELOAD wrapping is disabled via environment."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        # Mock LD_PRELOAD functions to return True to disable LD_PRELOAD wrapping
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=True,  # Disable LD_PRELOAD wrapping
        )

        # Use monkeypatch to mock os.environ.get to return an LD_PRELOAD value
        def mock_environ_get(key, default=None):
            if key == "LD_PRELOAD":
                return "/path/to/library.so"  # Simulate LD_PRELOAD being set
            elif key == "NSCB_DEBUG":
                return ""  # So debug_log doesn't output anything
            elif key == "NSCB_DISABLE_LD_PRELOAD_WRAP":
                return "1"  # This is what would disable LD_PRELOAD wrapping
            else:
                return default if default is not None else ""

        monkeypatch.setattr("os.environ.get", mock_environ_get)

        # Mock run_nonblocking to capture the command that would be executed
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        args = ["-f", "--", "testapp"]
        result = CommandExecutor.execute_gamescope_command(args)

        # Verify run_nonblocking was called and check that LD_PRELOAD was NOT handled for gamescope
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]  # Get the command string argument

        # Should NOT include env -u LD_PRELOAD since wrapping is disabled
        assert "env -u LD_PRELOAD gamescope" not in call_args
        # Should run gamescope directly with the app
        assert "gamescope -f -- testapp" in call_args

        assert result == 0

    def test_execute_gamescope_command_with_ld_preload_disabled_by_faugus(
        self, mocker, monkeypatch
    ):
        """Test execute_gamescope_command when LD_PRELOAD wrapping is disabled via FAUGUS_LOG."""
        # Mock environment detection
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        # Mock LD_PRELOAD functions to return True to disable LD_PRELOAD wrapping
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.should_disable_ld_preload_wrap",
            return_value=True,  # Disable LD_PRELOAD wrapping
        )

        # Use monkeypatch to mock os.environ.get to return an LD_PRELOAD value and FAUGUS_LOG
        def mock_environ_get(key, default=None):
            if key == "LD_PRELOAD":
                return "/path/to/library.so"  # Simulate LD_PRELOAD being set
            elif key == "NSCB_DEBUG":
                return ""  # So debug_log doesn't output anything
            elif key == "FAUGUS_LOG":
                return "1"  # This disables LD_PRELOAD wrapping automatically
            else:
                return default if default is not None else ""

        monkeypatch.setattr("os.environ.get", mock_environ_get)

        # Mock run_nonblocking to capture the command that would be executed
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        args = ["-f", "--", "testapp"]
        result = CommandExecutor.execute_gamescope_command(args)

        # Verify run_nonblocking was called and check that LD_PRELOAD was NOT handled for gamescope
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]  # Get the command string argument

        # Should NOT include env -u LD_PRELOAD since wrapping is disabled
        assert "env -u LD_PRELOAD gamescope" not in call_args
        # Should run gamescope directly with the app
        assert "gamescope -f -- testapp" in call_args

        assert result == 0


class TestEvaluateCondition:
    """Tests for CommandExecutor.evaluate_condition (structured predicates, no shell)."""

    def test_env_var_equals_match(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "niri")
        assert (
            CommandExecutor.evaluate_condition("env:XDG_CURRENT_DESKTOP=niri") is True
        )

    def test_env_var_equals_no_match(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "gnome")
        assert (
            CommandExecutor.evaluate_condition("env:XDG_CURRENT_DESKTOP=niri") is False
        )

    def test_env_var_set_any_value(self, monkeypatch):
        monkeypatch.setenv("SOME_VAR", "anything")
        assert CommandExecutor.evaluate_condition("env:SOME_VAR") is True

    def test_env_var_not_set(self, monkeypatch):
        monkeypatch.delenv("UNSET_VAR", raising=False)
        assert CommandExecutor.evaluate_condition("env:UNSET_VAR") is False

    def test_env_var_set_but_empty(self, monkeypatch):
        monkeypatch.setenv("EMPTY_VAR", "")
        assert CommandExecutor.evaluate_condition("env:EMPTY_VAR") is False

    def test_cmd_found_on_path(self, mocker):
        mocker.patch("shutil.which", return_value="/usr/bin/kscreen-doctor")
        assert CommandExecutor.evaluate_condition("cmd:kscreen-doctor") is True

    def test_cmd_not_found_on_path(self, mocker):
        mocker.patch("shutil.which", return_value=None)
        assert CommandExecutor.evaluate_condition("cmd:nonexistent-tool") is False

    def test_file_exists(self, mocker):
        mocker.patch("pathlib.Path.exists", return_value=True)
        assert CommandExecutor.evaluate_condition("file:/tmp/marker") is True

    def test_file_does_not_exist(self, mocker):
        mocker.patch("pathlib.Path.exists", return_value=False)
        assert CommandExecutor.evaluate_condition("file:/tmp/missing") is False

    def test_unrecognized_form_fails_closed(self):
        assert CommandExecutor.evaluate_condition("garbage:whatever") is False

    def test_bare_string_no_prefix_fails_closed(self):
        assert CommandExecutor.evaluate_condition("true") is False


class TestExecuteBare:
    """Tests for CommandExecutor.execute_bare."""

    def test_execute_bare_runs_app_command(self, mocker):
        mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=("", ""),
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        result = CommandExecutor.execute_bare(["--", "mygame", "--flag"])

        assert result == 0
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "mygame" in cmd
        assert "--flag" in cmd

    def test_execute_bare_no_separator_returns_1(self, mocker):
        result = CommandExecutor.execute_bare(["-f", "-W", "1920"])
        assert result == 1

    def test_execute_bare_empty_app_args_returns_0(self, mocker):
        result = CommandExecutor.execute_bare(["--"])
        assert result == 0

    def test_execute_bare_applies_pre_post_hooks(self, mocker):
        mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=("echo pre", "echo post"),
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        CommandExecutor.execute_bare(["--", "mygame"])

        cmd = mock_run.call_args[0][0]
        assert "echo pre" in cmd
        assert "echo post" in cmd
        assert "mygame" in cmd

    def test_execute_bare_passes_exports(self, mocker):
        mocker.patch(
            "nscb.command_executor.CommandExecutor.get_env_commands",
            return_value=("", ""),
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        exports = {"MY_VAR": "1"}
        CommandExecutor.execute_bare(["--", "mygame"], exports)

        assert mock_run.call_args[0][1] == exports


class TestApplyAutoRes:
    """Coverage for NSCB_AUTO_RES injection in CommandExecutor."""

    def test_injects_when_no_explicit_flag(self, monkeypatch, mocker):
        monkeypatch.delenv("NSCB_AUTO_RES", raising=False)
        mocker.patch(
            "nscb.command_executor.DisplayDetector.get_resolution",
            return_value=(3440, 1440),
        )
        result = CommandExecutor._apply_auto_res(["-f"])
        assert result[:4] == ["-W", "3440", "-H", "1440"]
        assert "-f" in result

    def test_explicit_flag_always_wins(self, monkeypatch, mocker):
        monkeypatch.setenv("NSCB_AUTO_RES", "1")
        mock_res = mocker.patch(
            "nscb.command_executor.DisplayDetector.get_resolution",
            return_value=(3440, 1440),
        )
        result = CommandExecutor._apply_auto_res(["-W", "1920", "-H", "1080"])
        assert result == ["-W", "1920", "-H", "1080"]
        mock_res.assert_not_called()

    def test_explicit_disable_skips(self, monkeypatch, mocker):
        monkeypatch.setenv("NSCB_AUTO_RES", "false")
        mock_res = mocker.patch(
            "nscb.command_executor.DisplayDetector.get_resolution",
            return_value=(3440, 1440),
        )
        result = CommandExecutor._apply_auto_res(["-f"])
        assert result == ["-f"]
        mock_res.assert_not_called()

    def test_detection_failure_is_noop(self, monkeypatch, mocker):
        monkeypatch.delenv("NSCB_AUTO_RES", raising=False)
        mocker.patch(
            "nscb.command_executor.DisplayDetector.get_resolution", return_value=None
        )
        assert CommandExecutor._apply_auto_res(["-f"]) == ["-f"]

    def test_merged_resolution_flags_block_auto(self, monkeypatch, mocker):
        # Profile-supplied -W/-H are already in the merged args, so auto-res defers.
        monkeypatch.delenv("NSCB_AUTO_RES", raising=False)
        mock_res = mocker.patch(
            "nscb.command_executor.DisplayDetector.get_resolution",
            return_value=(3440, 1440),
        )
        result = CommandExecutor._apply_auto_res(["-f", "-W", "1920", "-H", "1080"])
        assert result == ["-f", "-W", "1920", "-H", "1080"]
        mock_res.assert_not_called()
