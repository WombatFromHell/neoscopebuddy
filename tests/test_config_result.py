"""Tests for the config result container in NeoscopeBuddy."""

import pytest

from nscb.application import Application
from nscb.config_manager import ConfigManager
from nscb.config_result import ConfigResult, ProfileEntry


class TestConfigResultUnit:
    """Unit tests for the ConfigResult container."""

    def test_config_result_initialization(self):
        profiles = {"gaming": ProfileEntry("-f -W 1920")}
        exports = {"VAR": "value"}
        result = ConfigResult(profiles, exports)
        assert result.profiles == profiles
        assert result.exports == exports

    @pytest.mark.parametrize(
        "profiles,exports,expected_profiles,expected_exports",
        [
            (
                {"gaming": ProfileEntry("-f -W 1920")},
                {},
                {"gaming": ProfileEntry("-f -W 1920")},
                {},
            ),
            ({}, {"VAR": "value"}, {}, {"VAR": "value"}),
            (
                {"gaming": ProfileEntry("-f -W 1920")},
                {"VAR": "value"},
                {"gaming": ProfileEntry("-f -W 1920")},
                {"VAR": "value"},
            ),
            ({}, {}, {}, {}),
        ],
    )
    def test_config_result_initialization_parametrized(
        self, profiles, exports, expected_profiles, expected_exports
    ):
        result = ConfigResult(profiles, exports)
        assert result.profiles == expected_profiles
        assert result.exports == expected_exports


class TestConfigResultIntegration:
    """Integration tests for ConfigResult with other modules."""

    def test_config_result_config_manager_integration(self, temp_config_with_content):
        """Test ConfigResult working with ConfigManager for config loading."""
        config_data = "gaming=-f -W 1920 -H 1080\nexport DISPLAY=:0\n"
        config_path = temp_config_with_content(config_data)

        # Load config using ConfigManager which returns ConfigResult
        result = ConfigManager.load_config(config_path)

        # Verify it's a ConfigResult instance
        assert isinstance(result, ConfigResult)

        # Verify content
        assert "gaming" in result.profiles
        assert result.profiles["gaming"].args == "-f -W 1920 -H 1080"
        assert "DISPLAY" in result.exports
        assert result.exports["DISPLAY"] == ":0"

    def test_config_result_profile_manager_integration(
        self, mocker, temp_config_with_content
    ):
        """Test ConfigResult used in ProfileManager workflow."""
        config_data = "performance=-f -W 2560 -H 1440 --mangoapp\n"
        config_path = temp_config_with_content(config_data)

        # Mock the config loading
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file",
            return_value=config_path,
        )

        # Load the config
        config_result = ConfigManager.load_config(config_path)

        # Use the config result to get profile data for ProfileManager
        entry = config_result.profiles.get("performance")
        profile_args = entry.args.split() if entry else []

        # Verify we got the expected args
        assert "-f" in profile_args
        assert "2560" in profile_args
        assert "--mangoapp" in profile_args

    def test_config_result_application_workflow_integration(
        self, mocker, temp_config_with_content
    ):
        """Test ConfigResult as part of the full application workflow."""
        config_data = "gaming=-f -W 1920 -H 1080\nexport VAR=value\n"
        config_path = temp_config_with_content(config_data)

        # Set up the application
        app = Application()

        # Mock required components
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file",
            return_value=config_path,
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # Run with a profile to test config result usage
        result = app.run(["-p", "gaming", "--", "test_app"])

        assert result == 0
        assert mock_run.called


class TestConfigResultEndToEnd:
    """End-to-end tests for ConfigResult functionality."""

    def test_config_result_full_lifecycle_e2e(self, temp_config_with_content):
        """Test full lifecycle of ConfigResult from file loading to usage."""
        config_data = """# Performance profile
performance="-f -W 2560 -H 1440"
# With exports
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-1
# Another profile
streaming=--borderless -W 1920 -H 1080 --framerate-limit=60
# More exports
export VAR1="value with spaces"
export VAR2='single quoted value'
"""
        config_path = temp_config_with_content(config_data)

        # Load config using ConfigManager (returns ConfigResult)
        config_result = ConfigManager.load_config(config_path)

        # Verify all profiles are loaded
        assert "performance" in config_result.profiles
        assert "streaming" in config_result.profiles

        # Verify profile content
        assert config_result.profiles["performance"].args == "-f -W 2560 -H 1440"
        assert (
            config_result.profiles["streaming"].args
            == "--borderless -W 1920 -H 1080 --framerate-limit=60"
        )

        # Verify all exports are loaded
        assert "DISPLAY" in config_result.exports
        assert "WAYLAND_DISPLAY" in config_result.exports
        assert "VAR1" in config_result.exports
        assert "VAR2" in config_result.exports

        # Verify export content
        assert config_result.exports["DISPLAY"] == ":0"
        assert config_result.exports["WAYLAND_DISPLAY"] == "wayland-1"
        assert config_result.exports["VAR1"] == "value with spaces"
        assert config_result.exports["VAR2"] == "single quoted value"

        # Test dictionary-like access on profiles
        assert config_result.profiles["performance"].args == "-f -W 2560 -H 1440"
        assert config_result.profiles.get("nonexistent", "default") == "default"

        # Test iteration capabilities
        profile_keys = set(config_result.profiles.keys())
        expected_keys = {"performance", "streaming"}
        assert profile_keys == expected_keys

    def test_config_result_with_complex_config_e2e(self, temp_config_with_content):
        """Test ConfigResult with complex configuration scenarios."""
        config_data = """
# Multiple profiles with various gamescope options
performance=-f -W 2560 -H 1440 --mangoapp --framerate-limit=120
quality=--borderless -W 1920 -H 1080 --framerate-limit=60
compatibility=-W 1280 -H 720 --fsr-sharpness 5 --backend sdl2
ultrawide=-f -W 3440 -H 1440

# Environment exports
export PROTON_ENABLE_FSR=1
export PROTON_HIDE_NVIDIA_GPU=1
export MANGOHUD=1
export DXVK_ASYNC=1

# More profiles
vr-gaming=-w 1200 -h 1080 --vr --mangoapp
streaming-low=-W 1280 -H 720 --framerate-limit=30 --backend sdl2
"""
        config_path = temp_config_with_content(config_data)

        # Load and verify complex config
        config_result = ConfigManager.load_config(config_path)

        # Verify all profiles exist
        expected_profiles = {
            "performance",
            "quality",
            "compatibility",
            "ultrawide",
            "vr-gaming",
            "streaming-low",
        }
        assert set(config_result.profiles.keys()) == expected_profiles

        # Verify all exports exist
        expected_exports = {
            "PROTON_ENABLE_FSR",
            "PROTON_HIDE_NVIDIA_GPU",
            "MANGOHUD",
            "DXVK_ASYNC",
        }
        assert set(config_result.exports.keys()) & expected_exports == expected_exports

        # Verify complex profile content
        perf_content = config_result.profiles["performance"].args
        assert "-f" in perf_content
        assert "2560" in perf_content
        assert "--mangoapp" in perf_content
        assert "120" in perf_content

        # Test that the result works in application context
        assert hasattr(config_result, "profiles")
        assert hasattr(config_result, "exports")
        assert isinstance(config_result.profiles, dict)
        assert isinstance(config_result.exports, dict)

    def test_config_result_application_integration_e2e(
        self, mocker, temp_config_with_content
    ):
        """Test ConfigResult as part of full application workflow."""
        config_data = """gaming=-f -W 1920 -H 1080 --mangoapp --fsr-sharpness 8
export PROTON_ENABLE_FSR=1
export MANGOHUD=1
"""
        config_path = temp_config_with_content(config_data)

        app = Application()

        # Mock components to focus on config result handling
        mocker.patch(
            "nscb.config_manager.ConfigManager.find_config_file",
            return_value=config_path,
        )
        mocker.patch("nscb.application.shutil.which", return_value=True)
        # Hermetic: assume no gamescope session so the launch path is exercised
        mocker.patch(
            "nscb.environment_helper.EnvironmentHelper.is_gamescope_active",
            return_value=False,
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        # Run with profile to test the config result flow
        result = app.run(["-p", "gaming", "-W", "2560", "--", "test_game"])

        assert result == 0

        # The config result should have been used to get the profile args
        # which were then merged with overrides
        call_args = mock_run.call_args[0][0]
        assert "gamescope" in call_args  # Command should include gamescope
        assert "test_game" in call_args  # App should be in command
        assert "2560" in call_args  # Override should be present
        assert "1920" not in call_args  # Original value should be overridden
