"""Tests for the configuration management functionality in NeoscopeBuddy."""

from pathlib import Path

import pytest

from nscb.application import Application
from nscb.config_manager import ConfigManager
from nscb.config_result import ConfigResult
from nscb.profile_manager import ProfileManager


class TestConfigManagerUnit:
    """Unit tests for the ConfigManager class."""

    def test_find_config_file_xdg_exists(self, xdg_config_scenarios):
        """Test finding config file when XDG_CONFIG_HOME exists using xdg_config_scenarios fixture."""
        config_path = xdg_config_scenarios["xdg_exists"]()
        result = ConfigManager.find_config_file()
        assert result == config_path

    def test_find_config_file_xdg_missing_fallback(self, xdg_config_scenarios):
        """Test finding config file with XDG fallback to HOME using xdg_config_scenarios fixture."""
        config_path = xdg_config_scenarios["home_fallback"]()
        result = ConfigManager.find_config_file()
        assert result == config_path

    def test_find_config_file_home_only(self, xdg_config_scenarios):
        """Test finding config file when only HOME/.config exists using xdg_config_scenarios fixture."""
        config_path = xdg_config_scenarios["home_only"]()
        result = ConfigManager.find_config_file()
        assert result == config_path

    def test_find_config_file_no_config(self, xdg_config_scenarios):
        """Test finding config file when no config exists using xdg_config_scenarios fixture."""
        xdg_config_scenarios["no_config"]()
        result = ConfigManager.find_config_file()
        assert result is None

    def test_config_file_loading_with_mock_config_file_fixture(
        self, mock_config_file, temp_config_file
    ):
        """
        Test config file loading using mock_config_file fixture.

        This demonstrates how to use the mock_config_file fixture to simplify
        config file testing by automatically handling file creation and mocking.
        """
        # Setup config content using the fixture
        config_content = "gaming=-f -W 1920 -H 1080\nexport DISPLAY=:0\n"
        mock_config = mock_config_file(config_content)

        # The fixture automatically creates the file and mocks find_config_file
        # Now we can test finding and loading the config
        found_path = ConfigManager.find_config_file()
        if found_path:
            result = ConfigManager.load_config(found_path)
        else:
            result = None

        # Verify the config was loaded correctly
        if result:
            assert "gaming" in result.profiles
            assert result.profiles["gaming"] == "-f -W 1920 -H 1080"
            assert "DISPLAY" in result.exports
            assert result.exports["DISPLAY"] == ":0"
        else:
            assert False, "Config file should have been found"

        # Verify the mock was called
        mock_config.assert_called_once()

    def test_config_parsing_with_standard_content_using_test_config_content(
        self, test_config_content, temp_config_with_content
    ):
        """
        Test config parsing using test_config_content fixture.

        This demonstrates how to use the test_config_content fixture to test
        various configuration parsing scenarios with standard content.
        """
        # Test basic config parsing
        basic_config = test_config_content["basic"]
        config_path = temp_config_with_content(basic_config)
        result = ConfigManager.load_config(config_path)

        assert "gaming" in result.profiles
        assert result.profiles["gaming"] == "-f -W 1920 -H 1080"
        assert "streaming" in result.profiles
        assert result.profiles["streaming"] == "--borderless -W 1280 -H 720"

        # Test config with exports
        exports_config = test_config_content["with_exports"]
        config_path = temp_config_with_content(exports_config)
        result = ConfigManager.load_config(config_path)

        assert "gaming" in result.profiles
        assert "DISPLAY" in result.exports
        assert result.exports["DISPLAY"] == ":0"
        assert "MANGOHUD" in result.exports
        assert result.exports["MANGOHUD"] == "1"

        # Test complex config with comments and quotes
        complex_config = test_config_content["complex"]
        config_path = temp_config_with_content(complex_config)
        result = ConfigManager.load_config(config_path)

        assert "gaming" in result.profiles
        assert "streaming" in result.profiles
        assert "portable" in result.profiles
        assert "DISPLAY" in result.exports
        assert "MANGOHUD" in result.exports
        assert "CUSTOM_VAR" in result.exports
        assert result.exports["CUSTOM_VAR"] == "value with spaces"

    def test_find_config_file_permission_error(self, mocker, monkeypatch):
        mocker.patch.object(Path, "exists", return_value=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)

        result = ConfigManager.find_config_file()
        assert result is None

    @pytest.mark.parametrize(
        "content,expected",
        [
            (
                "gaming=-f -W 1920 -H 1080\nstreaming=--borderless -w 1280 -h 720\n",
                {
                    "gaming": "-f -W 1920 -H 1080",
                    "streaming": "--borderless -w 1280 -h 720",
                },
            ),
            (
                "gaming=\"-f -W 1920 -H 1080\"\nstreaming='--borderless -w 1280 -h 720'\n",
                {
                    "gaming": "-f -W 1920 -H 1080",
                    "streaming": "--borderless -w 1280 -h 720",
                },
            ),
            (
                "# This is a comment\n\ngaming=-f -W 1920 -H 1080\n# Another comment\n\nstreaming=--borderless\n",
                {"gaming": "-f -W 1920 -H 1080", "streaming": "--borderless"},
            ),
            (
                'gaming="-f -W 1920 -H 1080"\nspecial="test \'nested quotes\' here"\n',
                {
                    "gaming": "-f -W 1920 -H 1080",
                    "special": "test 'nested quotes' here",
                },
            ),
            ("", {}),
        ],
    )
    def test_load_config_variations(self, temp_config_with_content, content, expected):
        config_path = temp_config_with_content(content)
        result = ConfigManager.load_config(config_path)
        assert result.profiles == expected

    def test_load_config_invalid_formats(self, temp_config_file):
        with open(temp_config_file, "w") as f:
            f.write("invalid_line_without_equals_sign\n")

        # The function should handle this gracefully, not raise ValueError
        result = ConfigManager.load_config(temp_config_file)
        # Since there's no '=' in the line, the result would be an empty dict
        assert result.profiles == {}

        temp_config_file2 = temp_config_file.parent / "nscb2.conf"
        with open(temp_config_file2, "w") as f:
            f.write("multiple_equals=value=another_value\n")

        result = ConfigManager.load_config(temp_config_file2)
        expected = {"multiple_equals": "value=another_value"}
        assert result.profiles == expected

    def test_load_config_file_reading_errors(self):
        non_existent = Path("/non/existent/path/nscb.conf")
        with pytest.raises(FileNotFoundError):
            ConfigManager.load_config(non_existent)

    def test_load_config_malformed_config(self, temp_config_with_content):
        content = "gaming=-f -W 1920 -H 1080\n=\n=empty_key\nvalid=value\n"
        config_path = temp_config_with_content(content)
        result = ConfigManager.load_config(config_path)
        # Should return a ConfigResult which has dict-like behavior for profiles
        assert hasattr(result, "profiles") and isinstance(result.profiles, dict)

    @pytest.mark.parametrize(
        "content,expected_profiles,expected_exports",
        [
            # Basic export functionality
            (
                "export SOME_VAR=value\ngaming=-f",
                {"gaming": "-f"},
                {"SOME_VAR": "value"},
            ),
            # Multiple exports
            (
                "export VAR1=value1\nexport VAR2=value2\ngaming=-f",
                {"gaming": "-f"},
                {"VAR1": "value1", "VAR2": "value2"},
            ),
            # Export with quotes
            (
                'export QUOTED_VAR="quoted value here"\nstreaming=--borderless',
                {"streaming": "--borderless"},
                {"QUOTED_VAR": "quoted value here"},
            ),
            # Mixed profiles and exports
            (
                "gaming=-f -W 1920\nexport DISPLAY=:0\nstreaming=--borderless\nexport WAYLAND_DISPLAY=wayland-0",
                {"gaming": "-f -W 1920", "streaming": "--borderless"},
                {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"},
            ),
            # Export only config (no profiles)
            (
                "export ONLY_VAR=value\nexport ANOTHER_VAR=test",
                {},
                {"ONLY_VAR": "value", "ANOTHER_VAR": "test"},
            ),
            # Profile only config (no exports)
            (
                "gaming=-f\nstreaming=--borderless",
                {"gaming": "-f", "streaming": "--borderless"},
                {},
            ),
            # Empty config with exports
            ("export EMPTY_VAR=", {}, {"EMPTY_VAR": ""}),
        ],
    )
    def test_load_config_with_exports(
        self, temp_config_with_content, content, expected_profiles, expected_exports
    ):
        """Test loading config with export statements."""
        config_path = temp_config_with_content(content)
        result = ConfigManager.load_config(config_path)
        assert result.profiles == expected_profiles
        assert result.exports == expected_exports


class TestConfigManagerSecurity:
    """Security and validation tests for ConfigManager."""

    def test_file_size_validation(self, temp_config_file):
        """Test that large config files are rejected (DoS prevention)."""
        # Create a file larger than 10MB
        large_content = "a" * (11 * 1024 * 1024)  # 11MB
        with open(temp_config_file, "w") as f:
            f.write(large_content)

        with pytest.raises(Exception) as exc_info:
            ConfigManager.load_config(temp_config_file)

        assert "Config file too large" in str(exc_info.value)

    def test_line_length_validation(self, temp_config_file):
        """Test that excessively long lines are rejected."""
        # Create a line longer than 10KB
        long_line = "b" * 10001 + "=value\n"
        with open(temp_config_file, "w") as f:
            f.write(long_line)

        with pytest.raises(Exception) as exc_info:
            ConfigManager.load_config(temp_config_file)

        assert "Line too long" in str(exc_info.value)

    def test_invalid_env_var_names(self, temp_config_file):
        """Test validation of environment variable names."""
        invalid_names = [
            "123invalid",  # Starts with number
            "invalid-name",  # Contains hyphen
            "invalid name",  # Contains space
            "PATH",  # Reserved name
            "HOME",  # Reserved name
            "LD_PRELOAD",  # Reserved name
            "NSCB_VAR",  # Reserved prefix
        ]

        for invalid_name in invalid_names:
            with open(temp_config_file, "w") as f:
                f.write(f"export {invalid_name}=value\n")

            with pytest.raises(Exception) as exc_info:
                ConfigManager.load_config(temp_config_file)

            assert "Invalid environment variable name" in str(exc_info.value)

    def test_invalid_profile_names(self, temp_config_file):
        """Test validation of profile names."""
        invalid_names = [
            "invalid name",  # Contains space
            "invalid/name",  # Contains slash
            "help",  # Reserved name (case insensitive)
            "HELP",  # Reserved name (case insensitive)
            "debug",  # Reserved name
            "DEBUG",  # Reserved name
            "test",  # Reserved name
            "config",  # Reserved name
            "export",  # Reserved name
            "env",  # Reserved name
        ]

        for invalid_name in invalid_names:
            with open(temp_config_file, "w") as f:
                f.write(f"{invalid_name}=-f\n")

            with pytest.raises(Exception) as exc_info:
                ConfigManager.load_config(temp_config_file)

            assert "Invalid profile name" in str(exc_info.value)

    def test_empty_key_handling(self, temp_config_file):
        """Test handling of empty keys in config."""
        with open(temp_config_file, "w") as f:
            f.write("=value\n")

        # Should handle gracefully without raising exception
        result = ConfigManager.load_config(temp_config_file)
        assert result.profiles == {}  # Empty keys should be ignored

    def test_unicode_decode_error(self, temp_config_file):
        """Test handling of Unicode decode errors."""
        # Write invalid UTF-8 content
        with open(temp_config_file, "wb") as f:
            f.write(b"\xff\xfeinvalid utf-8 content\n")

        with pytest.raises(Exception) as exc_info:
            ConfigManager.load_config(temp_config_file)

        assert "Invalid file encoding" in str(exc_info.value)

    def test_command_injection_detection(self, temp_config_file):
        """Test detection of command injection attempts."""
        dangerous_values = [
            "value; rm -rf /",
            "value && echo hacked",
            "value || exit 1",
            "value `whoami`",
            "value $(whoami)",
            "value ${HOME}",
        ]

        for dangerous_value in dangerous_values:
            with open(temp_config_file, "w") as f:
                f.write(f"profile={dangerous_value}\n")

            # Command injection attempts should be skipped gracefully
            result = ConfigManager.load_config(temp_config_file)
            assert result.profiles == {}  # Invalid entries are skipped

    def test_reserved_env_var_names(self, temp_config_file):
        """Test that reserved environment variable names are rejected."""
        reserved_vars = ["PATH", "HOME", "USER", "SHELL", "LD_PRELOAD"]

        for var_name in reserved_vars:
            with open(temp_config_file, "w") as f:
                f.write(f"export {var_name}=value\n")

            with pytest.raises(Exception) as exc_info:
                ConfigManager.load_config(temp_config_file)

            assert "Invalid environment variable name" in str(exc_info.value)

    def test_reserved_profile_names(self, temp_config_file):
        """Test that reserved profile names are rejected."""
        reserved_profiles = ["help", "debug", "test", "config", "export", "env"]

        for profile_name in reserved_profiles:
            with open(temp_config_file, "w") as f:
                f.write(f"{profile_name}=-f\n")

            with pytest.raises(Exception) as exc_info:
                ConfigManager.load_config(temp_config_file)

            assert "Invalid profile name" in str(exc_info.value)

    def test_nscb_prefix_reserved(self, temp_config_file):
        """Test that NSCB_ prefix is reserved for environment variables."""
        with open(temp_config_file, "w") as f:
            f.write("export NSCB_CUSTOM_VAR=value\n")

        with pytest.raises(Exception) as exc_info:
            ConfigManager.load_config(temp_config_file)

        assert "Invalid environment variable name" in str(exc_info.value)

    def test_quoted_profile_names(self, temp_config_file):
        """Test handling of quoted profile names."""
        with open(temp_config_file, "w") as f:
            f.write('"quoted-profile"=-f\n')
            f.write("'another-profile'=--borderless\n")

        result = ConfigManager.load_config(temp_config_file)
        assert "quoted-profile" in result.profiles
        assert "another-profile" in result.profiles

    def test_malformed_export_lines(self, temp_config_file):
        """Test handling of malformed export lines."""
        with open(temp_config_file, "w") as f:
            f.write("export\n")  # No variable name
            f.write("export =")  # No variable name
            f.write("export VAR")  # No equals sign

        # These should raise exceptions as expected
        with pytest.raises(Exception):
            ConfigManager.load_config(temp_config_file)

    def test_mixed_valid_invalid_config(self, temp_config_file):
        """Test that invalid entries cause the entire config to fail."""
        with open(temp_config_file, "w") as f:
            f.write("valid_profile=-f\n")
            f.write("export VALID_VAR=value\n")
            f.write("invalid_profile_name=-f\n")  # This should cause failure
            f.write("export 123INVALID=value\n")  # This should cause failure

        # Should raise exception due to invalid entries
        with pytest.raises(Exception):
            ConfigManager.load_config(temp_config_file)


class TestConfigResultUnit:
    """Unit tests for the ConfigResult container."""

    def test_config_result_initialization(self):
        profiles = {"gaming": "-f -W 1920"}
        exports = {"VAR": "value"}
        result = ConfigResult(profiles, exports)
        assert result.profiles == profiles
        assert result.exports == exports

    def test_config_result_contains_method(self):
        profiles = {"gaming": "-f -W 1920"}
        result = ConfigResult(profiles, {})
        assert "gaming" in result
        assert "nonexistent" not in result

    def test_config_result_getitem_method(self):
        profiles = {"gaming": "-f -W 1920"}
        result = ConfigResult(profiles, {})
        assert result["gaming"] == "-f -W 1920"

    def test_config_result_get_method(self):
        profiles = {"gaming": "-f -W 1920"}
        result = ConfigResult(profiles, {})
        assert result.get("gaming") == "-f -W 1920"
        assert result.get("nonexistent") is None
        assert result.get("nonexistent", "default") == "default"

    def test_config_result_keys_values_items(self):
        profiles = {"gaming": "-f -W 1920", "streaming": "--borderless -W 1280"}
        result = ConfigResult(profiles, {})

        assert set(result.keys()) == {"gaming", "streaming"}
        assert set(result.values()) == {"-f -W 1920", "--borderless -W 1280"}
        assert set(result.items()) == {
            ("gaming", "-f -W 1920"),
            ("streaming", "--borderless -W 1280"),
        }

    def test_config_result_equality_with_dict(self):
        profiles = {"gaming": "-f -W 1920"}
        result = ConfigResult(profiles, {})
        assert result == profiles
        assert result != {"different": "content"}


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager with other modules."""

    def test_config_manager_profile_manager_workflow(
        self, mocker, temp_config_with_content
    ):
        """Test ConfigManager and ProfileManager working together."""
        config_data = "performance=-f -W 2560 -H 1440 --mangoapp\n"
        config_path = temp_config_with_content(config_data)

        # Mock config loading
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )

        # Test the config manager loading the config
        config = ConfigManager.load_config(config_path)
        assert "performance" in config.profiles
        assert config.profiles["performance"] == "-f -W 2560 -H 1440 --mangoapp"

        # Now test with real ProfileManager
        profiles, _remaining_args = ProfileManager.parse_profile_args(
            ["-p", "performance", "--borderless", "--", "app"]
        )
        assert profiles == ["performance"]

        # Test that we can merge profile args with overrides
        result = ProfileManager.merge_arguments(
            ["-f", "-W", "2560", "-H", "1440", "--mangoapp"],
            ["--borderless", "-W", "3200"],
        )
        assert "--borderless" in result
        assert "-f" not in result
        assert "3200" in result  # Overridden width
        assert "--mangoapp" in result  # Preserved from profile

    def test_config_manager_application_integration(
        self, mocker, temp_config_with_content
    ):
        """Test ConfigManager working as part of the full application workflow."""
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        # Set up application with real ConfigManager
        app = Application()

        # Mock executable detection
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # Run the app with a profile to test config loading
        result = app.run(["-p", "gaming", "--", "test_app"])

        assert result == 0
        assert mock_run.called


class TestConfigManagerEndToEnd:
    """End-to-end tests for ConfigManager functionality."""

    def test_profile_config_format_variations_e2e(self):
        import os
        import tempfile

        config_data = """# Performance profile
performance="-f -W 2560 -H 1440"

# Compatibility profile with mixed quotes
"compatibility"=-W 1280 -H 720

# Empty line above this line

# Profile with no value
empty_profile=
# Another profile
gaming=--borderless -W 1920 -H 1080
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as temp_file:
            temp_file.write(config_data)
            temp_config_path = temp_file.name

        try:
            config = ConfigManager.load_config(Path(temp_config_path))

            assert "performance" in config.profiles
            assert config.profiles["performance"] == "-f -W 2560 -H 1440"
            assert "gaming" in config.profiles
            assert config.profiles["gaming"] == "--borderless -W 1920 -H 1080"
            assert "empty_profile" in config.profiles
            assert config.profiles["empty_profile"] == ""

            compat_key_found = (
                "compatibility" in config.profiles
                or '"compatibility"' in config.profiles
            )
            assert compat_key_found

            compat_key = (
                "compatibility"
                if "compatibility" in config.profiles
                else '"compatibility"'
            )
            assert config.profiles[compat_key] == "-W 1280 -H 720"
        finally:
            os.unlink(temp_config_path)

    def test_profile_loading_real_workflow_e2e(self, mocker, temp_config_with_content):
        config_data = (
            "# Complex config with various settings\n"
            "performance=-f -W 2560 -H 1440 --mangoapp\n"
            "quality=--borderless -W 1920 -H 1080 --framerate-limit=60\n"
            "balanced=-W 1920 -H 1080 --fsr-sharpness 8\n"
        )

        config_path = temp_config_with_content(config_data)

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
        mocker.patch("sys.argv", ["nscb", "-p", "performance", "-W", "3200"])

        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        app = Application()
        result = app.run(["-p", "performance", "-W", "3200"])

        assert result == 0

        called_cmd = mock_run.call_args[0][0]
        assert "gamescope" in called_cmd
        assert "-f" in called_cmd
        assert "3200" in called_cmd
        assert "--mangoapp" in called_cmd
