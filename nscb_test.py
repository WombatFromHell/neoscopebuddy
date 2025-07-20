#!/usr/bin/python3

import unittest
from unittest.mock import patch
import os
import shutil
from pathlib import Path
import sys
from io import StringIO
from nscb import (
    find_config_file,
    find_executable,
    load_config,
    merge_arguments,
    parse_arguments,
    main,
)


class TestNSCB(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for testing."""
        self.test_root = Path("/tmp/nscb_test")
        self.test_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up after each test."""
        shutil.rmtree(self.test_root, ignore_errors=True)

    def test_config_file_handling(self):
        """Test finding and loading config files."""
        # Test XDG_CONFIG_HOME
        xdg_config = self.test_root / "xdg"
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(xdg_config)}):
            xdg_config.mkdir(parents=True)
            (xdg_config / "nscb.conf").touch()
            self.assertEqual(find_config_file(), xdg_config / "nscb.conf")

        # Test HOME fallback
        home_config = self.test_root / "home" / ".config"
        with patch.dict(
            "os.environ", {"HOME": str(self.test_root / "home"), "XDG_CONFIG_HOME": ""}
        ):
            home_config.mkdir(parents=True)
            (home_config / "nscb.conf").touch()
            self.assertEqual(find_config_file(), home_config / "nscb.conf")

        # Test config loading with quoted and unquoted values
        config_path = self.test_root / "nscb.conf"
        config_path.write_text(
            """profile1 = value1
    quoted = "-W 640 -H 480"
    unquoted = -W 800 -H 600
    """
        )
        expected = {
            "profile1": "value1",
            "quoted": "-W 640 -H 480",
            "unquoted": "-W 800 -H 600",
        }
        self.assertEqual(load_config(config_path), expected)

    def test_executable_check(self):
        """Test finding executables in PATH."""
        with patch.dict("os.environ", {"PATH": str(self.test_root / "bin")}):
            Path(self.test_root / "bin").mkdir()
            gamescope_path = Path(self.test_root / "bin" / "gamescope")
            gamescope_path.touch()
            os.chmod(gamescope_path, 0o755)
            self.assertTrue(find_executable("gamescope"))
            self.assertFalse(find_executable("nonexistent"))

    def test_argument_parsing(self):
        """Test parsing command-line arguments."""
        # No profile
        profile, remaining = parse_arguments(["-W", "1920", "-H", "1080"])
        self.assertIsNone(profile)
        self.assertEqual(remaining, ["-W", "1920", "-H", "1080"])

        # With profile (short, long, and equals syntax)
        profile, remaining = parse_arguments(["-p", "gaming", "-W", "1920"])
        self.assertEqual(profile, "gaming")
        self.assertEqual(remaining, ["-W", "1920"])

        profile, remaining = parse_arguments(["--profile", "vkcube", "--windowed"])
        self.assertEqual(profile, "vkcube")
        self.assertEqual(remaining, ["--windowed"])

        profile, remaining = parse_arguments(["--profile=steam", "-W", "1920"])
        self.assertEqual(profile, "steam")
        self.assertEqual(remaining, ["-W", "1920"])

        # Error case
        with patch("sys.stderr", StringIO()):
            with self.assertRaises(SystemExit):
                parse_arguments(["-p"])

    def test_argument_merging(self):
        """Test merging profile and command-line arguments."""
        # No conflicts
        result = merge_arguments(["-W", "1920"], ["-f"])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Conflicts (override takes precedence)
        result = merge_arguments(["-W", "1920", "--windowed"], ["-f"])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Positional and double-dash handling
        result = merge_arguments(["-W", "1920", "steam"], ["-f", "--", "dota2"])
        self.assertEqual(result, ["-W", "1920", "-f", "steam", "--", "dota2"])

        # Complex scenario
        result = merge_arguments(
            ["-W", "2560", "-H", "1080", "--grab-cursor"],
            ["-f", "--force-grab-cursor", "--", "dota2"],
        )
        self.assertEqual(
            result,
            ["-W", "2560", "-H", "1080", "-f", "--force-grab-cursor", "--", "dota2"],
        )

    def test_main_execution(self):
        """Test main execution flow."""
        # Setup environment
        bin_dir = self.test_root / "bin"
        bin_dir.mkdir()
        gamescope_path = bin_dir / "gamescope"
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)

        xdg_config_dir = self.test_root / "xdg"
        xdg_config_dir.mkdir()
        config_path = xdg_config_dir / "nscb.conf"
        config_path.write_text(
            """gaming = -W 1920 -H 1080
quoted = "-f -W 800 -H 600"
"""
        )

        env_vars = {"PATH": str(bin_dir), "XDG_CONFIG_HOME": str(xdg_config_dir)}

        # Test cases
        with patch.dict("os.environ", env_vars):
            # No profile
            with patch("sys.stdout", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-f"]):
                    with patch.object(os, "execvp") as mock_execvp:
                        main()
                        mock_execvp.assert_called_with("gamescope", ["-f"])

            # With profile
            with patch("sys.stdout", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-p", "gaming", "-f"]):
                    with patch.object(os, "execvp") as mock_execvp:
                        main()
                        mock_execvp.assert_called_with(
                            "gamescope", ["-W", "1920", "-H", "1080", "-f"]
                        )

            # Quoted profile args
            with patch("sys.stdout", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-p", "quoted"]):
                    with patch.object(os, "execvp") as mock_execvp:
                        main()
                        mock_execvp.assert_called_with(
                            "gamescope", ["-f", "-W", "800", "-H", "600"]
                        )

            # Error cases
            with patch("sys.stderr", StringIO()):
                with self.assertRaises(SystemExit):
                    with patch.object(sys, "argv", ["nscb.py", "-p", "nonexistent"]):
                        main()


if __name__ == "__main__":
    unittest.main()
