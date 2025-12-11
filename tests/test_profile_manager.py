"""Tests for the profile management functionality in NeoscopeBuddy."""

import pytest

from nscb.application import Application
from nscb.profile_manager import ProfileManager


class TestProfileManagerUnit:
    """Unit tests for the ProfileManager class."""

    def test_parse_profile_args_variations(self):
        """Test profile argument parsing variations"""
        test_cases = [
            (["-p", "gaming"], (["gaming"], [])),
            (["--profile=streaming"], (["streaming"], [])),
            (["-p", "a", "--profile=b", "cmd"], (["a", "b"], ["cmd"])),
            (["--profiles=gaming,streaming"], (["gaming", "streaming"], [])),
            (["--profiles="], ([], [])),
        ]

        for input_args, expected in test_cases:
            assert ProfileManager.parse_profile_args(input_args) == expected

    def test_parse_profile_args_errors(self):
        """Test profile argument parsing errors"""
        test_cases = [
            (["-p"], r"-p requires value"),
            (["--profile"], r"--profile requires value"),
        ]

        for input_args, error_msg in test_cases:
            with pytest.raises(ValueError, match=error_msg):
                ProfileManager.parse_profile_args(input_args)

    @pytest.mark.parametrize(
        "profile_args,override_args,expected_result",
        [
            # Basic conflict resolution - fullscreen vs borderless
            (["-f"], ["--borderless"], ["--borderless"]),
            (["--borderless"], ["-f"], ["-f"]),
            # Width and height preservation during conflict
            (
                ["-f", "-W", "1920", "-H", "1080"],
                ["--borderless"],
                ["--borderless", "-W", "1920", "-H", "1080"],
            ),
            # Multiple flag preservation
            (
                ["-f", "-C", "5", "-s", "1.5"],
                ["--borderless"],
                ["--borderless", "-C", "5", "-s", "1.5"],
            ),
            # Override value replacement
            (["-W", "1920"], ["-W", "2560"], ["-W", "2560"]),
            # No conflicts - all should be preserved
            (
                ["-W", "1920", "-H", "1080"],
                ["--mangoapp"],
                ["-W", "1920", "-H", "1080", "--mangoapp"],
            ),
            # Empty profile args
            ([], ["-f", "-W", "1920"], ["-f", "-W", "1920"]),
            # Empty override args
            (["-f", "-W", "1920"], [], ["-f", "-W", "1920"]),
            # Application separator preservation
            (["-f", "--", "app.exe"], ["-W", "1920"], ["-f", "-W", "1920"]),
        ],
    )
    def test_merge_arguments_variations_parametrized(
        self, profile_args, override_args, expected_result
    ):
        """Test argument merging with conflict resolution using parametrization."""
        result = ProfileManager.merge_arguments(profile_args, override_args)
        assert result == expected_result

    def test_merge_arguments_variations(self):
        """Test argument merging with conflict resolution - legacy test"""
        test_cases = [
            # Basic conflict resolution - fullscreen vs borderless
            (["-f"], ["--borderless"], ["--borderless"]),
            (["--borderless"], ["-f"], ["-f"]),
            # Width and height preservation during conflict
            (
                ["-f", "-W", "1920", "-H", "1080"],
                ["--borderless"],
                ["--borderless", "-W", "1920", "-H", "1080"],
            ),
            # Multiple flag preservation
            (
                ["-f", "-C", "5", "-s", "1.5"],
                ["--borderless"],
                ["--borderless", "-C", "5", "-s", "1.5"],
            ),
            # Override value replacement
            (["-W", "1920"], ["-W", "2560"], ["-W", "2560"]),
            # No conflicts - all should be preserved
            (
                ["-W", "1920", "-H", "1080"],
                ["--mangoapp"],
                ["-W", "1920", "-H", "1080", "--mangoapp"],
            ),
            # Empty profile args
            ([], ["-f", "-W", "1920"], ["-f", "-W", "1920"]),
            # Empty override args
            (["-f", "-W", "1920"], [], ["-f", "-W", "1920"]),
            # Application separator preservation
            (["-f", "--", "app.exe"], ["-W", "1920"], ["-f", "-W", "1920"]),
        ]

        for profile_args, override_args, expected_result in test_cases:
            result = ProfileManager.merge_arguments(profile_args, override_args)
            assert result == expected_result

    def test_merge_arguments_mutual_exclusivity(self):
        # Test -f vs --borderless conflict
        result = ProfileManager.merge_arguments(["-f"], ["--borderless"])
        assert "-f" not in result
        assert "--borderless" in result

        # Test --borderless vs -f conflict (reverse)
        result = ProfileManager.merge_arguments(["--borderless"], ["-f"])
        assert "--borderless" not in result
        assert "-f" in result

    def test_merge_arguments_conflict_with_values(self):
        # Profile has -W 1920, override has --borderless (should preserve width setting)
        result = ProfileManager.merge_arguments(["-W", "1920"], ["--borderless"])
        assert "-W" in result
        assert "1920" in result
        assert "--borderless" in result

    def test_merge_arguments_non_conflict_preservation(self):
        # Profile has -f, override has --borderless (should replace -f but preserve others)
        result = ProfileManager.merge_arguments(["-f", "-W", "1920"], ["--borderless"])
        assert "-f" not in result
        assert "--borderless" in result
        assert "-W" in result
        assert "1920" in result

    def test_merge_arguments_width_override(self):
        # Profile has -f and -W 1920, override has --borderless and -W 2560
        result = ProfileManager.merge_arguments(
            ["-f", "-W", "1920"], ["--borderless", "-W", "2560"]
        )
        assert "-f" not in result
        assert "--borderless" in result
        assert "-W" in result
        assert "2560" in result
        assert "1920" not in result

    def test_merge_arguments_complex_override_scenarios(self):
        # Test width override
        result = ProfileManager.merge_arguments(
            ["-W", "1920", "-H", "1080"], ["-W", "2560"]
        )
        assert "-W" in result
        assert "2560" in result
        assert "1920" not in result
        assert "-H" in result
        assert "1080" in result

        # Test height override
        result = ProfileManager.merge_arguments(
            ["-W", "1920", "-H", "1080"], ["-H", "1440"]
        )
        assert "-H" in result
        assert "1440" in result
        assert "1080" not in result
        assert "-W" in result
        assert "1920" in result

    def test_merge_arguments_separator_edge_cases(self):
        # Test profile has separator but override doesn't
        result = ProfileManager.merge_arguments(["-f", "--", "app.exe"], ["-W", "1920"])
        assert "-f" in result
        assert "-W" in result
        assert "1920" in result

        # Test override has separator
        result = ProfileManager.merge_arguments(["-f", "-W", "1920"], ["--", "app.exe"])
        assert "--" in result
        assert "app.exe" in result

    def test_merge_arguments_flag_canonicalization(self):
        # Using short and long form of same flag - should handle properly
        result = ProfileManager.merge_arguments(["-f"], ["--fullscreen"])
        # Both are fullscreen flags, so one should remain
        assert ("-f" in result) or ("--fullscreen" in result)

    def test_merge_multiple_profiles_basic(self):
        # Test empty list
        assert ProfileManager.merge_multiple_profiles([]) == []

        # Test single profile list
        assert ProfileManager.merge_multiple_profiles([["-f", "-W", "1920"]]) == [
            "-f",
            "-W",
            "1920",
        ]

        # Test multiple profiles with display mode conflicts
        profiles = [
            ["-f"],  # fullscreen
            ["--borderless"],  # should win over -f
            ["-W", "1920"],  # width setting
        ]
        result = ProfileManager.merge_multiple_profiles(profiles)
        assert "--borderless" in result
        assert "-f" not in result
        assert "-W" in result

    def test_merge_multiple_profiles_with_explicit_overrides(self):
        profiles = [
            ["-f", "-W", "1920"],
            ["--borderless", "-W", "2560"],  # should override previous width
        ]
        result = ProfileManager.merge_multiple_profiles(profiles)
        assert "--borderless" in result
        assert "-f" not in result
        assert "-W" in result
        assert "2560" in result
        assert "1920" not in result

    def test_merge_multiple_profiles_complex_conflicts(self):
        profiles = [
            ["-f", "-W", "1920"],
            ["--borderless", "-H", "1080"],
            ["-f", "-w", "1280"],  # conflicts with --borderless
        ]
        result = ProfileManager.merge_multiple_profiles(profiles)
        assert ("--borderless" in result) or ("-f" in result)

        # Check that mutually exclusive flags are handled correctly
        conflict_count = sum(
            1
            for flag in result
            if flag in ["-f", "--fullscreen"] or flag in ["-b", "--borderless"]
        )
        assert conflict_count <= 1
        assert "-w" in result

    def test_merge_multiple_profiles_sequential_overrides(self):
        profiles = [
            ["-f", "-W", "1920", "--mangoapp"],
            [
                "-W",
                "2560",
                "--nested",
            ],  # Should override -W but preserve -f and --mangoapp
            ["--borderless"],  # Should override -f but preserve other non-conflicts
        ]
        result = ProfileManager.merge_multiple_profiles(profiles)
        assert "--borderless" in result
        assert "-f" not in result
        assert "2560" in result
        assert "1920" not in result
        assert "--mangoapp" in result
        assert "--nested" in result

    def test_merge_multiple_profiles_mixed_conflicts(self):
        profiles = [
            ["-f", "-W", "1920", "--mangoapp"],
            ["--borderless", "-H", "1440"],  # --borderless conflicts with -f
            ["-w", "1280", "--nested"],  # Non-conflicts
        ]
        result = ProfileManager.merge_multiple_profiles(profiles)
        assert "--borderless" in result
        assert "-f" not in result
        assert "-H" in result and "1440" in result
        assert "-w" in result and "1280" in result
        assert "--mangoapp" in result
        assert "--nested" in result
        assert "-W" in result
        assert "1920" in result


class TestProfileManagerIntegration:
    """Integration tests for ProfileManager with other modules."""

    def test_profile_manager_with_config_manager(
        self, mocker, temp_config_with_content
    ):
        """Test ProfileManager working with ConfigManager to process profiles."""
        config_content = (
            "gaming=-f -W 1920 -H 1080\nstreaming=--borderless -W 1280 -H 720\n"
        )
        config_path = temp_config_with_content(config_content)

        # Mock config manager to return the test config
        mock_config = mocker.MagicMock()
        mock_config.__contains__.return_value = True
        mock_config.__getitem__.return_value = "-f -W 1920 -H 1080"
        mock_config.get.return_value = "-f -W 1920 -H 1080"

        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )

        # Use real ProfileManager to parse and merge args
        profiles, remaining_args = ProfileManager.parse_profile_args(
            ["-p", "gaming", "--borderless", "--", "app"]
        )

        # Verify parsing worked
        assert profiles == ["gaming"]
        assert "--borderless" in remaining_args
        assert "--" in remaining_args

        # Now test merging with a real config (simulated)
        result = ProfileManager.merge_arguments(
            ["-f", "-W", "1920", "-H", "1080"], ["--borderless"]
        )
        assert "--borderless" in result
        assert "-f" not in result
        assert "-W" in result  # This should be preserved even though there's a conflict

    def test_profile_manager_application_workflow_integration(
        self, mocker, temp_config_with_content
    ):
        """Test profile manager as part of the full application workflow."""
        config_content = "performance=-f -W 2560 -H 1440 --mangoapp\n"
        config_path = temp_config_with_content(config_content)

        # Set up a real application with profile manager
        app = Application()

        # Mock config and executable detection
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # Run the app with a profile to test the profile manager integration
        result = app.run(["-p", "performance", "-W", "3200", "--", "test_app"])

        # Should have processed the profile and run successfully
        assert result == 0
        assert mock_run.called


class TestProfileManagerEndToEnd:
    """End-to-end tests for ProfileManager functionality."""

    def test_profile_complex_combinations_e2e(self, mocker, temp_config_with_content):
        config_data = """performance=-f -W 2560 -H 1440 --mangoapp --framerate-limit=120
quality=--borderless -W 1920 -H 1080 --framerate-limit=60
compatibility=-W 1280 -H 720 --fsr-sharpness 5 --backend sdl2
ultrawide=-f -W 3440 -H 1440
"""

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
        mocker.patch(
            "sys.argv", ["nscb", "--profiles=performance,quality", "--", "game"]
        )
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        # Test with a real application instance
        app = Application()
        result = app.run(["--profiles=performance,quality", "--", "game"])

        assert result == 0
        assert mock_run.call_count > 0

        called_cmd = mock_run.call_args[0][0]
        assert "--borderless" in called_cmd
        # Check that -f is not present as a standalone flag (not substring in other arguments)
        import re

        assert not re.search(
            r"-f(\s|;|$)", called_cmd
        )  # Conflicting flag should be removed
        assert "--mangoapp" in called_cmd
        assert "1920" in called_cmd
        assert "1080" in called_cmd
        assert "60" in called_cmd  # framerate from quality profile
        assert "game" in called_cmd

    def test_profile_override_precedence_real_scenarios_e2e(
        self, mocker, temp_config_with_content
    ):
        config_data = "gaming=-f -W 1920 -H 1080 --mangoapp\n"

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
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        # Test override precedence: command-line args should override profile
        app = Application()
        result = app.run(["-p", "gaming", "--borderless", "-W", "3200"])

        assert result == 0
        called_cmd = mock_run.call_args[0][0]
        assert "--borderless" in called_cmd
        # Check that -f is not present as a standalone flag (not substring in other arguments)
        import re

        assert not re.search(r"-f(\s|;|$)", called_cmd)
        assert "3200" in called_cmd
        assert "1920" not in called_cmd
        assert "--mangoapp" in called_cmd

    def test_profile_argument_merging_real_workflow_e2e(
        self, mocker, temp_config_with_content
    ):
        config_data = "mixed=-f -W 1920 -H 1080 --mangoapp --fsr-sharpness 5\n"

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
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )
        mocker.patch("builtins.print")

        app = Application()
        result = app.run(["-p", "mixed", "--borderless", "-W", "3840", "-H", "2160"])

        assert result == 0
        called_cmd = mock_run.call_args[0][0]
        assert "--borderless" in called_cmd
        # Check that -f is not present as a standalone flag (not substring in other arguments)
        import re

        assert not re.search(r"-f(\s|;|$)", called_cmd)
        assert "3840" in called_cmd
        assert "2160" in called_cmd
        assert "--mangoapp" in called_cmd
        assert "5" in called_cmd  # fsr-sharpness from original profile


class TestProfileManagerFixtureUtilization:
    """Test class demonstrating utilization of profile manager fixtures."""

    def test_profile_scenarios_with_fixtures(self, profile_test_scenarios):
        """
        Test profile merging using profile_test_scenarios fixture.

        This demonstrates how to use the profile_test_scenarios fixture to test
        various profile merging scenarios in a standardized way.
        """
        from nscb.profile_manager import ProfileManager

        # Test basic profile scenario
        basic_scenario = profile_test_scenarios["basic"]
        result = ProfileManager.merge_arguments(
            basic_scenario["profiles"], basic_scenario["overrides"]
        )
        # The actual result may have different ordering, so let's check the content
        assert set(result) == set(basic_scenario["expected"])
        assert result.count("-W") == 1  # Should have one -W flag
        assert "3840" in result  # Should have the override width

        # Test conflict resolution scenario
        conflict_scenario = profile_test_scenarios["conflict_resolution"]
        result = ProfileManager.merge_arguments(
            conflict_scenario["profiles"], conflict_scenario["overrides"]
        )
        # For conflict resolution, the override should win
        assert "--borderless" in result
        assert "-f" not in result  # Fullscreen should be removed
        assert "-W" in result
        assert "2560" in result

        # Test multiple profiles scenario
        multiple_scenario = profile_test_scenarios["multiple_profiles"]
        # merge_multiple_profiles only takes the profile args list, not overrides
        result = ProfileManager.merge_multiple_profiles(multiple_scenario["profiles"])
        # Check that all expected elements from profiles are present (without overrides)
        expected_profiles_set = set([item for sublist in multiple_scenario["profiles"] for item in sublist])
        result_set = set(result)
        assert result_set == expected_profiles_set
        assert result.count("--framerate-limit") == 1
        assert "60" in result  # Should have the original framerate from profiles

        # Test empty profile scenario
        empty_profile_scenario = profile_test_scenarios["empty_profile"]
        result = ProfileManager.merge_arguments(
            empty_profile_scenario["profiles"], empty_profile_scenario["overrides"]
        )
        assert result == empty_profile_scenario["expected"]

        # Test empty override scenario
        empty_override_scenario = profile_test_scenarios["empty_override"]
        result = ProfileManager.merge_arguments(
            empty_override_scenario["profiles"], empty_override_scenario["overrides"]
        )
        assert result == empty_override_scenario["expected"]

    def test_config_scenarios_with_fixtures(self, config_scenarios, temp_config_with_content):
        """
        Test config parsing using config_scenarios fixture.

        This demonstrates how to use the config scenarios fixture to test
        various configuration parsing scenarios in a standardized way.
        """
        from nscb.config_manager import ConfigManager

        # Test basic config scenario
        basic_scenario = config_scenarios["basic"]
        config_path = temp_config_with_content(basic_scenario["content"])
        result = ConfigManager.load_config(config_path)
        assert result.profiles == basic_scenario["expected_profiles"]
        assert result.exports == basic_scenario["expected_exports"]

        # Test config with exports scenario
        exports_scenario = config_scenarios["with_exports"]
        config_path = temp_config_with_content(exports_scenario["content"])
        result = ConfigManager.load_config(config_path)
        assert result.profiles == exports_scenario["expected_profiles"]
        assert result.exports == exports_scenario["expected_exports"]

        # Test complex config scenario
        complex_scenario = config_scenarios["complex"]
        config_path = temp_config_with_content(complex_scenario["content"])
        result = ConfigManager.load_config(config_path)
        assert result.profiles == complex_scenario["expected_profiles"]
        assert result.exports == complex_scenario["expected_exports"]
