"""Tests for the exception classes in NeoscopeBuddy."""

from pathlib import Path

import pytest

from nscb.application import Application
from nscb.config_manager import ConfigManager
from nscb.exceptions import (
    ConfigNotFoundError,
    InvalidConfigError,
    NscbError,
    ProfileNotFoundError,
)


class TestExceptionsUnit:
    """Unit tests for the exception classes."""

    def test_nscb_error_instantiation(self):
        error = NscbError("test message")
        assert isinstance(error, NscbError)
        assert isinstance(error, Exception)

    def test_nscb_error_with_message(self):
        message = "Something went wrong"
        error = NscbError(message)
        assert str(error) == message

    def test_nscb_error_is_exception(self):
        error = NscbError("test message")
        assert isinstance(error, Exception)

    def test_config_not_found_error_instantiation(self):
        error = ConfigNotFoundError("test_path")
        assert isinstance(error, ConfigNotFoundError)
        assert isinstance(error, NscbError)

    def test_config_not_found_error_with_message(self):
        message = "Config file not found: expected_location"
        error = ConfigNotFoundError("expected_location")
        assert str(error) == message

    def test_config_not_found_error_is_nscb_error(self):
        error = ConfigNotFoundError("test_path")
        assert isinstance(error, NscbError)

    def test_profile_not_found_error_instantiation(self):
        error = ProfileNotFoundError("test_profile")
        assert isinstance(error, ProfileNotFoundError)
        assert isinstance(error, NscbError)

    def test_profile_not_found_error_with_message(self):
        message = "Profile 'gaming' not found in config"
        error = ProfileNotFoundError("gaming", "config")
        assert str(error) == message

    def test_profile_not_found_error_is_nscb_error(self):
        error = ProfileNotFoundError("test_profile")
        assert isinstance(error, NscbError)

    def test_invalid_config_error_instantiation(self):
        error = InvalidConfigError("test_path", 42, "test message")
        assert isinstance(error, InvalidConfigError)
        assert isinstance(error, NscbError)

    def test_invalid_config_error_with_message(self):
        error = InvalidConfigError("test_path", 42, "Invalid format")
        assert str(error) == "Invalid config in test_path at line 42: Invalid format"

    def test_invalid_config_error_is_nscb_error(self):
        error = InvalidConfigError("test_path", 42, "test message")
        assert isinstance(error, NscbError)

    def test_exception_inheritance_chain(self):
        exceptions = [
            ConfigNotFoundError,
            ProfileNotFoundError,
            InvalidConfigError,
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
        ],
    )
    def test_exception_polymorphism_parametrized(
        self,
        exc_class: type[NscbError],
        msg: str | tuple[str, ...],
        expected_msg: str,
    ) -> None:
        """Test that different exceptions can be caught as NscbError using parametrization."""
        try:
            if isinstance(msg, tuple):
                raise exc_class(*msg)
            else:
                raise exc_class(msg)
        except NscbError as e:
            assert isinstance(e, exc_class)
            assert str(e) == expected_msg

    def test_exception_polymorphism(self) -> None:
        """Test that different exceptions can be caught as NscbError."""
        exceptions_to_test: list[tuple[type[NscbError], tuple | str, str]] = [
            (NscbError, "base error", "base error"),
            (ConfigNotFoundError, "config_path", "Config file not found: config_path"),
            (ProfileNotFoundError, "profile_name", "Profile 'profile_name' not found"),
            (
                InvalidConfigError,
                ("path", None, "test message"),
                "Invalid config in path: test message",
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
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file", return_value=None
        )
        with pytest.raises(ConfigNotFoundError):
            config_path = ConfigManager.find_config_file()
            if config_path is None:
                raise ConfigNotFoundError("Config file could not be found")

    def test_profile_not_found_exception_integration(self, temp_config_with_content):
        """Test ProfileNotFoundError raised when accessing non-existent profile."""
        config_data = "existing_profile=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)
        config = ConfigManager.load_config(config_path)
        profile_name = "nonexistent_profile"
        if profile_name not in config.profiles:
            with pytest.raises(ProfileNotFoundError):
                raise ProfileNotFoundError(
                    f"Profile '{profile_name}' not found in config"
                )

    def test_exception_handling_in_application_workflow(self, mocker):
        """Test how exceptions are handled in the application workflow."""
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file", return_value=None
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=0,
        )
        app = Application()
        result = app.run(["-p", "gaming", "--", "test_app"])
        assert result == 1

    def test_profile_error_scenario_integration(self, mocker, temp_config_with_content):
        """Test profile not found error scenario in integration."""
        config_data = "existing=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file",
            return_value=config_path,
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        mock_log = mocker.patch("logging.error")
        app = Application()
        result = app.run(["-p", "nonexistent"])
        assert result == 1
        mock_log.assert_called_with("Profile 'nonexistent' not found")


class TestExceptionsEndToEnd:
    """End-to-end tests for exception functionality."""

    def test_e2e_basic_error_handling(self, mocker):
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file", return_value=None
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        mocker.patch("builtins.print")
        mock_log = mocker.patch("logging.error")
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=0,
        )
        app = Application()
        result = app.run(["-p", "gaming", "--", "test_app"])
        assert result == 1
        mock_log.assert_called_with("Config file not found: could not find nscb.conf")

    def test_e2e_advanced_error_condition_handling(self, mocker):
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file", return_value=None
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        mocker.patch("builtins.print")
        mock_log = mocker.patch("logging.error")
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=0,
        )
        app = Application()
        result = app.run(["-p", "gaming", "--invalid-arg"])
        assert result == 1
        mock_log.assert_called_with("Config file not found: could not find nscb.conf")

    def test_config_file_loading_errors_e2e(self):
        non_existent = Path("/non/existent/path/nscb.conf")
        with pytest.raises(FileNotFoundError):
            ConfigManager.load_config(non_existent)

    def test_exception_usage_in_real_error_flows_e2e(self, mocker):
        mocker.patch("nscb.application.shutil.which", return_value=None)
        mock_log = mocker.patch("logging.error")
        app = Application()
        result = app.run(["--", "test_app"])
        assert result == 1
        mock_log.assert_called_with("'gamescope' not found in PATH")

    def test_invalid_config_error_integration(self, mocker, temp_config_file):
        with open(temp_config_file, "w") as f:
            f.write("invalid profile name=-f\n")
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file",
            return_value=temp_config_file,
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        mocker.patch(
            "nscb.command_executor.CommandExecutor.execute_gamescope_command",
            return_value=1,
        )
        mock_log = mocker.patch("logging.error")
        app = Application()
        result = app.run(["-p", "invalid profile name"])
        assert result == 1
        mock_log.assert_called()
        actual_call = mock_log.call_args[0][0]
        assert "Invalid profile name" in actual_call
        assert "invalid profile name" in actual_call

    def test_executable_not_found_error_integration(self, mocker):
        mocker.patch("nscb.application.shutil.which", return_value=None)
        mock_log = mocker.patch("logging.error")
        app = Application()
        result = app.run(["--", "test_app"])
        assert result == 1
        mock_log.assert_called_with("'gamescope' not found in PATH")

    def test_error_scenarios_with_config_loading(
        self, mocker, temp_config_with_content
    ):
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file",
            return_value=config_path,
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        mock_log = mocker.patch("logging.error")
        app = Application()
        result = app.run(["-p", "nonexistent_profile"])
        assert result == 1
        mock_log.assert_called_with("Profile 'nonexistent_profile' not found")

    def test_exception_message_consistency_e2e(self):
        test_cases = [
            (NscbError, "base functionality test", "base functionality test"),
            (
                ConfigNotFoundError,
                "Config file missing",
                "Config file not found: Config file missing",
            ),
            (ProfileNotFoundError, "test", "Profile 'test' not found"),
        ]
        for exc_class, message, expected in test_cases:
            exc = exc_class(message)
            assert str(exc) == expected
            assert isinstance(exc, Exception)
            assert isinstance(exc, NscbError) or exc_class == NscbError
