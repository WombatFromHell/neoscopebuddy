import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


class SystemExitCalled(Exception):
    """Custom exception to simulate sys.exit behavior in tests"""

    def __init__(self, code):
        self.code = code
        super().__init__(f"sys.exit({code}) called")


@pytest.fixture
def mock_system_exit(mocker):
    """Fixture to mock sys.exit for testing"""

    def side_effect(code):
        raise SystemExitCalled(code)

    return mocker.patch("sys.exit", side_effect=side_effect)


@pytest.fixture
def mock_integration_setup(mocker):
    """Fixture to set up common mocking for integration tests"""
    mock_run_nonblocking = mocker.patch(
        "nscb.CommandExecutor.run_nonblocking", return_value=0
    )
    mock_build = mocker.patch(
        "nscb.CommandExecutor.build_command", side_effect=lambda x: "; ".join(x)
    )
    mock_print = mocker.patch("builtins.print")

    return {
        "run_nonblocking": mock_run_nonblocking,
        "build_command": mock_build,
        "print": mock_print,
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
    return mocker.patch("nscb.SystemDetector.find_executable", return_value=True)


@pytest.fixture
def mock_config_file(mocker, temp_config_file):
    """Fixture that creates a config file and mocks find_config_file to return it."""

    def _setup_config(content):
        with open(temp_config_file, "w") as f:
            f.write(content)
        return mocker.patch(
            "nscb.ConfigManager.find_config_file", return_value=temp_config_file
        )

    return _setup_config


@pytest.fixture
def mock_is_gamescope_active(mocker):
    """Fixture to mock is_gamescope_active function."""
    return mocker.patch("nscb.SystemDetector.is_gamescope_active")


@pytest.fixture
def mock_env_commands(mocker):
    """Fixture to mock environment commands."""

    def _setup_env(pre="", post=""):
        return mocker.patch(
            "nscb.CommandExecutor.get_env_commands", return_value=(pre, post)
        )

    return _setup_env


@pytest.fixture
def complex_args_scenario():
    """Fixture for complex argument scenarios."""
    return {
        "simple_profile": ["-f", "-W", "1920", "-H", "1080"],
        "conflicting_profile": ["--borderless", "-W", "2560"],
        "mixed_args": ["-f", "--mangoapp", "app.exe", "--", "game.exe"],
        "empty_args": [],
        "only_positionals": ["app.exe", "arg1", "arg2"],
    }


@pytest.fixture
def error_simulation():
    """Fixture for error simulation."""
    return {
        "permission_error": PermissionError("Permission denied"),
        "file_not_found": FileNotFoundError("File not found"),
        "value_error": ValueError("Invalid value"),
        "key_error": KeyError("Missing key"),
    }


@pytest.fixture
def mock_subprocess(mocker):
    """Fixture to mock subprocess operations."""
    mock_process = Mock()
    mock_process.stdout = Mock()
    mock_process.stderr = Mock()
    mock_process.wait.return_value = 0

    _mock_stdout_readline = mocker.patch.object(
        mock_process.stdout, "readline", side_effect=["test output\n", ""]
    )
    _mock_stderr_readline = mocker.patch.object(
        mock_process.stderr, "readline", side_effect=["error output\n", ""]
    )

    mock_selector = Mock()
    mock_selector.get_map.return_value = [Mock()]
    mock_selector.get_map.return_value = []
    mock_selector.select.return_value = [(Mock(fileobj=mock_process.stdout), None)]

    mocker.patch("subprocess.Popen", return_value=mock_process)
    mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

    return mock_process
