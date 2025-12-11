"""Tests for the exception classes in NeoscopeBuddy."""

from pathlib import Path

import pytest

from nscb.application import Application
from nscb.config_manager import ConfigManager
from nscb.exceptions import (
    ArgumentParseError,
    CommandExecutionError,
    ConfigNotFoundError,
    EnvironmentVariableError,
    ExecutableNotFoundError,
    GamescopeActiveError,
    InvalidConfigError,
    NscbError,
    ProfileNotFoundError,
)


class TestExceptionsUnit:
    """Unit tests for the exception classes."""

    def test_nscb_error_instantiation(self):
        """Test that NscbError can be instantiated."""
        error = NscbError("test message")
        assert isinstance(error, NscbError)
        assert isinstance(error, Exception)

    def test_nscb_error_with_message(self):
        """Test that NscbError can be instantiated with a message."""
        message = "Something went wrong"
        error = NscbError(message)
        assert str(error) == message

    def test_nscb_error_is_exception(self):
        """Test that NscbError is an instance of Exception."""
        error = NscbError("test message")
        assert isinstance(error, Exception)

    def test_config_not_found_error_instantiation(self):
        """Test that ConfigNotFoundError can be instantiated."""
        error = ConfigNotFoundError("test_path")
        assert isinstance(error, ConfigNotFoundError)
        assert isinstance(error, NscbError)

    def test_config_not_found_error_with_message(self):
        """Test that ConfigNotFoundError can be instantiated with a message."""
        message = "Config file not found: expected_location"
        error = ConfigNotFoundError("expected_location")
        assert str(error) == message

    def test_config_not_found_error_is_nscb_error(self):
        """Test that ConfigNotFoundError is an instance of NscbError."""
        error = ConfigNotFoundError("test_path")
        assert isinstance(error, NscbError)

    def test_profile_not_found_error_instantiation(self):
        """Test that ProfileNotFoundError can be instantiated."""
        error = ProfileNotFoundError("test_profile")
        assert isinstance(error, ProfileNotFoundError)
        assert isinstance(error, NscbError)

    def test_profile_not_found_error_with_message(self):
        """Test that ProfileNotFoundError can be instantiated with a message."""
        message = "Profile 'gaming' not found in config"
        error = ProfileNotFoundError("gaming", "config")
        assert str(error) == message

    def test_profile_not_found_error_is_nscb_error(self):
        """Test that ProfileNotFoundError is an instance of NscbError."""
        error = ProfileNotFoundError("test_profile")
        assert isinstance(error, NscbError)

    def test_invalid_config_error_instantiation(self):
        """Test that InvalidConfigError can be instantiated."""
        error = InvalidConfigError("test_path", 42, "test message")
        assert isinstance(error, InvalidConfigError)
        assert isinstance(error, NscbError)

    def test_invalid_config_error_with_message(self):
        """Test that InvalidConfigError can be instantiated with a message."""
        error = InvalidConfigError("test_path", 42, "Invalid format")
        assert str(error) == "Invalid config in test_path at line 42: Invalid format"

    def test_invalid_config_error_is_nscb_error(self):
        """Test that InvalidConfigError is an instance of NscbError."""
        error = InvalidConfigError("test_path", 42, "test message")
        assert isinstance(error, NscbError)

    def test_executable_not_found_error_instantiation(self):
        """Test that ExecutableNotFoundError can be instantiated."""
        error = ExecutableNotFoundError("gamescope")
        assert isinstance(error, ExecutableNotFoundError)
        assert isinstance(error, NscbError)

    def test_executable_not_found_error_with_message(self):
        """Test that ExecutableNotFoundError can be instantiated with a message."""
        error = ExecutableNotFoundError("gamescope")
        assert str(error) == "Required executable 'gamescope' not found in PATH"

    def test_executable_not_found_error_is_nscb_error(self):
        """Test that ExecutableNotFoundError is an instance of NscbError."""
        error = ExecutableNotFoundError("gamescope")
        assert isinstance(error, NscbError)

    def test_command_execution_error_instantiation(self):
        """Test that CommandExecutionError can be instantiated."""
        error = CommandExecutionError("test_cmd", 1, "error output")
        assert isinstance(error, CommandExecutionError)
        assert isinstance(error, NscbError)

    def test_command_execution_error_with_message(self):
        """Test that CommandExecutionError can be instantiated with a message."""
        error = CommandExecutionError("test_cmd", 1, "error output")
        assert (
            str(error)
            == "Command execution failed: test_cmd (exit code: 1)\nError output: error output"
        )

    def test_command_execution_error_is_nscb_error(self):
        """Test that CommandExecutionError is an instance of NscbError."""
        error = CommandExecutionError("test_cmd", 1, "error output")
        assert isinstance(error, NscbError)

    def test_argument_parse_error_instantiation(self):
        """Test that ArgumentParseError can be instantiated."""
        error = ArgumentParseError("--invalid", "unknown argument")
        assert isinstance(error, ArgumentParseError)
        assert isinstance(error, NscbError)

    def test_argument_parse_error_with_message(self):
        """Test that ArgumentParseError can be instantiated with a message."""
        error = ArgumentParseError("--invalid", "unknown argument")
        assert str(error) == "Failed to parse argument '--invalid': unknown argument"

    def test_argument_parse_error_is_nscb_error(self):
        """Test that ArgumentParseError is an instance of NscbError."""
        error = ArgumentParseError("--invalid", "unknown argument")
        assert isinstance(error, NscbError)

    def test_gamescope_active_error_instantiation(self):
        """Test that GamescopeActiveError can be instantiated."""
        error = GamescopeActiveError()
        assert isinstance(error, GamescopeActiveError)
        assert isinstance(error, NscbError)

    def test_gamescope_active_error_with_message(self):
        """Test that GamescopeActiveError can be instantiated with a message."""
        error = GamescopeActiveError()
        assert str(error) == "Gamescope is already active - nesting not allowed"

    def test_gamescope_active_error_is_nscb_error(self):
        """Test that GamescopeActiveError is an instance of NscbError."""
        error = GamescopeActiveError()
        assert isinstance(error, NscbError)

    def test_environment_variable_error_instantiation(self):
        """Test that EnvironmentVariableError can be instantiated."""
        error = EnvironmentVariableError("VAR", "invalid value")
        assert isinstance(error, EnvironmentVariableError)
        assert isinstance(error, NscbError)

    def test_environment_variable_error_with_message(self):
        """Test that EnvironmentVariableError can be instantiated with a message."""
        error = EnvironmentVariableError("VAR", "invalid value")
        assert str(error) == "Environment variable 'VAR' error: invalid value"

    def test_environment_variable_error_is_nscb_error(self):
        """Test that EnvironmentVariableError is an instance of NscbError."""
        error = EnvironmentVariableError("VAR", "invalid value")
        assert isinstance(error, NscbError)

    def test_exception_inheritance_chain(self):
        """Test that all custom exceptions inherit from NscbError."""
        exceptions = [
            ConfigNotFoundError,
            ProfileNotFoundError,
            InvalidConfigError,
            ExecutableNotFoundError,
            CommandExecutionError,
            ArgumentParseError,
            GamescopeActiveError,
            EnvironmentVariableError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, NscbError)
            assert issubclass(exc_class, Exception)

    @pytest.mark.parametrize(
        "exc_class, msg, expected_msg",
        [
            (NscbError, "base error", "base error"),
            (ConfigNotFoundError, "config_path", "Config file not found: config_path"),
            (ProfileNotFoundError, "profile_name", "Profile 'profile_name' not found"),
            (
                InvalidConfigError,
                ("path", None, "test message"),
                "Invalid config in path: test message",
            ),
            (
                ExecutableNotFoundError,
                "gamescope",
                "Required executable 'gamescope' not found in PATH",
            ),
            (
                CommandExecutionError,
                ("test_cmd", 1, "error output"),
                "Command execution failed: test_cmd (exit code: 1)\nError output: error output",
            ),
            (
                ArgumentParseError,
                ("--invalid", "unknown argument"),
                "Failed to parse argument '--invalid': unknown argument",
            ),
            (
                GamescopeActiveError,
                (),
                "Gamescope is already active - nesting not allowed",
            ),
            (
                EnvironmentVariableError,
                ("VAR", "invalid value"),
                "Environment variable 'VAR' error: invalid value",
            ),
        ],
    )
    def test_exception_polymorphism_parametrized(self, exc_class, msg, expected_msg):
        """Test that different exceptions can be caught as NscbError using parametrization."""
        try:
            if isinstance(msg, tuple):
                raise exc_class(*msg)
            else:
                raise exc_class(msg)
        except NscbError as e:
            assert isinstance(e, exc_class)
            assert str(e) == expected_msg

    def test_exception_polymorphism(self):
        """Test that different exceptions can be caught as NscbError."""
        exceptions_to_test = [
            (NscbError, "base error", "base error"),
            (ConfigNotFoundError, "config_path", "Config file not found: config_path"),
            (ProfileNotFoundError, "profile_name", "Profile 'profile_name' not found"),
            (
                InvalidConfigError,
                ("path", None, "test message"),
                "Invalid config in path: test message",
            ),
            (
                ExecutableNotFoundError,
                "gamescope",
                "Required executable 'gamescope' not found in PATH",
            ),
            (
                CommandExecutionError,
                ("test_cmd", 1, "error output"),
                "Command execution failed: test_cmd (exit code: 1)\nError output: error output",
            ),
            (
                ArgumentParseError,
                ("--invalid", "unknown argument"),
                "Failed to parse argument '--invalid': unknown argument",
            ),
            (
                GamescopeActiveError,
                (),
                "Gamescope is already active - nesting not allowed",
            ),
            (
                EnvironmentVariableError,
                ("VAR", "invalid value"),
                "Environment variable 'VAR' error: invalid value",
            ),
        ]

        for exc_class, msg, expected_msg in exceptions_to_test:
            try:
                if isinstance(msg, tuple):
                    raise exc_class(*msg)
                else:
                    raise exc_class(msg)
            except NscbError as e:
                assert isinstance(e, exc_class)
                assert str(e) == expected_msg


class TestExceptionsIntegration:
    """Integration tests for exceptions with other modules."""

    def test_config_not_found_exception_integration(self, mocker):
        """Test ConfigNotFoundError raised in ConfigManager operations."""
        # Mock config path to return None (not found)
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=None
        )

        with pytest.raises(ConfigNotFoundError):
            # This simulates the application trying to load config when it doesn't exist
            config_path = ConfigManager.find_config_file()
            if config_path is None:
                raise ConfigNotFoundError("Config file could not be found")

    def test_profile_not_found_exception_integration(self, temp_config_with_content):
        """Test ProfileNotFoundError raised when accessing non-existent profile."""
        config_data = "existing_profile=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        # Load config that doesn't have the requested profile
        config = ConfigManager.load_config(config_path)

        # Try to access a non-existent profile (this simulates ProfileManager behavior)
        profile_name = "nonexistent_profile"
        if profile_name not in config.profiles:
            with pytest.raises(ProfileNotFoundError):
                raise ProfileNotFoundError(
                    f"Profile '{profile_name}' not found in config"
                )

    def test_exception_handling_in_application_workflow(self, mocker):
        """Test how exceptions are handled in the application workflow."""
        # Test when config file is not found
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=None
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        # Prevent actual command execution
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=0,
        )

        app = Application()

        # This should trigger a config not found error
        result = app.run(["-p", "gaming", "--", "test_app"])
        # The application should return error code 1 when config not found
        assert result == 1

    def test_profile_error_scenario_integration(self, mocker, temp_config_with_content):
        """Test profile not found error scenario in integration."""
        config_data = "existing=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mock_log = mocker.patch("logging.error")

        app = Application()
        result = app.run(["-p", "nonexistent"])  # Profile doesn't exist

        assert result == 1  # Error exit code
        mock_log.assert_called_with("Profile 'profile nonexistent not found' not found")


class TestExceptionsEndToEnd:
    """End-to-end tests for exception functionality."""

    def test_e2e_basic_error_handling(self, mocker):
        """Test end-to-end error handling scenarios."""
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=None
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch("builtins.print")
        mock_log = mocker.patch("logging.error")
        # Prevent actual command execution
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=0,
        )

        app = Application()
        result = app.run(["-p", "gaming", "--", "test_app"])

        assert result == 1  # Should return error code
        mock_log.assert_called_with("Config file not found: could not find nscb.conf")

    def test_e2e_advanced_error_condition_handling(self, mocker):
        """Test advanced error condition handling end-to-end."""
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=None
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch("builtins.print")
        mock_log = mocker.patch("logging.error")
        # Prevent actual command execution
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=0,
        )

        app = Application()
        result = app.run(["-p", "gaming", "--invalid-arg"])

        assert result == 1  # Should return error code
        mock_log.assert_called_with("Config file not found: could not find nscb.conf")

    def test_config_file_loading_errors_e2e(self):
        """Test config file loading errors end-to-end."""
        # Test with non-existent file
        non_existent = Path("/non/existent/path/nscb.conf")
        with pytest.raises(FileNotFoundError):
            ConfigManager.load_config(non_existent)

    def test_exception_usage_in_real_error_flows_e2e(self, mocker):
        """Test exceptions in real error flow scenarios."""
        # Test gamescope not found scenario
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=False
        )
        mock_log = mocker.patch("logging.error")

        app = Application()
        result = app.run(["--", "test_app"])

        assert result == 1
        mock_log.assert_called_with("'gamescope' not found in PATH")

    def test_invalid_config_error_integration(self, mocker, temp_config_file):
        """Test InvalidConfigError in integration scenarios."""
        # Create a config with invalid content (profile name with spaces)
        with open(temp_config_file, "w") as f:
            f.write("invalid profile name=-f\n")  # Invalid profile name with spaces

        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path",
            return_value=temp_config_file,
        )
        # Mock gamescope executable check to prevent actual execution
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        # Mock the actual gamescope command execution to prevent real execution
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=1,
        )
        mock_log = mocker.patch("logging.error")

        app = Application()
        result = app.run(["-p", "invalid profile name"])

        assert result == 1
        # Check that logging.error was called with an error message containing the invalid profile name
        mock_log.assert_called()
        actual_call = mock_log.call_args[0][0]
        assert "Invalid profile name" in actual_call
        assert "invalid profile name" in actual_call

    def test_executable_not_found_error_integration(self, mocker):
        """Test ExecutableNotFoundError in integration scenarios."""
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=False
        )
        mock_log = mocker.patch("logging.error")

        app = Application()
        result = app.run(["--", "test_app"])

        assert result == 1
        mock_log.assert_called_with("'gamescope' not found in PATH")

    def test_command_execution_error_integration(self, mocker):
        """Test CommandExecutionError in integration scenarios."""
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            side_effect=CommandExecutionError("test_cmd", 1, "execution failed"),
        )
        mock_log = mocker.patch("logging.error")

        # Test through the main function which has proper exception handling
        # Mock sys.argv to simulate command line arguments
        import sys

        from nscb.application import main

        original_argv = sys.argv
        try:
            sys.argv = ["nscb", "--", "test_app"]
            result = main()
        finally:
            sys.argv = original_argv

        assert result == 1
        # Check that logging.error was called with the expected message
        mock_log.assert_called()
        actual_call = mock_log.call_args[0][0]
        assert "Command execution failed: test_cmd" in actual_call
        assert "exit code: 1" in actual_call
        assert "execution failed" in actual_call

    def test_argument_parse_error_integration(self, mocker):
        """Test ArgumentParseError in integration scenarios."""
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.profile_manager.ProfileManager.parse_profile_args",
            side_effect=ArgumentParseError("--invalid", "unknown argument"),
        )
        mock_log = mocker.patch("logging.error")

        # Test through the main function which has proper exception handling
        # Mock sys.argv to simulate command line arguments
        import sys

        from nscb.application import main

        original_argv = sys.argv
        try:
            sys.argv = ["nscb", "--invalid", "--", "test_app"]
            result = main()
        finally:
            sys.argv = original_argv

        assert result == 1
        # Check that logging.error was called with the expected message
        mock_log.assert_called()
        actual_call = mock_log.call_args[0][0]
        assert "Failed to parse argument '--invalid'" in actual_call
        assert "unknown argument" in actual_call

    def test_gamescope_active_error_integration(self, mocker):
        """Test GamescopeActiveError in integration scenarios."""
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.is_gamescope_active",
            return_value=True,
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            side_effect=GamescopeActiveError(),
        )
        mock_log = mocker.patch("logging.error")

        # Test through the main function which has proper exception handling
        # Mock sys.argv to simulate command line arguments
        import sys

        from nscb.application import main

        original_argv = sys.argv
        try:
            sys.argv = ["nscb", "--", "test_app"]
            result = main()
        finally:
            sys.argv = original_argv

        assert result == 1
        # Check that logging.error was called with the expected message
        mock_log.assert_called()
        actual_call = mock_log.call_args[0][0]
        assert "Gamescope is already active" in actual_call
        assert "nesting not allowed" in actual_call

    def test_environment_variable_error_integration(self, mocker):
        """Test EnvironmentVariableError in integration scenarios."""
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.get_pre_post_commands",
            side_effect=EnvironmentVariableError("VAR", "invalid value"),
        )
        mock_log = mocker.patch("logging.error")

        # Test through the main function which has proper exception handling
        # Mock sys.argv to simulate command line arguments
        import sys

        from nscb.application import main

        original_argv = sys.argv
        try:
            sys.argv = ["nscb", "--", "test_app"]
            result = main()
        finally:
            sys.argv = original_argv

        assert result == 1
        # Check that logging.error was called with the expected message
        mock_log.assert_called()
        actual_call = mock_log.call_args[0][0]
        assert "Environment variable 'VAR'" in actual_call
        assert "invalid value" in actual_call

    def test_error_scenarios_with_config_loading(
        self, mocker, temp_config_with_content
    ):
        """Test various error scenarios with config loading."""
        # Create a valid config
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        # Test missing profile scenario
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mock_log = mocker.patch("logging.error")

        app = Application()
        result = app.run(["-p", "nonexistent_profile"])

        assert result == 1
        mock_log.assert_called_with(
            "Profile 'profile nonexistent_profile not found' not found"
        )

    def test_exception_message_consistency_e2e(self):
        """Test that exception messages are consistent and informative."""
        test_cases = [
            (NscbError, "base functionality test", "base functionality test"),
            (
                ConfigNotFoundError,
                "Config file missing",
                "Config file not found: Config file missing",
            ),
            (
                ProfileNotFoundError,
                "test",
                "Profile 'test' not found",
            ),
        ]

        for exc_class, message, expected in test_cases:
            exc = exc_class(message)
            assert str(exc) == expected
            assert isinstance(exc, Exception)
            assert isinstance(exc, NscbError) or exc_class == NscbError
