from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Import the custom exception from conftest
from conftest import SystemExitCalled

from nscb import (
    get_env_commands,
    is_gamescope_active,
    main,
)


@pytest.mark.integration
def test_main_complete_workflow_with_profiles(mock_integration_setup, mock_system_exit):
    """Test complete main workflow with multiple profiles and argument merging"""
    mock_setup = mock_integration_setup
    config_data = """
# Config file with comments
gaming=-f -W 1920 -H 1080
streaming=--borderless -W 1280 -H 720
"""
    cmd = "nscb --profiles=gaming,streaming -W 1600 -- app".split(" ")
    with (
        patch("nscb.is_gamescope_active", return_value=False),
        patch("nscb.find_config_file", return_value=Path("/fake/config")),
        patch("builtins.open", new_callable=mock_open, read_data=config_data),
        patch("sys.argv", cmd),
        patch("nscb.find_executable", return_value=True),
    ):
        with pytest.raises(SystemExitCalled) as cm:
            main()

        # Verify the exit code
        assert cm.value.code == 0

        # Verify the merged command includes profile args with overrides
        called_cmd = mock_setup["run_nonblocking"].call_args[0][0]
        assert "gamescope" in called_cmd
        assert "-W 1600" in called_cmd  # Override should win
        assert "app" in called_cmd


@pytest.mark.integration
def test_main_error_scenarios(mock_system_exit):
    """Test main function error handling scenarios"""
    # Test missing gamescope executable - this should exit before execute_gamescope_command
    with (
        patch("nscb.find_executable", return_value=False),
        patch("logging.error") as mock_log,
        patch("sys.argv", ["nscb"]),
    ):
        with pytest.raises(SystemExitCalled) as cm:
            main()

        assert cm.value.code == 1
        mock_log.assert_called_with("'gamescope' not found in PATH")


@pytest.mark.integration
def test_gamescope_detection_and_execution_modes():
    """Test gamescope detection methods and execution modes"""
    # Test XDG desktop detection
    with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True):
        assert is_gamescope_active() is True


@pytest.mark.integration
def test_environment_commands_integration():
    """Test pre/post command environment variable handling"""
    test_cases = [
        # Test new variable names
        ({"NSCB_PRE_CMD": "pre", "NSCB_POST_CMD": "post"}, ("pre", "post")),
        # Test legacy variable names
        (
            {"NSCB_PRECMD": "old_pre", "NSCB_POSTCMD": "old_post"},
            ("old_pre", "old_post"),
        ),
    ]

    for env_vars, expected in test_cases:
        with patch.dict("os.environ", env_vars, clear=True):
            result = get_env_commands()
            assert result == expected
