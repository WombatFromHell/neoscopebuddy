#!/usr/bin/python3

import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from nscb import (
    execute_gamescope_command,
    find_config_file,
    find_executable,
    get_env_commands,
    is_gamescope_active,
    load_config,
    main,
    merge_arguments,
    merge_multiple_profiles,
    parse_profile_args,
)


class SystemExitCalled(Exception):
    """Custom exception to simulate sys.exit behavior in tests"""

    def __init__(self, code):
        self.code = code
        super().__init__(f"sys.exit({code}) called")


class TestNSCBIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_run_nonblocking = patch(
            "nscb.run_nonblocking", return_value=0
        ).start()
        self.mock_build = patch(
            "nscb.build_command_string", side_effect=lambda x: "; ".join(x)
        ).start()
        self.mock_print = patch("builtins.print").start()
        # Make sys.exit actually stop execution by raising an exception
        self.mock_sys_exit = patch(
            "sys.exit",
            side_effect=lambda code: (_ for _ in ()).throw(SystemExitCalled(code)),
        ).start()

    def tearDown(self):
        patch.stopall()

    def test_argument_parsing_and_merging_edge_cases(self):
        """Test argument parsing edge cases and complex merging scenarios"""
        # Test profile argument parsing variations
        self.assertEqual(parse_profile_args(["-p", "gaming"]), (["gaming"], []))
        self.assertEqual(
            parse_profile_args(["--profile=streaming"]), (["streaming"], [])
        )
        self.assertEqual(
            parse_profile_args(["-p", "a", "--profile=b", "cmd"]), (["a", "b"], ["cmd"])
        )

        # Test new --profiles= syntax
        self.assertEqual(
            parse_profile_args(["--profiles=gaming,streaming"]),
            (["gaming", "streaming"], []),
        )
        self.assertEqual(
            parse_profile_args(["--profiles=a,b,c", "--profile=d"]),
            (["a", "b", "c", "d"], []),
        )
        self.assertEqual(
            parse_profile_args(["-p", "gaming", "--profiles=streaming,fullscreen"]),
            (["gaming", "streaming", "fullscreen"], []),
        )

        # Test edge cases for --profiles=
        self.assertEqual(parse_profile_args(["--profiles="]), ([], []))
        self.assertEqual(parse_profile_args(["--profiles=a,b,"]), (["a", "b"], []))
        self.assertEqual(parse_profile_args(["--profiles=,a,b"]), (["a", "b"], []))
        self.assertEqual(
            parse_profile_args(["-p", "gaming", "--profiles="]), (["gaming"], [])
        )

        # Test argument merging with conflicts
        result = merge_arguments(["-f", "-W", "1920"], ["--borderless", "-W", "1600"])
        self.assertIn("--borderless", result)  # newest conflict should win
        self.assertNotIn("-f", result)  # old conflict should get dumped
        self.assertIn("1600", result)  # override should take priority

        # Test multiple profile merging
        profiles = [["-f"], ["-W", "1920"], ["--borderless"]]
        result = merge_multiple_profiles(profiles)
        self.assertIn("--borderless", result)  # Last conflict wins
        self.assertIn("-W", result)

        # Test multiple profile single arg list merging
        result = merge_multiple_profiles([["-f", "-W", "1920"]])
        self.assertEqual(result, ["-f", "-W", "1920"])

        # Test empty profile merging
        result = merge_multiple_profiles([])
        self.assertEqual(result, [])

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

    def test_main_complete_workflow_with_dimension_override(self):
        """Test main workflow where dimension overrides are applied to a profile"""
        config_data = """
# Config file with profiles
gamingold=-f -w 1920 -h 1080 -W 1920 -H 1080
"""
        cmd = "nscb --profiles=gamingold -w 1600 -h 900 app".split(" ")
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
            self.assertIn("-w 1600", called_cmd)  # Override for width wins
            self.assertIn("-h 900", called_cmd)  # Override for height wins
            self.assertNotIn("-w 1920", called_cmd)  # Old width should be replaced
            self.assertNotIn("-h 1080", called_cmd)  # Old height should be replaced
            self.assertIn(
                "-W 1920", called_cmd
            )  # Profile value remains (not overridden)
            self.assertIn(
                "-H 1080", called_cmd
            )  # Profile value remains (not overridden)
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

        # Test missing config file when profile specified
        with (
            patch("nscb.find_executable", return_value=True),
            patch("nscb.find_config_file", return_value=None),
            patch("sys.argv", ["nscb", "--profiles=gaming"]),
            patch("logging.error") as mock_log,
        ):
            with self.assertRaises(SystemExitCalled) as cm:
                main()

            self.assertEqual(cm.exception.code, 1)
            mock_log.assert_called_with("could not find nscb.conf")

        # Test invalid profile in config
        with (
            patch("nscb.find_executable", return_value=True),
            patch("nscb.find_config_file", return_value=Path("/fake/config")),
            patch("builtins.open", new_callable=mock_open, read_data="gaming=-f"),
            patch("sys.argv", ["nscb", "--profiles=invalid"]),
            patch("logging.error") as mock_log,
        ):
            with self.assertRaises(SystemExitCalled) as cm:
                main()

            self.assertEqual(cm.exception.code, 1)
            mock_log.assert_called_with("profile 'invalid' not found")

    def test_gamescope_detection_and_execution_modes(self):
        """Test gamescope detection methods and execution modes"""
        # Test XDG desktop detection
        with patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True):
            self.assertTrue(is_gamescope_active())

        # Test ps command detection
        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "subprocess.check_output",
                return_value="1234 gamescope --nested\n5678 grep gamescope",
            ),
        ):
            self.assertTrue(is_gamescope_active())

        # Test negative detection - must clear environment and mock subprocess
        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "subprocess.check_output",
                return_value="no match here\nother processes",
            ),
        ):
            self.assertFalse(is_gamescope_active())

        # Test subprocess exception handling
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("subprocess.check_output", side_effect=Exception()),
        ):
            self.assertFalse(is_gamescope_active())

    def test_gamescope_active_execution_workflow(self):
        """Test execution when gamescope is already active"""
        cmd = "nscb --profiles=profile1,profile2 -- app arg1".split(" ")
        with (
            patch("nscb.is_gamescope_active", return_value=True),
            patch("nscb.find_config_file", return_value=Path("/config")),
            patch(
                "builtins.open",
                new_callable=mock_open,
                read_data="profile1=-f -W 1920\nprofile2=--borderless -H 720",
            ),
            patch("sys.argv", cmd),
            patch("nscb.find_executable", return_value=True),
            patch("nscb.get_env_commands", return_value=("", "")),
        ):
            with self.assertRaises(SystemExitCalled):
                main()

            # Should execute just the app portion
            self.mock_run_nonblocking.assert_called_once_with("app arg1")

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
            # Test new overrides legacy
            ({"NSCB_PRE_CMD": "new", "NSCB_PRECMD": "old"}, ("new", "")),
            # Test whitespace handling
            ({"NSCB_PRE_CMD": "  spaced  "}, ("spaced", "")),
        ]

        for env_vars, expected in test_cases:
            with patch.dict("os.environ", env_vars, clear=True):
                result = get_env_commands()
                self.assertEqual(result, expected)

    def test_config_file_discovery_paths(self):
        """Test config file discovery in different locations"""
        # Test XDG_CONFIG_HOME path
        with (
            patch.dict("os.environ", {"XDG_CONFIG_HOME": "/custom"}, clear=True),
            patch.object(Path, "exists") as mock_exists,
        ):
            mock_exists.return_value = True
            result = find_config_file()
            self.assertEqual(result, Path("/custom/nscb.conf"))

        # Test HOME/.config fallback - need to use a lambda that captures the Path instance
        with (
            patch.dict("os.environ", {"HOME": "/home/user"}, clear=True),
            patch.object(
                Path,
                "exists",
                lambda self: str(self).endswith("/home/user/.config/nscb.conf"),
            ),
        ):
            result = find_config_file()
            self.assertEqual(result, Path("/home/user/.config/nscb.conf"))

        # Test no config found
        with (
            patch.dict("os.environ", {"HOME": "/home/user"}, clear=True),
            patch.object(Path, "exists", return_value=False),
        ):
            result = find_config_file()
            self.assertIsNone(result)

    def test_executable_discovery_and_path_handling(self):
        """Test executable discovery in PATH"""
        # Test executable found
        with (
            patch.dict("os.environ", {"PATH": "/usr/bin:/bin"}),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "is_dir", return_value=True),
            patch.object(Path, "is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            self.assertTrue(find_executable("gamescope"))

        # Test executable not found
        with patch.dict("os.environ", {"PATH": ""}, clear=True):
            self.assertFalse(find_executable("gamescope"))

    def test_config_loading_with_comments_and_quotes(self):
        """Test config file loading with various formats"""
        config_content = """
# This is a comment
gaming = -f -W 1920
# Another comment
streaming="--borderless -W 1280"
"""
        with patch("builtins.open", new_callable=mock_open, read_data=config_content):
            config = load_config(Path("/fake"))
            expected = {
                "gaming": "-f -W 1920",
                "streaming": "--borderless -W 1280",
            }
            self.assertEqual(config, expected)

    def test_command_execution_with_no_args(self):
        """Test edge case where no final command is built"""
        pre_cmd = "echo 'first'"
        post_cmd = "echo 'finally'"

        with (
            patch.dict(
                "os.environ", {"NSCB_PRE_CMD": pre_cmd, "NSCB_POST_CMD": post_cmd}
            ),
            patch("nscb.is_gamescope_active", return_value=True),
            patch("nscb.build_command") as mock_build,
        ):
            with self.assertRaises(SystemExitCalled) as cm:
                execute_gamescope_command([])

            mock_build.assert_called_once_with([pre_cmd, post_cmd])

            self.assertEqual(cm.exception.code, 0)

    def test_profile_argument_parsing_errors(self):
        """Test profile argument parsing error handling"""
        with self.assertRaises(ValueError):
            parse_profile_args(["-p"])  # Missing value

        with self.assertRaises(ValueError):
            parse_profile_args(["--profile"])  # Missing value


if __name__ == "__main__":
    unittest.main()
