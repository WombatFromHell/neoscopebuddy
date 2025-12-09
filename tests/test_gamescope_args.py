"""Tests for the gamescope argument mappings in NeoscopeBuddy."""

import sys
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import nscb modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from nscb.application import Application
from nscb.argument_processor import ArgumentProcessor
from nscb.gamescope_args import GAMESCOPE_ARGS_MAP
from nscb.profile_manager import ProfileManager


class TestGamescopeArgsMapUnit:
    """Unit tests for the gamescope argument mappings."""

    def test_gamescope_args_map_exists(self):
        """Test that GAMESCOPE_ARGS_MAP is defined."""
        assert GAMESCOPE_ARGS_MAP is not None
        assert isinstance(GAMESCOPE_ARGS_MAP, dict)

    def test_gamescope_args_map_not_empty(self):
        """Test that GAMESCOPE_ARGS_MAP contains mappings."""
        assert len(GAMESCOPE_ARGS_MAP) > 0

    @pytest.mark.parametrize(
        "short_arg,expected_long_arg",
        [
            ("-W", "--output-width"),
            ("-H", "--output-height"),
            ("-w", "--nested-width"),
            ("-h", "--nested-height"),
            ("-b", "--borderless"),
            ("-C", "--hide-cursor-delay"),
            ("-e", "--steam"),
            ("-f", "--fullscreen"),
            ("-F", "--filter"),
            ("-g", "--grab"),
            ("-o", "--nested-unfocused-refresh"),
            ("-O", "--prefer-output"),
            ("-r", "--nested-refresh"),
            ("-R", "--ready-fd"),
            ("-s", "--mouse-sensitivity"),
            ("-T", "--stats-path"),
            ("--sharpness", "--fsr-sharpness"),
        ],
    )
    def test_gamescope_args_mapping(self, short_arg, expected_long_arg):
        """Test that specific short-to-long argument mappings exist."""
        assert short_arg in GAMESCOPE_ARGS_MAP
        assert GAMESCOPE_ARGS_MAP[short_arg] == expected_long_arg

    def test_all_mappings_are_strings(self):
        """Test that all keys and values in the mapping are strings."""
        for key, value in GAMESCOPE_ARGS_MAP.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_no_duplicate_values(self):
        """Test that no two keys map to the same value."""
        values = list(GAMESCOPE_ARGS_MAP.values())
        unique_values = set(values)
        assert len(values) == len(unique_values), "Duplicate values found in mapping"

    def test_argument_formatting(self):
        """Test that arguments follow expected formatting patterns."""
        for key, value in GAMESCOPE_ARGS_MAP.items():
            # Short arguments should start with one dash
            if len(key) == 2:  # Single character flag like -W
                assert key.startswith("-") and not key.startswith("--")
            # Long arguments should start with two dashes
            assert value.startswith("--")


class TestGamescopeArgsMapIntegration:
    """Integration tests for gamescope args with other modules."""

    def test_gamescope_args_profile_manager_integration(self):
        """Test that gamescope args work with ProfileManager for conflict detection."""
        # The profile manager should be able to work with the mappings for conflict resolution
        # Check that known conflicting args are in the mapping
        assert "-f" in GAMESCOPE_ARGS_MAP  # fullscreen short
        assert "-b" in GAMESCOPE_ARGS_MAP  # borderless short
        # Note: --borderless is not directly mapped as a key (it's a value), so we check that the reverse is handled
        # The mapping goes from short to long, not vice versa
        assert (
            "--borderless" in GAMESCOPE_ARGS_MAP.values()
        )  # borderless long exists as a value

        # Test basic argument merging with known mappings
        result = ProfileManager.merge_arguments(["-f", "-W", "1920"], ["--borderless"])
        # --borderless should override -f due to conflict
        assert "--borderless" in result
        assert "-f" not in result
        # Non-conflicting args should be preserved
        assert "-W" in result and "1920" in result

    def test_gamescope_args_argument_processor_integration(self):
        """Test gamescope args integration with argument processor."""
        # Test with a mix of mapped and unmapped args
        test_args = ["-f", "-W", "1920", "--mangoapp", "--unknown-flag"]
        flags, positionals = ArgumentProcessor.separate_flags_and_positionals(test_args)

        # All arguments should be processed correctly
        flag_dict = {flag: value for flag, value in flags}
        assert ("-f", None) in flags  # fullscreen flag
        assert ("-W", "1920") in flags  # width flag with value
        assert ("--mangoapp", None) in flags  # gamescope flag without mapping
        assert ("--unknown-flag", None) in flags  # unmapped flag

    def test_gamescope_args_full_workflow_integration(
        self, mocker, temp_config_with_content
    ):
        """Test gamescope args in full application workflow."""
        config_data = "gaming=-f -W 1920 -H 1080 --mangoapp\n"
        config_path = temp_config_with_content(config_data)

        app = Application()

        # Mock required components
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # Run with args that include mapped gamescope arguments
        result = app.run(["-p", "gaming", "--borderless", "--", "test_game"])

        assert result == 0

        # The gamescope args mapping should have been used implicitly in argument processing
        call_args = mock_run.call_args[0][0]
        assert "gamescope" in call_args
        assert "test_game" in call_args
        # The --borderless should have overridden -f from the profile due to conflict resolution
        assert "--borderless" in call_args


class TestGamescopeArgsMapEndToEnd:
    """End-to-end tests for gamescope args functionality."""

    def test_gamescope_args_complete_mapping_e2e(self):
        """Test that all expected gamescope arguments are properly mapped."""
        expected_mappings = {
            "-W": "--output-width",
            "-H": "--output-height",
            "-w": "--nested-width",
            "-h": "--nested-height",
            "-b": "--borderless",
            "-C": "--hide-cursor-delay",
            "-e": "--steam",
            "-f": "--fullscreen",
            "-F": "--filter",
            "-g": "--grab",
            "-o": "--nested-unfocused-refresh",
            "-O": "--prefer-output",
            "-r": "--nested-refresh",
            "-R": "--ready-fd",
            "-s": "--mouse-sensitivity",
            "-T": "--stats-path",
            "--sharpness": "--fsr-sharpness",
        }

        # Check that all expected mappings exist
        for short_arg, long_arg in expected_mappings.items():
            assert short_arg in GAMESCOPE_ARGS_MAP, f"Missing mapping for {short_arg}"
            assert GAMESCOPE_ARGS_MAP[short_arg] == long_arg, (
                f"Incorrect mapping for {short_arg}"
            )

    def test_gamescope_args_conflict_resolution_e2e(self):
        """Test gamescope argument conflict resolution end-to-end."""
        # Test direct conflict resolution in ProfileManager
        result = ProfileManager.merge_arguments(
            ["-f", "-W", "1920", "-H", "1080"],  # Fullscreen profile
            ["--borderless", "-W", "2560"],  # Borderless override
        )

        # Should have non-conflicting args from profile preserved
        # Should have conflicting args properly resolved
        assert "--borderless" in result  # Override wins
        assert "-f" not in result  # Conflicting flag removed
        assert "-W" in result and "2560" in result  # Override value wins
        assert "-H" in result and "1080" in result  # Non-conflicting preserved

    def test_gamescope_args_complex_profile_scenario_e2e(
        self, mocker, temp_config_with_content
    ):
        """Test gamescope args in complex profile scenarios."""
        config_data = """performance=-f -W 2560 -H 1440 --mangoapp --framerate-limit=120
quality=--borderless -W 1920 -H 1080 --framerate-limit=60
compatibility=-W 1280 -H 720 --fsr-sharpness 5
ultrawide=-f -W 3440 -H 1440
"""
        config_path = temp_config_with_content(config_data)

        app = Application()

        # Mock components
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.system_detector.SystemDetector.is_gamescope_active",
            return_value=False,
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # Test merging multiple profiles with gamescope args
        result = app.run(
            ["--profiles=performance,quality", "-W", "3200", "--", "complex_game"]
        )

        assert result == 0
        call_args = mock_run.call_args[0][0]

        # The quality profile has --borderless which should override -f from performance
        # The -W should be overridden by command line value
        assert "--borderless" in call_args  # From quality profile
        # Check that -f is not present as a standalone flag (not substring in --framerate-limit)
        # Look for "-f " or "-f;" or similar patterns that would indicate a separate flag
        import re

        assert not re.search(
            r"-f(\s|;|$)", call_args
        )  # Conflicting flag from performance removed
        assert "3200" in call_args  # Command line override
        assert "60" in call_args  # Framerate from quality profile

    def test_gamescope_args_mapping_usage_in_real_scenarios(self):
        """Test that gamescope args mapping is used correctly in realistic scenarios."""
        # Verify that all mappings follow the expected format
        for short_arg, long_arg in GAMESCOPE_ARGS_MAP.items():
            assert isinstance(short_arg, str), f"Key {short_arg} is not a string"
            assert isinstance(long_arg, str), f"Value {long_arg} is not a string"

            # Short args should be single dash (or double for special cases like --sharpness)
            if short_arg.startswith("--"):
                # Long arg format
                assert short_arg.startswith("--"), (
                    f"Long arg {short_arg} doesn't start with --"
                )
            else:
                # Short arg format
                assert short_arg.startswith("-") and not short_arg.startswith("--"), (
                    f"Short arg {short_arg} doesn't follow format"
                )

            # Long args should always be double dash
            assert long_arg.startswith("--"), (
                f"Long arg {long_arg} doesn't start with --"
            )

    def test_gamescope_args_in_argument_processing_e2e(self):
        """Test gamescope args throughout the argument processing pipeline."""
        # Start with args containing gamescope mappings
        profile_args = ["-f", "-W", "1920", "-H", "1080", "--mangoapp"]
        override_args = ["--borderless", "-W", "2560"]

        # Process through the full pipeline
        result = ProfileManager.merge_arguments(profile_args, override_args)

        # Verify correct handling of gamescope-specific conflicts
        assert "--borderless" in result  # Override wins
        assert "-f" not in result  # Conflicting flag removed
        assert "2560" in result  # Override value wins
        assert "-H" in result and "1080" in result  # Non-conflicting preserved
        assert "--mangoapp" in result  # Non-conflicting preserved

        # Test with multiple profiles
        profiles = [
            ["-f", "--mangoapp"],  # Would normally conflict with next
            ["--borderless", "-W", "1920"],  # Would override conflicting flag
            ["--framerate-limit=120"],  # Additional flag
        ]

        merged = ProfileManager.merge_multiple_profiles(profiles)
        assert "--borderless" in merged  # Wins over -f
        assert "-f" not in merged  # Removed due to conflict
        assert "--mangoapp" in merged  # Non-conflicting preserved
        assert "--framerate-limit=120" in merged  # Non-conflicting preserved
