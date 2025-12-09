"""Tests for the configuration management functionality in NeoscopeBuddy."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import nscb modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from nscb.application import Application
from nscb.config_manager import ConfigManager
from nscb.config_result import ConfigResult
from nscb.profile_manager import ProfileManager


class TestConfigManagerUnit:
    """Unit tests for the ConfigManager class."""

    def test_find_config_file_xdg_exists(self, temp_config_file, monkeypatch):
        with open(temp_config_file, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_file.parent))
        monkeypatch.delenv("HOME", raising=False)

        result = ConfigManager.find_config_file()
        assert result == temp_config_file

    def test_find_config_file_xdg_missing_fallback(self, temp_config_file, monkeypatch):
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent")
        monkeypatch.setenv("HOME", str(home_config_dir))

        result = ConfigManager.find_config_file()
        assert result == config_path

    def test_find_config_file_home_only(self, temp_config_file, monkeypatch):
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_config_dir))

        result = ConfigManager.find_config_file()
        assert result == config_path

    def test_find_config_file_no_config(self, monkeypatch):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)

        result = ConfigManager.find_config_file()
        assert result is None

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
        profiles, remaining_args = ProfileManager.parse_profile_args(
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
