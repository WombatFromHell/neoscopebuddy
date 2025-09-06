#!/usr/bin/python3

import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from nscb import (
    find_executable,
    get_env_commands,
    is_gamescope_active,
    main,
    merge_arguments,
    merge_multiple_profiles,
    separate_flags_and_positionals,
    parse_profile_args,
)


class SystemExitCalled(Exception):
    """Custom exception to simulate sys.exit behavior in tests"""

    def __init__(self, code):
        self.code = code
        super().__init__(f"sys.exit({code}) called")


# Unit Tests for smaller functions
class TestNSCBUnitFunctions(unittest.TestCase):
    def test_parse_profile_args(self):
        """Test profile argument parsing variations"""
        self.assertEqual(parse_profile_args(["-p", "gaming"]), (["gaming"], []))
        self.assertEqual(
            parse_profile_args(["--profile=streaming"]), (["streaming"], [])
        )
        self.assertEqual(
            parse_profile_args(["-p", "a", "--profile=b", "cmd"]), (["a", "b"], ["cmd"])
        )
        self.assertEqual(
            parse_profile_args(["--profiles=gaming,streaming"]),
            (["gaming", "streaming"], []),
        )
        self.assertEqual(parse_profile_args(["--profiles="]), ([], []))

    def test_separate_flags_and_positionals_basic(self):
        """Basic flag and positional separation"""
        flags, positionals = separate_flags_and_positionals(["-W", "1920", "--nested"])
        self.assertEqual(flags, [("-W", "1920"), ("--nested", None)])
        self.assertEqual(positionals, [])

    def test_separate_flags_and_positionals_with_positionals(self):
        """Mix of flags and positionals"""
        flags, positionals = separate_flags_and_positionals(
            ["-f", "app.exe", "--borderless"]
        )
        self.assertEqual(flags, [("-f", "app.exe"), ("--borderless", None)])
        self.assertEqual(positionals, [])

    def test_separate_flags_and_positionals_only_flags(self):
        """Only flags, no positionals"""
        flags, positionals = separate_flags_and_positionals(
            ["-W", "1920", "-H", "1080"]
        )
        self.assertEqual(flags, [("-W", "1920"), ("-H", "1080")])
        self.assertEqual(positionals, [])

    def test_separate_flags_and_positionals_only_positionals(self):
        """Only positionals, no flags"""
        flags, positionals = separate_flags_and_positionals(["app.exe", "arg1"])
        self.assertEqual(flags, [])
        self.assertEqual(positionals, ["app.exe", "arg1"])

    def test_separate_flags_and_positionals_empty(self):
        """Empty input"""
        flags, positionals = separate_flags_and_positionals([])
        self.assertEqual(flags, [])
        self.assertEqual(positionals, [])

    def test_merge_arguments_basic(self):
        """Test basic argument merging"""
        result = merge_arguments(["-f"], ["--mangoapp"])
        self.assertIn("-f", result)
        self.assertIn("--mangoapp", result)

    def test_merge_arguments_conflict(self):
        """A different conflict flag in the override removes the profile’s conflict."""
        # Profile has -f (fullscreen), override has --borderless (should win)
        result = merge_arguments(["-f", "-W", "1920"], ["--borderless"])
        self.assertNotIn("-f", result)  # fullscreen removed
        self.assertIn("--borderless", result)  # borderless wins
        self.assertIn("-W", result)  # width preserved (not mutually exclusive)
        self.assertIn("1920", result)  # width value preserved

    def test_merge_arguments_width_override(self):
        """Test that width can be explicitly overridden"""
        # Profile has -W 1920, override explicitly sets different width
        result = merge_arguments(["-f", "-W", "1920"], ["--borderless", "-W", "2560"])
        self.assertNotIn("-f", result)  # fullscreen removed due to conflict
        self.assertIn("--borderless", result)  # borderless wins
        self.assertIn("-W", result)  # width flag preserved
        self.assertIn("2560", result)  # new width value (overridden)
        self.assertNotIn("1920", result)  # old width removed

    def test_merge_arguments_mutual_exclusivity(self):
        """Test that mutually exclusive flags are properly handled"""
        # Profile has -f (fullscreen), override has --borderless
        result = merge_arguments(["-f"], ["--borderless"])
        self.assertNotIn("-f", result)  # -f should be replaced by --borderless
        self.assertIn("--borderless", result)

        # Override has -f, profile has --borderless
        result = merge_arguments(["--borderless"], ["-f"])
        self.assertNotIn(
            "--borderless", result
        )  # --borderless should be replaced by -f
        self.assertIn("-f", result)

    def test_merge_arguments_conflict_with_values(self):
        """Test conflict handling when flags have values"""
        # Profile has -W 1920, override has --borderless (should preserve width setting)
        result = merge_arguments(["-W", "1920"], ["--borderless"])
        self.assertIn("-W", result)  # Width flag should be preserved
        self.assertIn("1920", result)  # Width value should be preserved
        self.assertIn("--borderless", result)

    def test_merge_arguments_non_conflict_preservation(self):
        """Test that non-conflict flags are preserved when not overridden"""
        # Profile has -W 1920, override doesn't touch width (should be preserved)
        result = merge_arguments(["-f", "-W", "1920"], ["--borderless"])
        self.assertNotIn("-f", result)  # fullscreen removed due to conflict
        self.assertIn("--borderless", result)  # borderless wins
        self.assertIn("-W", result)  # width preserved (not overridden)
        self.assertIn("1920", result)  # width value preserved

    def test_merge_multiple_profiles(self):
        """Test merging multiple profile argument lists"""
        # Test empty list
        self.assertEqual(merge_multiple_profiles([]), [])

        # Test single profile list (should return unchanged)
        self.assertEqual(
            merge_multiple_profiles([["-f", "-W", "1920"]]), ["-f", "-W", "1920"]
        )

        # Test multiple profiles with display mode conflicts
        profiles = [
            ["-f"],  # fullscreen
            ["--borderless"],  # should win over -f due to mutual exclusivity
            ["-W", "1920"],  # width setting that should be preserved
        ]
        result = merge_multiple_profiles(profiles)
        self.assertIn("--borderless", result)  # conflict winner
        self.assertNotIn("-f", result)  # conflict loser removed
        self.assertIn("-W", result)  # non-conflict flag preserved

        # Test profiles with explicit width overrides
        profiles = [
            ["-f", "-W", "1920"],
            ["--borderless", "-W", "2560"],  # should override previous width setting
        ]
        result = merge_multiple_profiles(profiles)
        self.assertIn("--borderless", result)  # conflict winner
        self.assertNotIn("-f", result)  # conflict loser removed
        self.assertIn("-W", result)  # width flag preserved
        self.assertIn("2560", result)  # latest value wins
        self.assertNotIn("1920", result)  # old value removed

    def test_find_executable_true(self):
        """Test executable discovery when found"""
        with (
            patch.dict("os.environ", {"PATH": "/usr/bin:/bin"}),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "is_dir", return_value=True),
            patch.object(Path, "is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            self.assertTrue(find_executable("gamescope"))

    def test_find_executable_false(self):
        """Test executable discovery when not found"""
        with patch.dict("os.environ", {"PATH": ""}, clear=True):
            self.assertFalse(find_executable("gamescope"))


# Integration Tests for larger workflows
class TestNSCBIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_run_nonblocking = patch(
            "nscb.run_nonblocking", return_value=0
        ).start()
        self.mock_build = patch(
            "nscb.build_command", side_effect=lambda x: "; ".join(x)
        ).start()
        self.mock_print = patch("builtins.print").start()
        # Make sys.exit actually stop execution by raising an exception
        self.mock_sys_exit = patch(
            "sys.exit",
            side_effect=lambda code: (_ for _ in ()).throw(SystemExitCalled(code)),
        ).start()

    def tearDown(self):
        patch.stopall()

    def test_main_complete_workflow_with_profiles(self):
        """Test complete main workflow with multiple profiles and argument merging"""
        config_data = """
# Config file with comments
gaming=-f -W 1920 -H 1080
streaming=--borderless -W 1280 -H 720
"""
        cmd = "nscb --profiles=gaming,streaming -W 1600 -- app".split(" ")
        with (
            patch("nscb.is_gamescope_active", return_value=False),
            patch("nscb.find_config_file", return_value=Path("/fake/config")),
            patch("builtins.open", new_callable=mock_open, read_data=config_data),
            patch("sys.argv", cmd),
            patch("nscb.find_executable", return_value=True),
        ):
            with self.assertRaises(SystemExitCalled) as cm:
                main()

            # Verify the exit code
            self.assertEqual(cm.exception.code, 0)

            # Verify the merged command includes profile args with overrides
            called_cmd = self.mock_run_nonblocking.call_args[0][0]
            self.assertIn("gamescope", called_cmd)
            self.assertIn("-W 1600", called_cmd)  # Override should win
            self.assertIn("app", called_cmd)

    def test_main_error_scenarios(self):
        """Test main function error handling scenarios"""
        # Test missing gamescope executable - this should exit before execute_gamescope_command
        with (
            patch("nscb.find_executable", return_value=False),
            patch("logging.error") as mock_log,
            patch("sys.argv", ["nscb"]),
        ):
            with self.assertRaises(SystemExitCalled) as cm:
                main()

            self.assertEqual(cm.exception.code, 1)
            mock_log.assert_called_with("'gamescope' not found in PATH")

    def test_gamescope_detection_and_execution_modes(self):
        """Test gamescope detection methods and execution modes"""
        # Test XDG desktop detection
        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True):
            self.assertTrue(is_gamescope_active())

    def test_environment_commands_integration(self):
        """Test pre/post command environment variable handling"""
        test_cases = [
            # Test new variable names
            ({"NSCB_PRE_CMD": "pre", "NSCB_POST_CMD": "post"}, ("pre", "post")),
            # Test legacy variable names
            (
                {"NSCB_PRECMD": "old_pre", "NSCB_POSTCMD": "old_post"},
                ("old_pre", "old_post"),
            ),
        ]

        for env_vars, expected in test_cases:
            with patch.dict("os.environ", env_vars, clear=True):
                result = get_env_commands()
                self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
