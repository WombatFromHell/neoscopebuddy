"""Tests for the command execution functionality in NeoscopeBuddy."""

import io
import os
import selectors
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to the path so we can import nscb modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from nscb.application import Application
from nscb.command_executor import CommandExecutor, debug_log
from nscb.environment_helper import EnvironmentHelper
from nscb.system_detector import SystemDetector


class TestCommandExecutorUnit:
    """Unit tests for the CommandExecutor class."""

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

    def test_run_nonblocking_signature(self):
        import inspect

        sig = inspect.signature(CommandExecutor.run_nonblocking)
        assert len(sig.parameters) == 1
        assert "cmd" in sig.parameters

    def test_run_nonblocking_with_mocked_subprocess(self, mocker):
        # Mock subprocess.Popen to avoid actual process creation
        mock_process = Mock()
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.wait.return_value = 0

        mock_selector = Mock()
        mock_selector.get_map.return_value = []
        mock_selector.select.return_value = []

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

        result = CommandExecutor.run_nonblocking("echo test")
        assert result == 0

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


class TestCommandExecutorIntegration:
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

        # Mock subprocess to prevent actual execution
        mock_process = Mock()
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.wait.return_value = 0

        mock_selector = Mock()
        mock_selector.get_map.return_value = []
        mock_selector.select.return_value = []

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

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
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 0

        # Test with gamescope active
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active", return_value=True
        )
        mock_run = mocker.patch(
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
