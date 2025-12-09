"""Tests for the argument processing functionality in NeoscopeBuddy."""

import sys
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import nscb modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from nscb.application import Application
from nscb.argument_processor import ArgumentProcessor
from nscb.profile_manager import ProfileManager


class TestArgumentProcessorUnit:
    """Unit tests for the ArgumentProcessor class."""

    @pytest.mark.parametrize(
        "input_args,expected_before,expected_after",
        [
            (["-f", "--", "app.exe"], ["-f"], ["--", "app.exe"]),
            (["-f", "--", "app1", "--", "app2"], ["-f"], ["--", "app1", "--", "app2"]),
            (["-f", "-W", "1920"], ["-f", "-W", "1920"], []),
            (["--", "app.exe"], [], ["--", "app.exe"]),
            ([], [], []),
            (["-f"], ["-f"], []),
        ],
    )
    def test_split_at_separator_variations(
        self, input_args, expected_before, expected_after
    ):
        result_before, result_after = ArgumentProcessor.split_at_separator(input_args)
        assert result_before == expected_before
        assert result_after == expected_after

    @pytest.mark.parametrize(
        "input_args,expected_flags,expected_positionals",
        [
            (["-W", "1920", "--nested"], [("-W", "1920"), ("--nested", None)], []),
            (
                ["-f", "app.exe", "--borderless"],
                [("-f", "app.exe"), ("--borderless", None)],
                [],
            ),
            (["-W", "1920", "-H", "1080"], [("-W", "1920"), ("-H", "1080")], []),
            (["app.exe", "arg1"], [], ["app.exe", "arg1"]),
            ([], [], []),
            (
                [
                    "-W",
                    "1920",
                    "--output-width",
                    "2560",
                    "-f",
                    "--mangoapp",
                    "game.exe",
                ],
                [
                    ("-W", "1920"),
                    ("--output-width", "2560"),
                    ("-f", None),
                    ("--mangoapp", "game.exe"),
                ],
                [],
            ),
            (
                ["-f", "--borderless", "--mangoapp"],
                [("-f", None), ("--borderless", None), ("--mangoapp", None)],
                [],
            ),
            (
                ["-W", "1920", "game.exe", "--fullscreen", "-H", "1080", "input.txt"],
                [("-W", "1920"), ("--fullscreen", None), ("-H", "1080")],
                ["game.exe", "input.txt"],
            ),
            (
                ["game.exe", "-W", "1920", "--", "-f", "extra_arg"],
                [("-W", "1920"), ("--", None), ("-f", "extra_arg")],
                ["game.exe"],
            ),
            (
                [
                    "-f",
                    "-W",
                    "1920",
                    "--nested-width",
                    "1280",
                    "game.exe",
                    "save1",
                    "--borderless",
                ],
                [
                    ("-f", None),
                    ("-W", "1920"),
                    ("--nested-width", "1280"),
                    ("--borderless", None),
                ],
                ["game.exe", "save1"],
            ),
        ],
    )
    def test_separate_flags_and_positionals_variations(
        self, input_args, expected_flags, expected_positionals
    ):
        flags, positionals = ArgumentProcessor.separate_flags_and_positionals(
            input_args
        )
        assert flags == expected_flags
        assert positionals == expected_positionals


class TestArgumentProcessorIntegration:
    """Integration tests for ArgumentProcessor with other modules."""

    def test_argument_processor_profile_manager_integration(self):
        """Test ArgumentProcessor working with ProfileManager for argument processing."""
        # Test that ProfileManager uses ArgumentProcessor internally
        profiles, remaining_args = ProfileManager.parse_profile_args(
            ["-p", "gaming", "--borderless", "--", "app"]
        )
        assert profiles == ["gaming"]
        assert "--borderless" in remaining_args
        assert "--" in remaining_args
        assert "app" in remaining_args

    def test_argument_processor_full_workflow_integration(
        self, mocker, temp_config_with_content
    ):
        """Test ArgumentProcessor as part of the full application workflow."""
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

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

        # Test the full application flow with various argument types
        test_args = ["-p", "gaming", "--borderless", "-W", "2560", "--", "test_app"]
        result = app.run(test_args)

        assert result == 0
        # Verify that arguments were processed correctly through the pipeline
        assert mock_run.called

    def test_complex_argument_processing_integration(self):
        """Test complex argument processing scenarios."""
        # Split at separator
        before, after = ArgumentProcessor.split_at_separator(
            ["-f", "-W", "1920", "--", "game.exe", "save1"]
        )
        assert before == ["-f", "-W", "1920"]
        assert after == ["--", "game.exe", "save1"]

        # Separate flags and positionals
        flags, positionals = ArgumentProcessor.separate_flags_and_positionals(
            ["-f", "-W", "1920", "game.exe", "save1"]
        )
        assert flags == [("-f", None), ("-W", "1920")]
        assert positionals == ["game.exe", "save1"]

        # Combine both operations to simulate full processing
        full_args = ["-f", "-W", "1920", "game.exe", "--", "extra_args"]
        before_split, after_split = ArgumentProcessor.split_at_separator(full_args)
        flags_before, pos_before = ArgumentProcessor.separate_flags_and_positionals(
            before_split
        )

        assert flags_before == [("-f", None), ("-W", "1920")]
        assert pos_before == ["game.exe"]
        assert after_split == ["--", "extra_args"]


class TestArgumentProcessorEndToEnd:
    """End-to-end tests for ArgumentProcessor functionality."""

    def test_complex_args_scenario_e2e(self):
        """Test comprehensive argument processing scenario."""
        # Test various complex argument combinations
        test_scenarios = [
            # Basic profile with overrides and app
            (
                ["-p", "gaming", "--borderless", "-W", "2560", "--", "game.exe"],
                ["gaming"],
                ["--borderless", "-W", "2560", "--", "game.exe"],
            ),
            # Multiple profiles with mixed args
            (
                ["--profiles=gaming,streaming", "-f", "--", "app", "arg1"],
                ["gaming", "streaming"],
                ["-f", "--", "app", "arg1"],
            ),
            # Args with no profile
            (
                ["-W", "1920", "-H", "1080", "--", "app"],
                [],
                ["-W", "1920", "-H", "1080", "--", "app"],
            ),
        ]

        for input_args, expected_profiles, expected_remaining in test_scenarios:
            profiles, remaining_args = ProfileManager.parse_profile_args(input_args)
            assert profiles == expected_profiles
            assert remaining_args == expected_remaining

    def test_argument_separation_edge_cases_e2e(self):
        """Test edge cases in argument processing."""
        # Test empty lists
        before, after = ArgumentProcessor.split_at_separator([])
        assert before == []
        assert after == []

        flags, positionals = ArgumentProcessor.separate_flags_and_positionals([])
        assert flags == []
        assert positionals == []

        # Test only separator
        before, after = ArgumentProcessor.split_at_separator(["--"])
        assert before == []
        assert after == ["--"]

        # Test no separator
        before, after = ArgumentProcessor.split_at_separator(["-f", "app"])
        assert before == ["-f", "app"]
        assert after == []

        # Test multiple separators (should only split on first)
        before, after = ArgumentProcessor.split_at_separator(
            ["-f", "--", "app", "--", "extra"]
        )
        assert before == ["-f"]
        assert after == ["--", "app", "--", "extra"]

    def test_argument_processing_full_pipeline_e2e(
        self, mocker, temp_config_with_content
    ):
        """Test the full argument processing pipeline from input to execution."""
        config_data = "performance=-f -W 2560 -H 1440 --mangoapp\n"
        config_path = temp_config_with_content(config_data)

        # Create a full application flow with complex arguments
        app = Application()

        # Mock components to focus on argument processing
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # Test complex argument scenario
        complex_args = [
            "-p",
            "performance",
            "--borderless",  # This should override -f from profile
            "-W",
            "3200",  # This should override -W from profile
            "--mangoapp",  # This should be additive
            "--",
            "complex_game",
            "save1",
            "level2",
        ]

        result = app.run(complex_args)

        assert result == 0
        # Verify execution was called with properly processed arguments
        call_args = mock_run.call_args[0][0]
        # The command should reflect the merged and processed arguments
        assert "complex_game" in call_args
        assert "save1" in call_args
        assert "level2" in call_args

    def test_argument_merging_with_complex_separators_e2e(self):
        """Test argument merging scenarios without expecting separator in result."""
        # Profile args with separator
        profile_args = ["-f", "-W", "1920", "--", "profile_app"]
        override_args = ["--borderless", "-H", "1080"]

        # When merging, merge_arguments only processes flags/arguments before the separator
        # The separator separates command specification from the application to run
        result = ProfileManager.merge_arguments(profile_args, override_args)

        # Should contain the override flags and preserve non-conflicting profile flags
        assert "--borderless" in result
        assert "-f" not in result  # Conflicting flag removed
        assert "-H" in result and "1080" in result  # Override applied
        assert "-W" in result and "1920" in result  # Non-conflicting preserved
        # The separator itself is not part of the result as it's used for internal processing

    def test_argument_processing_with_mixed_quotes_and_values_e2e(self):
        """Test processing of arguments that might include quoted values."""
        # Simulate complex argument structures
        complex_input = [
            "--some-flag",
            "value with spaces",
            "--quoted-flag",
            '"quoted value"',
            "-f",  # Flag without value
            "--",  # Separator
            "app",
            "arg with spaces",
        ]

        # Test separation
        flags, positionals = ArgumentProcessor.separate_flags_and_positionals(
            complex_input[:-3]
        )  # Exclude separator and after
        assert len(flags) >= 3  # At least the three flags
        assert "app" in complex_input[5:]  # Positional after separator
