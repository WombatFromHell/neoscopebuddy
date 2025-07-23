#!/usr/bin/python3

import unittest
from unittest.mock import patch, MagicMock
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
    is_gamescope_active,
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

        # Test no config file found
        with patch.dict("os.environ", {"HOME": "/nonexistent", "XDG_CONFIG_HOME": ""}):
            self.assertIsNone(find_config_file())

    def test_config_loading(self):
        """Test loading configuration files with various formats."""
        config_path = self.test_root / "nscb.conf"

        # Test quoted and unquoted values
        config_path.write_text(
            """profile1 = value1
    quoted = "-W 640 -H 480"
    unquoted = -W 800 -H 600
    single_quoted = '-f --windowed'
    # This is a comment
    empty_line_above = test
    """
        )
        expected = {
            "profile1": "value1",
            "quoted": "-W 640 -H 480",
            "unquoted": "-W 800 -H 600",
            "single_quoted": "-f --windowed",
            "empty_line_above": "test",
        }
        self.assertEqual(load_config(config_path), expected)

        # Test edge cases
        config_path.write_text(
            """spaces_around = " value with spaces "
    no_quotes = value without quotes
    equals_in_value = key=value=more
    """
        )
        expected = {
            "spaces_around": " value with spaces ",
            "no_quotes": "value without quotes",
            "equals_in_value": "key=value=more",
        }
        self.assertEqual(load_config(config_path), expected)

    def test_executable_check(self):
        """Test finding executables in PATH."""
        # Test with executable in PATH
        with patch.dict("os.environ", {"PATH": str(self.test_root / "bin")}):
            Path(self.test_root / "bin").mkdir()
            gamescope_path = Path(self.test_root / "bin" / "gamescope")
            gamescope_path.touch()
            os.chmod(gamescope_path, 0o755)
            self.assertTrue(find_executable("gamescope"))
            self.assertFalse(find_executable("nonexistent"))

        # Test with non-executable file
        with patch.dict("os.environ", {"PATH": str(self.test_root / "bin2")}):
            Path(self.test_root / "bin2").mkdir()
            non_exec_path = Path(self.test_root / "bin2" / "gamescope")
            non_exec_path.touch()
            os.chmod(non_exec_path, 0o644)  # Not executable
            self.assertFalse(find_executable("gamescope"))

        # Test with empty PATH
        with patch.dict("os.environ", {"PATH": ""}):
            self.assertFalse(find_executable("gamescope"))

    def test_argument_parsing_comprehensive(self):
        """Test parsing command-line arguments comprehensively."""
        # No profile
        profile, remaining = parse_arguments(["-W", "1920", "-H", "1080"])
        self.assertIsNone(profile)
        self.assertEqual(remaining, ["-W", "1920", "-H", "1080"])

        # With profile (short syntax)
        profile, remaining = parse_arguments(["-p", "gaming", "-W", "1920"])
        self.assertEqual(profile, "gaming")
        self.assertEqual(remaining, ["-W", "1920"])

        # With profile (long syntax)
        profile, remaining = parse_arguments(["--profile", "vkcube", "--windowed"])
        self.assertEqual(profile, "vkcube")
        self.assertEqual(remaining, ["--windowed"])

        # With profile (equals syntax)
        profile, remaining = parse_arguments(["--profile=steam", "-W", "1920"])
        self.assertEqual(profile, "steam")
        self.assertEqual(remaining, ["-W", "1920"])

        # Profile at end
        profile, remaining = parse_arguments(["-W", "1920", "-p", "gaming"])
        self.assertEqual(profile, "gaming")
        self.assertEqual(remaining, ["-W", "1920"])

        # Multiple profile flags (last one wins)
        profile, remaining = parse_arguments(
            ["-p", "first", "--profile=second", "-W", "1920"]
        )
        self.assertEqual(profile, "second")
        self.assertEqual(remaining, ["-W", "1920"])

        # Error cases
        with patch("sys.stderr", StringIO()):
            with self.assertRaises(SystemExit):
                parse_arguments(["-p"])  # Missing profile name

            with self.assertRaises(SystemExit):
                parse_arguments(["--profile"])  # Missing profile name

    def test_argument_merging_comprehensive(self):
        """Test merging profile and command-line arguments comprehensively."""
        # No conflicts
        result = merge_arguments(["-W", "1920"], ["-f"])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Empty profile args
        result = merge_arguments([], ["-W", "1920", "-f"])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Empty override args
        result = merge_arguments(["-W", "1920", "-f"], [])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Both empty
        result = merge_arguments([], [])
        self.assertEqual(result, [])

        # Value flag conflicts (override takes precedence)
        result = merge_arguments(["-W", "1920", "-H", "1080"], ["-W", "2560"])
        self.assertEqual(result, ["-W", "2560", "-H", "1080"])

        # Exclusive flag conflicts
        result = merge_arguments(["--windowed"], ["-f"])
        self.assertEqual(result, ["-f"])

        result = merge_arguments(["--grab-cursor"], ["--force-grab-cursor"])
        self.assertEqual(result, ["--force-grab-cursor"])

        # Positional arguments
        result = merge_arguments(["-W", "1920", "steam"], ["-f"])
        self.assertEqual(result, ["-W", "1920", "-f", "steam"])

        # Double-dash handling
        result = merge_arguments(["-W", "1920"], ["-f", "--", "dota2"])
        self.assertEqual(result, ["-W", "1920", "-f", "--", "dota2"])

        result = merge_arguments(["-W", "1920", "--", "steam"], ["-f", "--", "dota2"])
        self.assertEqual(result, ["-W", "1920", "-f", "--", "dota2"])

        # Complex scenario with multiple conflicts
        result = merge_arguments(
            ["-W", "1920", "-H", "1080", "--windowed", "--grab-cursor", "app1"],
            ["-W", "2560", "-f", "--force-grab-cursor", "app2", "--", "args"],
        )
        self.assertEqual(
            result,
            [
                "-W",
                "2560",
                "-H",
                "1080",
                "-f",
                "--force-grab-cursor",
                "app1",
                "app2",
                "--",
                "args",
            ],
        )

    def test_main_execution_comprehensive(self):
        """Test main execution flow comprehensively."""
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
            """gaming = -W 1920 -H 1080 --windowed
quoted = "-f -W 800 -H 600"
complex = "-W 2560 -H 1440 steam -- --args"
"""
        )

        base_env = {"PATH": str(bin_dir), "XDG_CONFIG_HOME": str(xdg_config_dir)}

        # Test case 1: No profile
        with patch.dict("os.environ", base_env):
            with patch("sys.stdout", StringIO()) as _:
                with patch.object(sys, "argv", ["nscb.py", "-f", "--windowed"]):
                    with patch("os.system") as mock_system:
                        main()
                        # Verify the command construction
                        mock_system.assert_called_once()
                        call_args = mock_system.call_args[0][0]
                        self.assertIn("gamescope -f --windowed", call_args)

        # Test case 2: With profile
        with patch.dict("os.environ", base_env):
            with patch("sys.stdout", StringIO()) as _:
                with patch.object(sys, "argv", ["nscb.py", "-p", "gaming", "-f"]):
                    with patch("os.system") as mock_system:
                        main()
                        call_args = mock_system.call_args[0][0]
                        # Should merge profile args with command args
                        self.assertIn("gamescope -W 1920 -H 1080 -f", call_args)

        # Test case 3: Pre and post commands
        env_with_cmds = {
            **base_env,
            "NSCB_PRECMD": "echo 'starting'",
            "NSCB_POSTCMD": "echo 'finished'",
        }
        with patch.dict("os.environ", env_with_cmds):
            with patch("sys.stdout", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-f"]):
                    with patch("os.system") as mock_system:
                        main()
                        call_args = mock_system.call_args[0][0]
                        self.assertIn("'echo '\"'\"'starting'\"'\"''", call_args)
                        self.assertIn("'echo '\"'\"'finished'\"'\"''", call_args)

        # Test case 4: Complex profile with double-dash
        with patch.dict("os.environ", base_env):
            with patch("sys.stdout", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-p", "complex"]):
                    with patch("os.system") as mock_system:
                        main()
                        call_args = mock_system.call_args[0][0]
                        self.assertIn("steam", call_args)
                        self.assertIn("--args", call_args)

    def test_error_conditions(self):
        """Test various error conditions."""
        # Gamescope not found
        with patch.dict("os.environ", {"PATH": "/nonexistent"}):
            with patch("sys.stderr", StringIO()):
                with self.assertRaises(SystemExit):
                    main()

        # Config file not found when profile specified
        bin_dir = self.test_root / "bin"
        bin_dir.mkdir()
        gamescope_path = bin_dir / "gamescope"
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)

        with patch.dict(
            "os.environ",
            {"PATH": str(bin_dir), "XDG_CONFIG_HOME": "", "HOME": "/nonexistent"},
        ):
            with patch("sys.stderr", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-p", "gaming"]):
                    with self.assertRaises(SystemExit):
                        main()

        # Profile not found in config
        xdg_config_dir = self.test_root / "xdg2"
        xdg_config_dir.mkdir()
        config_path = xdg_config_dir / "nscb.conf"
        config_path.write_text("existing = -W 1920")

        with patch.dict(
            "os.environ", {"PATH": str(bin_dir), "XDG_CONFIG_HOME": str(xdg_config_dir)}
        ):
            with patch("sys.stderr", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-p", "nonexistent"]):
                    with self.assertRaises(SystemExit):
                        main()

    def test_shlex_integration(self):
        """Test that shlex is properly handling quoted arguments."""
        # Test config with complex quoting
        config_path = self.test_root / "nscb.conf"
        config_path.write_text(
            '''complex = "-W 1920 -H 1080 -- 'game with spaces' --option=value"'''
        )

        config = load_config(config_path)
        # The quotes should be removed by load_config
        self.assertEqual(
            config["complex"], "-W 1920 -H 1080 -- 'game with spaces' --option=value"
        )

        # Test that shlex.split properly handles the value
        import shlex

        args = shlex.split(config["complex"])
        expected = [
            "-W",
            "1920",
            "-H",
            "1080",
            "--",
            "game with spaces",
            "--option=value",
        ]
        self.assertEqual(args, expected)

    def test_environment_variable_handling(self):
        """Test handling of NSCB_PRECMD and NSCB_POSTCMD environment variables."""
        bin_dir = self.test_root / "bin"
        bin_dir.mkdir()
        gamescope_path = bin_dir / "gamescope"
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)

        # Test with special characters in commands
        env_vars = {
            "PATH": str(bin_dir),
            "NSCB_PRECMD": "echo 'test with spaces & special chars'",
            "NSCB_POSTCMD": "notify-send 'Game finished' || true",
            "XDG_CONFIG_HOME": "",
            "HOME": "/nonexistent",
        }

        with patch.dict("os.environ", env_vars):
            with patch("sys.stdout", StringIO()):
                with patch.object(sys, "argv", ["nscb.py", "-f"]):
                    with patch("os.system") as mock_system:
                        main()
                        call_args = mock_system.call_args[0][0]
                        # Verify that commands are properly quoted
                        self.assertIn("&", call_args)  # Should contain the pre command
                        self.assertIn(
                            "||", call_args
                        )  # Should contain the post command

    def test_path_edge_cases(self):
        """Test edge cases in PATH handling."""
        # Test with multiple PATH entries
        bin1 = self.test_root / "bin1"
        bin2 = self.test_root / "bin2"
        bin1.mkdir()
        bin2.mkdir()

        # Put gamescope in second directory
        gamescope_path = bin2 / "gamescope"
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)

        with patch.dict("os.environ", {"PATH": f"{bin1}:{bin2}"}):
            self.assertTrue(find_executable("gamescope"))

        # Test with PATH containing non-existent directories
        with patch.dict("os.environ", {"PATH": f"/nonexistent:{bin2}"}):
            self.assertTrue(find_executable("gamescope"))

    def test_merge_arguments_comprehensive(self):
        """Test merging profile and command-line arguments comprehensively."""
        # No conflicts
        result = merge_arguments(["-W", "1920"], ["-f"])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Empty profile args
        result = merge_arguments([], ["-W", "1920", "-f"])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Empty override args
        result = merge_arguments(["-W", "1920", "-f"], [])
        self.assertEqual(result, ["-W", "1920", "-f"])

        # Both empty
        result = merge_arguments([], [])
        self.assertEqual(result, [])

        # Value flag conflicts (override takes precedence)
        result = merge_arguments(["-W", "1920", "-H", "1080"], ["-W", "2560"])
        self.assertEqual(result, ["-W", "2560", "-H", "1080"])

        # Exclusive flag conflicts
        result = merge_arguments(["--windowed"], ["-f"])
        self.assertEqual(result, ["-f"])

        result = merge_arguments(["--grab-cursor"], ["--force-grab-cursor"])
        self.assertEqual(result, ["--force-grab-cursor"])

        # Positional arguments
        result = merge_arguments(["-W", "1920", "steam"], ["-f"])
        self.assertEqual(result, ["-W", "1920", "-f", "steam"])

        # Double-dash handling
        result = merge_arguments(["-W", "1920"], ["-f", "--", "dota2"])
        self.assertEqual(result, ["-W", "1920", "-f", "--", "dota2"])

        result = merge_arguments(["-W", "1920", "--", "steam"], ["-f", "--", "dota2"])
        self.assertEqual(result, ["-W", "1920", "-f", "--", "dota2"])

        # Complex scenario with multiple conflicts
        result = merge_arguments(
            ["-W", "1920", "-H", "1080", "--windowed", "--grab-cursor", "app1"],
            ["-W", "2560", "-f", "--force-grab-cursor", "app2", "--", "args"],
        )
        self.assertEqual(
            result,
            [
                "-W",
                "2560",
                "-H",
                "1080",
                "-f",
                "--force-grab-cursor",
                "app1",
                "app2",
                "--",
                "args",
            ],
        )

    def test_is_gamescope_active(self):
        """Test is_gamescope_active with various scenarios."""

        # Case 1: XDG_CURRENT_DESKTOP == "gamescope" => return True
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "gamescope"}):
            self.assertTrue(is_gamescope_active())

        # Case 2: Process matches "steam.sh -.+ -steampal"
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "1234 pts/0  S+  0:00 steam.sh some-args -steampal"
            mock_run.return_value = mock_result
            self.assertTrue(is_gamescope_active())

        # Case 3: No matching process, no XDG_CURRENT_DESKTOP == gamescope => return False
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "1234 pts/0  S+  0:00 steam.sh -no-args"
            mock_run.return_value = mock_result

            self.assertFalse(is_gamescope_active())


def test_main_output_when_gamescope_active(self):
    """Test that when Gamescope is active, full_command excludes 'gamescope' and includes application part."""

    bin_dir = self.test_root / "bin"
    bin_dir.mkdir()
    gamescope_path = bin_dir / "gamescope"
    gamescope_path.touch()
    os.chmod(gamescope_path, 0o755)

    # Mock environment variables
    base_env = {
        "PATH": str(bin_dir),
        "NSCB_PRECMD": "echo 'pre-command'",
        "NSCB_POSTCMD": "echo 'post-command'",
    }

    with patch.dict("os.environ", base_env):
        with patch("nscb.is_gamescope_active", return_value=True):
            # Simulate command-line arguments including a -- and an app to run
            with patch.object(sys, "argv", ["nscb.py", "--", "steam.sh"]):

                captured_output = StringIO()
                with patch("sys.stdout", captured_output):
                    main()

                output = captured_output.getvalue()
                self.assertIn("Executing:", output)
                self.assertNotIn("gamescope", output)  # Verify Gamescope not present
                self.assertIn(
                    "echo 'pre-command'; steam.sh; echo 'post-command'", output
                )


if __name__ == "__main__":
    unittest.main()
