#!/usr/bin/python3

import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from nscb import (
    main,
    find_config_file,
    find_executable,
    parse_arguments,
    merge_arguments,
    is_gamescope_active,
    parse_env_and_command,
    extract_nscb_args,
    build_interpolated_string,
)


class TestNSCB(unittest.TestCase):

    def test_find_config_file(self):
        # Case 1: XDG_CONFIG_HOME set and config exists
        with patch("os.getenv") as mock_getenv, patch.object(
            Path, "exists", return_value=True
        ):
            mock_getenv.side_effect = lambda key: (
                "custom_path" if key == "XDG_CONFIG_HOME" else None
            )
            result = find_config_file()
            self.assertEqual(result, Path("custom_path/nscb.conf"))

        # Case 2: HOME set and config exists in ~/.config/
        with patch("os.getenv") as mock_getenv, patch.object(
            Path, "exists", return_value=True
        ):
            mock_getenv.side_effect = lambda key: "home_path" if key == "HOME" else None
            result = find_config_file()
            self.assertEqual(result, Path("home_path/.config/nscb.conf"))

        # Case 3: Neither XDG_CONFIG_HOME nor HOME set, config does not exist
        with patch("os.getenv") as mock_getenv, patch.object(
            Path, "exists", return_value=False
        ):
            mock_getenv.return_value = None
            result = find_config_file()
            self.assertIsNone(result)

    def test_find_executable(self):
        with patch("os.environ", {"PATH": "/usr/bin:/bin"}), patch(
            "os.path.exists", return_value=True
        ), patch("os.access", return_value=True):

            self.assertTrue(find_executable("gamescope"))

        # Case where executable not found
        with patch("os.environ", {"PATH": ""}):
            self.assertFalse(find_executable("nonexistent"))

    def test_parse_arguments(self):
        # Case 1: -p flag with value
        args = ["-p", "myprofile", "--otherarg"]
        profile, remaining_args = parse_arguments(args)
        self.assertEqual(profile, "myprofile")
        self.assertEqual(remaining_args, ["--otherarg"])

        # Case 2: --profile=value format
        args = ["--profile=dev", "-f"]
        profile, remaining_args = parse_arguments(args)
        self.assertEqual(profile, "dev")
        self.assertEqual(remaining_args, ["-f"])

        # Case 3: Missing value for -p flag - capture stderr to suppress output
        with patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                parse_arguments(["-p"])

    def test_merge_arguments_gamescope_args(self):
        profile_args = ["--windowed", "-f", "-W 1280", "-H 720"]
        override_args = [
            "--force-grab-cursor",
            "-W",
            "2560",
            "-H",
            "1440",
            "--",
            "/usr/bin/someapp",
        ]

        merged = merge_arguments(profile_args, override_args)

        # Check that all flags and args are present
        self.assertIn("-f", merged)
        self.assertIn("--windowed", merged)
        self.assertIn("--force-grab-cursor", merged)
        self.assertIn("-W", merged)
        self.assertIn("2560", merged)
        self.assertIn("-H", merged)
        self.assertIn("1440", merged)
        self.assertIn("--", merged)
        self.assertIn("/usr/bin/someapp", merged)

    def test_parse_env_and_command(self):
        cmd_line = 'LD_PRELOAD="/lib/libtest.so" NSCB_PRECMD="echo pre" gamescope -f'

        env_vars, command_parts = parse_env_and_command(cmd_line)

        self.assertEqual(
            env_vars, {"LD_PRELOAD": "/lib/libtest.so", "NSCB_PRECMD": "echo pre"}
        )

        self.assertEqual(command_parts, ["gamescope", "-f"])

    def test_extract_nscb_args_gamescope_style(self):
        # Case 1: nscb.py found in args with gamescope-like arguments
        args = [
            "nscb.py",
            "-p",
            "dev",
            "-f",
            "-W",
            "2560",
            "-H",
            "1440",
            "--force-grab-cursor",
            "--",
            "/usr/bin/someapp",
        ]

        profile, nscb_args, gamescope_app_args = extract_nscb_args(args)

        self.assertEqual(profile, "dev")
        self.assertEqual(
            nscb_args, ["-f", "-W", "2560", "-H", "1440", "--force-grab-cursor"]
        )
        self.assertEqual(gamescope_app_args, ["--", "/usr/bin/someapp"])

        # Case 2: nscb.py not found
        args = ["gamescope", "-f"]
        profile, nscb_args, gamescope_app_args = extract_nscb_args(args)
        self.assertIsNone(profile)
        self.assertEqual(nscb_args, [])
        self.assertEqual(gamescope_app_args, ["gamescope", "-f"])

    def test_build_interpolated_string_gamescope_style(self):
        cmd_line = (
            "nscb.py -p dev -f -W 2560 -H 1440 --force-grab-cursor -- /usr/bin/someapp"
        )

        result = build_interpolated_string(cmd_line)

        self.assertIn("gamescope -f", result)
        self.assertIn("-W 2560", result)
        self.assertIn("-H 1440", result)
        self.assertIn("--force-grab-cursor", result)
        self.assertIn("-- /usr/bin/someapp", result)

    def test_main_gamescope_style(self):
        # Mock sys.argv to simulate command-line arguments
        original_sys_argv = sys.argv
        sys.argv = [
            "nscb.py",
            "-p",
            "dev",
            "-f",
            "-W",
            "2560",
            "-H",
            "1440",
            "--force-grab-cursor",
            "--",
            "/usr/bin/someapp",
        ]

        # Mock find_executable to return True
        with patch("nscb.find_executable", return_value=True), patch(
            "nscb.find_config_file", return_value=Path("/fake/config")
        ), patch("nscb.load_config", return_value={"dev": "-f --windowed"}), patch(
            "nscb.is_gamescope_active", return_value=False
        ), patch(
            "os.system"
        ) as mock_system, patch(
            "builtins.print"
        ):  # Suppress print statements

            main()

            # Check that os.system was called with a command containing expected elements
            mock_system.assert_called_once()
            called_command = mock_system.call_args[0][0]
            self.assertIn("gamescope", called_command)
            self.assertIn("-f", called_command)
            self.assertIn("-W 2560", called_command)
            self.assertIn("-H 1440", called_command)
            self.assertIn("--force-grab-cursor", called_command)
            self.assertIn("/usr/bin/someapp", called_command)

        # Restore original sys.argv
        sys.argv = original_sys_argv

    def test_is_gamescope_active(self):
        # Case 1: XDG_CURRENT_DESKTOP == "gamescope" → returns True
        with patch("os.environ.get", return_value="gamescope"):
            self.assertTrue(is_gamescope_active())

        # Case 2: Steam process running with -steampal → returns True
        with patch("subprocess.run") as mock_run:
            output = "1234 steam.sh -someflag -steampal"
            mock_run.return_value.stdout = output
            self.assertTrue(is_gamescope_active())

        # Case 3: Neither condition is met → returns False
        with patch("os.environ.get", return_value=""), patch(
            "subprocess.run"
        ) as mock_run:
            mock_run.side_effect = Exception("No process found")
            self.assertFalse(is_gamescope_active())

    def test_main_with_legacy_env_vars(self):
        # Test with legacy NSCB_PRECMD/NSCB_POSTCMD (without underscore)
        original_sys_argv = sys.argv
        sys.argv = ["nscb.py", "-f", "--", "vkcube"]

        mock_env = {
            "NSCB_PRECMD": "echo 'legacy pre'",
            "NSCB_POSTCMD": "echo 'legacy post'",
            "PATH": "/usr/bin:/bin",
        }

        with patch("nscb.find_executable", return_value=True), patch(
            "nscb.is_gamescope_active", return_value=False
        ), patch("os.system") as mock_system, patch("builtins.print"), patch(
            "os.environ", mock_env
        ):

            main()

            called_command = mock_system.call_args[0][0]
            parts = called_command.split("; ")
            self.assertEqual(len(parts), 3)
            self.assertEqual(parts[0], "echo 'legacy pre'")
            self.assertIn("gamescope -f -- vkcube", parts[1])
            self.assertEqual(parts[2], "echo 'legacy post'")

        sys.argv = original_sys_argv


if __name__ == "__main__":
    unittest.main()
