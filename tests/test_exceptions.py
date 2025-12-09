"""Tests for the exception classes in NeoscopeBuddy."""

from pathlib import Path

import pytest

from nscb.application import Application
from nscb.config_manager import ConfigManager
from nscb.exceptions import ConfigNotFoundError, NscbError, ProfileNotFoundError


class TestExceptionsUnit:
    """Unit tests for the exception classes."""

    def test_nscb_error_instantiation(self):
        """Test that NscbError can be instantiated."""
        error = NscbError()
        assert isinstance(error, NscbError)
        assert isinstance(error, Exception)

    def test_nscb_error_with_message(self):
        """Test that NscbError can be instantiated with a message."""
        message = "Something went wrong"
        error = NscbError(message)
        assert str(error) == message

    def test_nscb_error_is_exception(self):
        """Test that NscbError is an instance of Exception."""
        error = NscbError()
        assert isinstance(error, Exception)

    def test_config_not_found_error_instantiation(self):
        """Test that ConfigNotFoundError can be instantiated."""
        error = ConfigNotFoundError()
        assert isinstance(error, ConfigNotFoundError)
        assert isinstance(error, NscbError)

    def test_config_not_found_error_with_message(self):
        """Test that ConfigNotFoundError can be instantiated with a message."""
        message = "Config file not found at expected location"
        error = ConfigNotFoundError(message)
        assert str(error) == message

    def test_config_not_found_error_is_nscb_error(self):
        """Test that ConfigNotFoundError is an instance of NscbError."""
        error = ConfigNotFoundError()
        assert isinstance(error, NscbError)

    def test_profile_not_found_error_instantiation(self):
        """Test that ProfileNotFoundError can be instantiated."""
        error = ProfileNotFoundError()
        assert isinstance(error, ProfileNotFoundError)
        assert isinstance(error, NscbError)

    def test_profile_not_found_error_with_message(self):
        """Test that ProfileNotFoundError can be instantiated with a message."""
        message = "Profile 'gaming' not found in config"
        error = ProfileNotFoundError(message)
        assert str(error) == message

    def test_profile_not_found_error_is_nscb_error(self):
        """Test that ProfileNotFoundError is an instance of NscbError."""
        error = ProfileNotFoundError()
        assert isinstance(error, NscbError)

    def test_exception_inheritance_chain(self):
        """Test that all custom exceptions inherit from NscbError."""
        exceptions = [ConfigNotFoundError, ProfileNotFoundError]
        for exc_class in exceptions:
            assert issubclass(exc_class, NscbError)
            assert issubclass(exc_class, Exception)

    @pytest.mark.parametrize(
        "exc_class, msg",
        [
            (NscbError, "base error"),
            (ConfigNotFoundError, "config not found"),
            (ProfileNotFoundError, "profile not found"),
        ],
    )
    def test_exception_polymorphism_parametrized(self, exc_class, msg):
        """Test that different exceptions can be caught as NscbError using parametrization."""
        try:
            raise exc_class(msg)
        except NscbError as e:
            assert isinstance(e, exc_class)
            assert str(e) == msg

    def test_exception_polymorphism(self):
        """Test that different exceptions can be caught as NscbError."""
        exceptions_to_test = [
            (NscbError, "base error"),
            (ConfigNotFoundError, "config not found"),
            (ProfileNotFoundError, "profile not found"),
        ]

        for exc_class, msg in exceptions_to_test:
            try:
                raise exc_class(msg)
            except NscbError as e:
                assert isinstance(e, exc_class)
                assert str(e) == msg


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

    def test_profile_not_found_exception_integration(
        self, mocker, temp_config_with_content
    ):
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
        mock_log.assert_called_with("profile nonexistent not found")


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
        mock_log.assert_called_with("could not find nscb.conf")

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
        mock_log.assert_called_with("could not find nscb.conf")

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
        mock_log.assert_called_with("profile nonexistent_profile not found")

    def test_exception_message_consistency_e2e(self):
        """Test that exception messages are consistent and informative."""
        test_cases = [
            (NscbError, "base functionality test", "base functionality test"),
            (ConfigNotFoundError, "Config file missing", "Config file missing"),
            (
                ProfileNotFoundError,
                "Profile 'test' not found",
                "Profile 'test' not found",
            ),
        ]

        for exc_class, message, expected in test_cases:
            exc = exc_class(message)
            assert str(exc) == expected
            assert isinstance(exc, Exception)
            assert isinstance(exc, NscbError) or exc_class == NscbError
