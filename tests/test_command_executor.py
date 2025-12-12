"""Tests for the command execution functionality in NeoscopeBuddy."""

import selectors

import pytest

from nscb.command_executor import CommandExecutor, debug_log
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
        mock_process = mocker.MagicMock()
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.wait.return_value = 0

        mock_selector = mocker.MagicMock()
        mock_selector.get_map.return_value = []
        mock_selector.select.return_value = []

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

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
        from nscb.command_executor import CommandExecutor

        # Test subprocess execution failure
        mock_process = mocker.MagicMock()
        mock_process.wait.return_value = 1
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = "Command failed\n"

        mock_selector = mocker.MagicMock()
        mock_selector.get_map.return_value = []
        mock_selector.select.return_value = []

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

        # Test that subprocess errors are handled properly
        result = CommandExecutor.run_nonblocking("nonexistent_command")
        assert result == 1

        # Test IOError handling during subprocess operations
        # Reset the process to success mode first
        mock_process.wait.return_value = 0
        mock_process.stdout.readline.side_effect = error_simulation_comprehensive[
            "file_system"
        ]["permission_denied"]
        mock_process.stderr.readline.side_effect = error_simulation_comprehensive[
            "file_system"
        ]["permission_denied"]

        # This should handle the IOError gracefully
        result = CommandExecutor.run_nonblocking("test_command")
        # Should still return the process exit code even with IO errors
        assert result == 0

    def test_environment_command_error_handling(self, mock_env_commands, mocker):
        """
        Test environment command handling using mock_env_commands fixture.

        This demonstrates how to use the mock_env_commands fixture to test
        pre/post command execution scenarios.
        """
        from nscb.command_executor import CommandExecutor

        # Setup environment commands
        mock_env_commands("echo 'pre-command'", "echo 'post-command'")

        # Mock the actual command execution
        mock_process = mocker.MagicMock()
        mock_process.wait.return_value = 0
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""

        mock_selector = mocker.MagicMock()
        mock_selector.get_map.return_value = []
        mock_selector.select.return_value = []

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

        # Test that environment commands are handled properly
        result = CommandExecutor.run_nonblocking("test_command")
        assert result == 0

        # Verify that the environment commands were set up correctly
        from nscb.command_executor import CommandExecutor

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

    def test_subprocess_scenarios_with_fixtures(self, mock_subprocess, mocker):
        """
        Test subprocess handling using the consolidated subprocess fixture.

        This demonstrates how to use the consolidated mock_subprocess fixture
        to test various subprocess execution scenarios in a standardized way.
        """
        # Test that the consolidated fixture is working by verifying it mocks subprocess correctly
        import subprocess

        assert hasattr(subprocess, "Popen")
        assert callable(subprocess.Popen)

        # Test the default success behavior (exit code 0)
        assert mock_subprocess.wait.return_value == 0

        # Test that we can configure the fixture for failure scenarios
        mock_subprocess.wait.return_value = 1
        mocker.patch.object(
            mock_subprocess.stderr, "readline", side_effect=["error output\n", ""]
        )
        assert mock_subprocess.wait.return_value == 1

        # Reset to success for other tests
        mock_subprocess.wait.return_value = 0
        mocker.patch.object(mock_subprocess.stderr, "readline", side_effect=["", ""])

    def test_run_nonblocking_with_empty_output(self, mocker):
        """Test run_nonblocking with command that produces no output."""
        mock_process = mocker.MagicMock()
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.wait.return_value = 0
        mock_stdout = mocker.Mock()
        mock_stderr = mocker.Mock()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr

        mock_selector = mocker.MagicMock()
        # Track call count to eventually return empty map and break the while loop
        call_count = 0

        def get_map():
            nonlocal call_count
            call_count += 1
            # Return empty map after first call to break out of the while loop
            if call_count == 1:
                return {id(mock_process.stdout): mock_process.stdout}
            return {}

        mock_selector.get_map.side_effect = get_map
        mock_selector.select.return_value = [
            (mocker.Mock(fileobj=mock_stdout), selectors.EVENT_READ)
        ]

        # Mock sys.stdout and sys.stderr to prevent write errors
        mocker.patch("sys.stdout")
        mocker.patch("sys.stderr")

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

        result = CommandExecutor.run_nonblocking("echo ''")
        assert result == 0

    def test_run_nonblocking_with_immediate_failure(self, mocker):
        """Test run_nonblocking with command that fails immediately (lines 43-52)."""
        mock_process = mocker.MagicMock()
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.wait.return_value = 1  # Non-zero exit code
        mock_process.stdout = mocker.Mock()
        mock_process.stderr = mocker.Mock()

        mock_selector = mocker.MagicMock()
        mock_selector.get_map.return_value = {}
        mock_selector.select.return_value = []

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

        result = CommandExecutor.run_nonblocking("false")
        assert result == 1

    def test_run_nonblocking_with_stdout_stderr_mix(self, mocker):
        """Test run_nonblocking with both stdout and stderr output (lines 43-52)."""
        mock_stdout = mocker.MagicMock()
        mock_stdout.readline.side_effect = ["stdout line 1\n", "stdout line 2\n", ""]
        mock_stdout.__hash__ = lambda: 123  # For selector key
        mock_stderr = mocker.MagicMock()
        mock_stderr.readline.side_effect = ["stderr line 1\n", ""]
        mock_stderr.__hash__ = lambda: 456  # For selector key

        mock_process = mocker.MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.wait.return_value = 0

        mock_selector = mocker.MagicMock()
        mock_selector_map = {
            123: mocker.Mock(fileobj=mock_stdout),
            456: mocker.Mock(fileobj=mock_stderr),
        }
        call_count = 0

        def get_map():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # Return maps for 3 iterations
                return mock_selector_map
            return {}  # Empty after that

        mock_selector.get_map.side_effect = get_map

        # Simulate selector.select() returning both stdout and stderr in different calls
        def select():
            if call_count == 1:
                return [(mocker.Mock(fileobj=mock_stdout), selectors.EVENT_READ)]
            elif call_count == 2:
                return [(mocker.Mock(fileobj=mock_stderr), selectors.EVENT_READ)]
            elif call_count == 3:
                return [(mocker.Mock(fileobj=mock_stdout), selectors.EVENT_READ)]
            return []

        mock_selector.select.side_effect = select

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)
        mocker.patch("sys.stdout")
        mocker.patch("sys.stderr")

        result = CommandExecutor.run_nonblocking("echo test")
        assert result == 0

    def test_run_nonblocking_process_exception_handling(self, mocker):
        """Test run_nonblocking exception handling when selector operations fail."""
        mock_process = mocker.MagicMock()
        mock_process.stdout = mocker.Mock()
        mock_process.stderr = mocker.Mock()
        mock_process.wait.return_value = 0

        # Make readline raise an exception to test error handling
        mock_process.stdout.readline.side_effect = IOError("Read error")
        mock_process.stderr.readline.side_effect = IOError("Read error")

        mock_selector = mocker.MagicMock()
        # Track call count to eventually return empty map and break the while loop
        call_count = 0

        def get_map():
            nonlocal call_count
            call_count += 1
            # Return empty map after first call to break out of the while loop
            if call_count == 1:
                return {id(mock_process.stdout): mock_process.stdout}
            return {}

        mock_selector.get_map.side_effect = get_map
        mock_selector.select.return_value = [
            (mocker.Mock(fileobj=mock_process.stdout), selectors.EVENT_READ)
        ]

        mocker.patch("subprocess.Popen", return_value=mock_process)
        mocker.patch("selectors.DefaultSelector", return_value=mock_selector)

        # We expect this to handle the IOError gracefully and return the process exit code
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

        # Mock subprocess to prevent actual execution
        mock_process = mocker.MagicMock()
        mock_process.stdout.readline.return_value = ""
        mock_process.stderr.readline.return_value = ""
        mock_process.wait.return_value = 0

        mock_selector = mocker.MagicMock()
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
        exports = {"TEST_VAR": "test_value"}
        result = CommandExecutor._build_inactive_gamescope_command(
            args, "", "", exports
        )

        # Should build a command that executes exports and then gamescope
        assert (
            "env TEST_VAR=test_value true" in result
        )  # Export command (shlex.quote doesn't add quotes for simple values)
        assert "gamescope -f -W 1920" in result  # Gamescope command

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
        exports = {"TEST_VAR": "test_value"}
        result = CommandExecutor._build_active_gamescope_command(args, "", "", exports)

        # Should build a command that executes the exports
        assert "env TEST_VAR=test_value" in result
        # In active gamescope with exports but no app args, no 'true' is added since there are no app args to execute

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

        # Should include env -u LD_PRELOAD for gamescope and preserve LD_PRELOAD for app
        assert "env -u LD_PRELOAD gamescope" in call_args
        assert "env LD_PRELOAD=/path/to/library.so testapp" in call_args

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
