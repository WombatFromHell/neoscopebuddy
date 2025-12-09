"""Tests for the environment helper functionality in NeoscopeBuddy."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to the path so we can import nscb modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from nscb.application import Application
from nscb.command_executor import CommandExecutor
from nscb.environment_helper import EnvironmentHelper, debug_log
from nscb.system_detector import SystemDetector


class TestEnvironmentHelperUnit:
    """Unit tests for the EnvironmentHelper class."""

    def test_debug_log_no_output_when_disabled(self, capsys, monkeypatch):
        """Test that debug_log doesn't output when NSCB_DEBUG is not set."""
        monkeypatch.delenv("NSCB_DEBUG", raising=False)
        debug_log("test message")
        captured = capsys.readouterr()
        assert "test message" not in captured.err

    @pytest.mark.parametrize(
        "debug_value", ["1", "true", "yes", "on", "TRUE", "YES", "ON"]
    )
    def test_debug_log_outputs_when_enabled(self, capsys, monkeypatch, debug_value):
        """Test that debug_log outputs when NSCB_DEBUG is set to truthy values."""
        monkeypatch.setenv("NSCB_DEBUG", debug_value)
        test_message = "debug test message"
        debug_log(test_message)
        captured = capsys.readouterr()
        assert f"[DEBUG] {test_message}" in captured.err

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
    def test_get_pre_post_commands_variations(self, monkeypatch, env_vars, expected):
        # Clear all env vars first
        for var in ["NSCB_PRE_CMD", "NSCB_POST_CMD", "NSCB_PRECMD", "NSCB_POSTCMD"]:
            monkeypatch.delenv(var, raising=False)

        # Set the test vars
        for var, value in env_vars.items():
            monkeypatch.setenv(var, value)

        pre, post = EnvironmentHelper.get_pre_post_commands()
        assert pre == expected[0]
        assert post == expected[1]

    def test_is_gamescope_active_xdg_method(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "gamescope")
        assert EnvironmentHelper.is_gamescope_active() is True

    def test_is_gamescope_active_not_gamescope_xdg(self, monkeypatch):
        monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
        # When XDG_CURRENT_DESKTOP is not gamescope, it should check ps command
        with patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 Xorg"
        ):
            assert EnvironmentHelper.is_gamescope_active() is False

    def test_is_gamescope_active_ps_method_finds_gamescope(self, monkeypatch):
        monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
        with patch(
            "subprocess.check_output",
            return_value="1234 ?    Sl     0:00 gamescope -f -W 1920 -H 1080",
        ):
            assert EnvironmentHelper.is_gamescope_active() is True

    def test_is_gamescope_active_ps_method_no_gamescope(self, monkeypatch):
        monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
        with patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 Xorg"
        ):
            assert EnvironmentHelper.is_gamescope_active() is False

    def test_is_gamescope_active_ps_command_error(self, monkeypatch):
        monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
        with patch("subprocess.check_output", side_effect=Exception("Command failed")):
            assert EnvironmentHelper.is_gamescope_active() is False

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1", True),
            ("true", True),
            ("yes", True),
            ("on", True),
            ("0", False),
            ("false", False),
            ("no", False),
            ("off", False),
            ("other", False),
            ("", False),
        ],
    )
    def test_should_disable_ld_preload_wrap_with_env_var(
        self, monkeypatch, value, expected
    ):
        if value:  # Only set if value is not empty string
            monkeypatch.setenv("NSCB_DISABLE_LD_PRELOAD_WRAP", value)
        else:
            monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)

        result = EnvironmentHelper.should_disable_ld_preload_wrap()
        assert result == expected

    def test_should_disable_ld_preload_wrap_with_faugus_log(self, monkeypatch):
        # Save original values
        original_faugus_log = os.environ.get("FAUGUS_LOG")
        original_disable_flag = os.environ.get("NSCB_DISABLE_LD_PRELOAD_WRAP")

        try:
            # Test that LD_PRELOAD wrapping is disabled when FAUGUS_LOG is set
            monkeypatch.setenv("FAUGUS_LOG", "/path/to/log")
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

            # Test that LD_PRELOAD wrapping is still disabled with a different FAUGUS_LOG value
            monkeypatch.setenv("FAUGUS_LOG", "some_value")
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

            # Clear FAUGUS_LOG and test with other variables
            monkeypatch.delenv("FAUGUS_LOG", raising=False)
            monkeypatch.setenv("OTHER_VAR", "value")
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is False

            # Test that FAUGUS_LOG takes precedence over NSCB_DISABLE_LD_PRELOAD_WRAP being falsy
            monkeypatch.setenv("FAUGUS_LOG", "/path/to/log")
            monkeypatch.setenv("NSCB_DISABLE_LD_PRELOAD_WRAP", "0")
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

            # Test with FAUGUS_LOG present but NSCB_DISABLE_LD_PRELOAD_WRAP as truthy (both should disable)
            monkeypatch.setenv("NSCB_DISABLE_LD_PRELOAD_WRAP", "1")
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

        finally:
            # Restore original environment
            if original_faugus_log is not None:
                monkeypatch.setenv("FAUGUS_LOG", original_faugus_log)
            elif "FAUGUS_LOG" in os.environ:
                monkeypatch.delenv("FAUGUS_LOG", raising=False)

            if original_disable_flag is not None:
                monkeypatch.setenv(
                    "NSCB_DISABLE_LD_PRELOAD_WRAP", original_disable_flag
                )
            elif "NSCB_DISABLE_LD_PRELOAD_WRAP" in os.environ:
                monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)

    def test_should_disable_ld_preload_wrap_no_vars_set(self, monkeypatch):
        monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
        monkeypatch.delenv("FAUGUS_LOG", raising=False)
        assert EnvironmentHelper.should_disable_ld_preload_wrap() is False


class TestEnvironmentHelperIntegration:
    """Integration tests for EnvironmentHelper with other modules."""

    def test_environment_helper_system_detector_integration(self):
        """Test that EnvironmentHelper and SystemDetector share gamescope detection logic."""
        # Both modules should be able to detect gamescope
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("XDG_CURRENT_DESKTOP", "gamescope")
            assert EnvironmentHelper.is_gamescope_active() is True
            assert SystemDetector.is_gamescope_active() is True

    def test_environment_helper_command_executor_integration(self, mocker):
        """Test EnvironmentHelper working with CommandExecutor for pre/post commands."""
        # Test the environment command flow integration
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
        ]

        for env_vars, expected in test_cases:
            mocker.patch.dict("os.environ", env_vars, clear=True)
            result = CommandExecutor.get_env_commands()
            assert result == expected

    def test_environment_helper_application_integration(
        self, mocker, temp_config_with_content
    ):
        """Test EnvironmentHelper as part of the full application workflow."""
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        # Set up environment with pre/post commands
        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "echo 'starting'", "NSCB_POST_CMD": "echo 'finished'"},
            clear=True,
        )

        app = Application()

        # Mock required components
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # Run the application to test environment integration
        result = app.run(["-p", "gaming", "--", "test_app"])

        assert result == 0
        # Verify the command was executed with pre/post commands
        call_args = mock_run.call_args[0][0]
        assert "echo 'starting'" in call_args
        assert "echo 'finished'" in call_args


class TestEnvironmentHelperEndToEnd:
    """End-to-end tests for EnvironmentHelper functionality."""

    def test_environment_variable_integration_e2e(
        self, mocker, temp_config_with_content
    ):
        config_data = "gaming=-f -W 1920 -H 1080\n"

        config_path = temp_config_with_content(config_data)
        mocker.patch.dict(
            "os.environ", {"NSCB_PRE_CMD": "before_cmd", "NSCB_POST_CMD": "after_cmd"}
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.EnvironmentHelper.is_gamescope_active",
            return_value=False,
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("sys.argv", ["nscb", "-p", "gaming", "--", "app"])
        mocker.patch("builtins.print")

        app = Application()
        result = app.run(["-p", "gaming", "--", "app"])

        assert result == 0

        called_cmd = mock_run.call_args[0][0]
        assert "before_cmd" in called_cmd
        assert "after_cmd" in called_cmd
        assert "app" in called_cmd

    def test_env_pre_post_command_flow_e2e(self, mocker):
        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "echo 'starting'", "NSCB_POST_CMD": "echo 'finished'"},
            clear=True,
        )
        pre_cmd, post_cmd = EnvironmentHelper.get_pre_post_commands()

        command_parts = [pre_cmd, "gamescope -f -- testapp", post_cmd]
        full_cmd = CommandExecutor.build_command(command_parts)

        assert "echo 'starting'" in full_cmd
        assert "echo 'finished'" in full_cmd
        assert "gamescope -f -- testapp" in full_cmd

    def test_env_variable_fallback_behavior_e2e(self, mocker):
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

    def test_env_command_chaining_scenarios_e2e(self):
        test_cases = [
            (["cmd1", "cmd2"], "cmd1; cmd2"),
            (["cmd1", "", "cmd2", ""], "cmd1; cmd2"),
            (["single"], "single"),
            (["", "", ""], ""),
            (["export X=1", "gamescope -f", "app"], "export X=1; gamescope -f; app"),
        ]

        for parts, expected_contains in test_cases:
            result = CommandExecutor.build_command(parts)
            if expected_contains:
                for part in expected_contains.split("; "):
                    if part.strip():
                        assert part.strip() in result

    def test_env_empty_variable_handling_e2e(self, mocker):
        mocker.patch.dict(
            "os.environ", {"NSCB_PRE_CMD": "", "NSCB_POST_CMD": ""}, clear=True
        )
        pre_cmd, post_cmd = EnvironmentHelper.get_pre_post_commands()
        assert pre_cmd == ""
        assert post_cmd == ""

        full_cmd = CommandExecutor.build_command([pre_cmd, "gamescope test", post_cmd])
        assert "gamescope test" in full_cmd

    def test_env_mixed_scenario_execution_e2e(self, mocker, temp_config_with_content):
        config_data = "test_profile=-f -W 1920 -H 1080\n"

        config_path = temp_config_with_content(config_data)

        mocker.patch.dict(
            "os.environ", {"NSCB_PRE_CMD": "before", "NSCB_POST_CMD": "after"}
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.EnvironmentHelper.is_gamescope_active",
            return_value=False,
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("sys.argv", ["nscb", "-p", "test_profile", "--", "myapp"])
        mocker.patch("builtins.print")

        app = Application()
        result = app.run(["-p", "test_profile", "--", "myapp"])

        assert result == 0

        if mock_run.call_args:
            called_cmd = mock_run.call_args[0][0]
            assert "before" in called_cmd
            assert "gamescope" in called_cmd
            assert "-f" in called_cmd
            assert "myapp" in called_cmd
            assert "after" in called_cmd

    def test_should_disable_ld_preload_wrap_e2e_with_faugus_launcher(self, mocker):
        """Test LD_PRELOAD wrapping disable behavior with faugus-launcher scenario."""
        original_env = dict(os.environ)

        try:
            # Test that LD_PRELOAD wrapping is disabled when FAUGUS_LOG is set (faugus-launcher detection)
            os.environ["FAUGUS_LOG"] = "/path/to/faugus/log"
            os.environ.pop("NSCB_DISABLE_LD_PRELOAD_WRAP", None)  # Ensure it's not set

            result = EnvironmentHelper.should_disable_ld_preload_wrap()
            assert result is True

            # Test with different FAUGUS_LOG value
            os.environ["FAUGUS_LOG"] = "some_other_log_path"
            result = EnvironmentHelper.should_disable_ld_preload_wrap()
            assert result is True

            # Test normal behavior when FAUGUS_LOG is not set
            os.environ.pop("FAUGUS_LOG", None)
            os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = "0"  # Explicitly false
            result = EnvironmentHelper.should_disable_ld_preload_wrap()
            assert result is False

            # Test with truthy disable flag
            os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = "1"
            result = EnvironmentHelper.should_disable_ld_preload_wrap()
            assert result is True

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
