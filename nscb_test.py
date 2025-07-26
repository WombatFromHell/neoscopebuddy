#!/usr/bin/python3

import sys
from pathlib import Path
import unittest
from unittest.mock import patch, mock_open

from nscb import NSCBConfig, ArgumentParser, GameScopeChecker, CommandBuilder, main


class BaseTestCase(unittest.TestCase):
    """Base test case with common utilities."""

    def setUp(self):
        """Save original sys.argv for tests that modify it."""
        self.original_argv = sys.argv

    def tearDown(self):
        """Restore original sys.argv."""
        sys.argv = self.original_argv

    def mock_env(self, env_vars):
        """Helper to mock environment variables."""
        return patch(
            "os.environ.get",
            side_effect=lambda key, default="": env_vars.get(key, default),
        )


class TestNSCBConfig(BaseTestCase):
    """Test configuration file handling."""

    def test_find_config_file_locations(self):
        """Test config file discovery in different locations."""
        test_cases = [
            # (XDG_CONFIG_HOME, HOME, expected_path)
            ("custom_path", None, Path("custom_path/nscb.conf")),
            (None, "home_path", Path("home_path/.config/nscb.conf")),
            (None, None, None),
        ]

        for xdg_path, home_path, expected in test_cases:
            with self.subTest(xdg=xdg_path, home=home_path):
                env_vars = {}
                if xdg_path:
                    env_vars["XDG_CONFIG_HOME"] = xdg_path
                if home_path:
                    env_vars["HOME"] = home_path

                with self.mock_env(env_vars), patch.object(
                    Path, "exists", return_value=bool(expected)
                ):
                    result = NSCBConfig.find_config_file()
                    self.assertEqual(result, expected)

    def test_load_config_formats(self):
        """Test loading config with various formats."""
        config_content = """# Comment line
profile1="-f --windowed"
profile2='-W 1920 -H 1080'
profile3=unquoted_value
empty_line_above=test
"""

        with patch("builtins.open", mock_open(read_data=config_content)):
            config = NSCBConfig.load_config(Path("/fake/config"))

            expected = {
                "profile1": "-f --windowed",
                "profile2": "-W 1920 -H 1080",
                "profile3": "unquoted_value",
                "empty_line_above": "test",
            }
            self.assertEqual(config, expected)


class TestArgumentParser(BaseTestCase):
    """Test argument parsing functionality."""

    def test_parse_profile_args_formats(self):
        """Test parsing profile arguments in different formats."""
        test_cases = [
            (["-p", "profile1", "--other"], "profile1", ["--other"]),
            (["--profile", "profile2", "-f"], "profile2", ["-f"]),
            (["--profile=profile3", "-W", "1920"], "profile3", ["-W", "1920"]),
            (["--other", "-f"], None, ["--other", "-f"]),
        ]

        for args, expected_profile, expected_remaining in test_cases:
            with self.subTest(args=args):
                profile, remaining = ArgumentParser.parse_profile_args(args)
                self.assertEqual(profile, expected_profile)
                self.assertEqual(remaining, expected_remaining)

    def test_parse_profile_args_errors(self):
        """Test error handling in profile argument parsing."""
        error_cases = [["-p"], ["--profile"]]

        for args in error_cases:
            with self.subTest(args=args):
                with patch("sys.stderr"), self.assertRaises(SystemExit):
                    ArgumentParser.parse_profile_args(args)

    def test_merge_arguments_edge_cases(self):
        """Test argument merging edge cases."""
        test_cases = [
            # (profile_args, override_args, description)
            ([], [], "both empty"),
            (["-f"], [], "override empty"),
            ([], ["-f"], "profile empty"),
        ]

        for profile_args, override_args, description in test_cases:
            with self.subTest(case=description):
                result = ArgumentParser.merge_arguments(profile_args, override_args)
                expected = profile_args if override_args == [] else override_args
                self.assertEqual(result, expected)

    def test_merge_arguments_complex_scenarios(self):
        """Test complex argument merging scenarios."""
        # Test value flag override
        profile_args = ["-W", "1920", "-H", "1080", "-f"]
        override_args = ["-W", "2560", "--force-grab-cursor", "--", "steam"]
        result = ArgumentParser.merge_arguments(profile_args, override_args)

        # Override value should replace profile value
        self.assertIn("-W", result)
        self.assertIn("2560", result)
        self.assertNotIn("1920", result)
        # Profile values should remain
        self.assertIn("-H", result)
        self.assertIn("1080", result)
        self.assertIn("-f", result)
        # New args should be added
        self.assertIn("--force-grab-cursor", result)
        self.assertIn("--", result)
        self.assertIn("steam", result)

    def test_merge_arguments_exclusive_groups(self):
        """Test exclusive flag group handling."""
        profile_args = ["--windowed", "-H", "1080"]
        override_args = ["-f"]
        result = ArgumentParser.merge_arguments(profile_args, override_args)

        # Verify basic merging works
        self.assertIn("-f", result)
        self.assertIn("-H", result)
        self.assertIn("1080", result)

        # Test a clearer exclusive group scenario
        # When override contains -f, it should remove --windowed from earlier position
        profile_args2 = ["-H", "1080", "--windowed"]
        override_args2 = ["-f"]
        result2 = ArgumentParser.merge_arguments(profile_args2, override_args2)

        # The override -f should be present
        self.assertIn("-f", result2)
        # Other non-conflicting args should remain
        self.assertIn("-H", result2)
        self.assertIn("1080", result2)


class TestGameScopeChecker(BaseTestCase):
    """Test gamescope detection functionality."""

    def test_find_executable_scenarios(self):
        """Test executable finding in various scenarios."""
        test_cases = [
            # (path_exists, is_file, executable, expected)
            (True, True, True, True),  # Found and executable
            (False, True, True, False),  # Not in path
            (True, False, True, False),  # Not a file
            (True, True, False, False),  # Not executable
        ]

        for path_exists, is_file, executable, expected in test_cases:
            with self.subTest(exists=path_exists, file=is_file, exec=executable):
                env_vars = {"PATH": "/usr/bin:/bin"}

                with self.mock_env(env_vars):
                    # Mock Path.exists to return different values based on the path
                    def mock_exists(self):
                        path_str = str(self)
                        # Return True for PATH directories so they pass the exists() check
                        if path_str in ["/usr/bin", "/bin"]:
                            return True
                        # For the executable file itself, return the test parameter
                        if path_str.endswith("/gamescope"):
                            return path_exists
                        # Default case for other paths
                        return True

                    # Mock Path.is_file to return different values based on the path
                    def mock_is_file(self):
                        path_str = str(self)
                        # Only return is_file for the actual gamescope executable path
                        if path_str.endswith("/gamescope"):
                            return (
                                is_file and path_exists
                            )  # File must exist AND be a file
                        # Other paths (like directories) are not files
                        return False

                    with patch.object(Path, "exists", mock_exists), patch.object(
                        Path, "is_file", mock_is_file
                    ), patch("os.access", return_value=executable):

                        result = GameScopeChecker.find_executable("gamescope")
                        self.assertEqual(result, expected)

    def test_is_gamescope_active_detection_methods(self):
        """Test different gamescope detection methods."""
        test_cases = [
            # (xdg_desktop, ps_output, expected)
            ("gamescope", "", True),  # XDG desktop detection
            ("", "1234 steam.sh -flag -steampal", True),  # Process detection
            ("kde", "other process", False),  # Not detected
        ]

        for xdg_desktop, ps_output, expected in test_cases:
            with self.subTest(xdg=xdg_desktop, ps=bool(ps_output)):
                with patch("os.environ.get", return_value=xdg_desktop), patch(
                    "subprocess.run"
                ) as mock_run:

                    mock_run.return_value.stdout = ps_output
                    result = GameScopeChecker.is_gamescope_active()
                    self.assertEqual(result, expected)

    def test_is_gamescope_active_exception_handling(self):
        """Test exception handling in gamescope detection."""
        with patch("os.environ.get", return_value=""), patch(
            "subprocess.run", side_effect=Exception("Process error")
        ):
            result = GameScopeChecker.is_gamescope_active()
            self.assertFalse(result)


class TestCommandBuilder(BaseTestCase):
    """Test command building functionality."""

    def test_get_env_commands_priority(self):
        """Test environment command priority (new vs legacy)."""
        test_cases = [
            # (env_vars, expected_pre, expected_post)
            (
                {"NSCB_PRE_CMD": "new pre", "NSCB_POST_CMD": "new post"},
                "new pre",
                "new post",
            ),
            (
                {"NSCB_PRECMD": "legacy pre", "NSCB_POSTCMD": "legacy post"},
                "legacy pre",
                "legacy post",
            ),
            (
                {"NSCB_PRE_CMD": "new", "NSCB_PRECMD": "legacy"},
                "new",
                "",
            ),  # New takes priority
            ({}, "", ""),  # Empty when not set
        ]

        for env_vars, expected_pre, expected_post in test_cases:
            with self.subTest(env_vars=list(env_vars.keys())):
                with self.mock_env(env_vars):
                    pre_cmd, post_cmd = CommandBuilder.get_env_commands()
                    self.assertEqual(pre_cmd, expected_pre)
                    self.assertEqual(post_cmd, expected_post)

    def test_build_command_string_filtering(self):
        """Test command string building with empty part filtering."""
        test_cases = [
            (
                ["echo pre", "gamescope -f", "echo post"],
                "echo pre; gamescope -f; echo post",
            ),
            (["", "gamescope -f", ""], "gamescope -f"),
            (["", "", ""], ""),
            ([], ""),
        ]

        for parts, expected in test_cases:
            with self.subTest(parts=parts):
                result = CommandBuilder.build_command_string(parts)
                self.assertEqual(result, expected)

    def test_execute_gamescope_command_modes(self):
        """Test command execution in different modes."""
        final_args = ["-f", "-W", "1920", "--", "steam"]

        # Test normal mode (gamescope not active)
        with self.mock_env({}), patch.object(
            GameScopeChecker, "is_gamescope_active", return_value=False
        ), patch.object(
            CommandBuilder, "run_with_pty", return_value=0
        ) as mock_run, patch(
            "builtins.print"
        ), patch(
            "sys.exit"
        ):

            CommandBuilder.execute_gamescope_command(final_args)

            mock_run.assert_called_once()
            called_command = mock_run.call_args[0][0]
            self.assertIn("gamescope -f -W 1920 -- steam", called_command)

    def test_execute_gamescope_command_active_mode(self):
        """Test command execution when gamescope is already active."""
        test_cases = [
            # (final_args, expected_in_command)
            (["-f", "-W", "1920", "--", "steam"], "steam"),
            (["-f", "-W", "1920"], ""),  # No app to run
        ]

        for final_args, expected_in_command in test_cases:
            with self.subTest(args=final_args):
                with self.mock_env({}), patch.object(
                    GameScopeChecker, "is_gamescope_active", return_value=True
                ), patch.object(
                    CommandBuilder, "run_with_pty", return_value=0
                ) as mock_run, patch(
                    "builtins.print"
                ), patch(
                    "sys.exit"
                ):

                    CommandBuilder.execute_gamescope_command(final_args)

                    if expected_in_command:
                        mock_run.assert_called_once()
                        called_command = mock_run.call_args[0][0]
                        self.assertEqual(called_command, expected_in_command)
                    else:
                        # When there's no command to run, it should still call run_with_pty
                        # but with an empty command (which gets filtered out)
                        mock_run.assert_not_called()

    def test_execute_gamescope_command_with_env_commands(self):
        """Test execution with pre/post environment commands."""
        final_args = ["-f", "--", "steam"]
        env_vars = {"NSCB_PRE_CMD": "echo start", "NSCB_POST_CMD": "echo end"}

        with self.mock_env(env_vars), patch.object(
            GameScopeChecker, "is_gamescope_active", return_value=False
        ), patch.object(
            CommandBuilder, "run_with_pty", return_value=0
        ) as mock_run, patch(
            "builtins.print"
        ), patch(
            "sys.exit"
        ):

            CommandBuilder.execute_gamescope_command(final_args)

            called_command = mock_run.call_args[0][0]
            expected = "echo start; gamescope -f -- steam; echo end"
            self.assertEqual(called_command, expected)


class TestMainIntegration(BaseTestCase):
    """Test main function integration scenarios."""

    def test_main_error_conditions(self):
        """Test main function error handling."""
        error_cases = [
            # (find_executable, find_config, config_data, profile, expected_exit)
            (False, None, {}, None, "gamescope not found"),
            (True, None, {}, "profile", "config file not found"),
            (True, Path("/config"), {}, "missing", "profile not found"),
        ]

        for find_exec, find_conf, config_data, profile, error_desc in error_cases:
            with self.subTest(error=error_desc):
                sys.argv = ["nscb.py"] + (["-p", profile] if profile else [])

                with patch.object(
                    GameScopeChecker, "find_executable", return_value=find_exec
                ), patch.object(
                    NSCBConfig, "find_config_file", return_value=find_conf
                ), patch.object(
                    NSCBConfig, "load_config", return_value=config_data
                ), patch(
                    "sys.stderr"
                ), self.assertRaises(
                    SystemExit
                ):
                    main()

    def test_main_successful_scenarios(self):
        """Test successful main function execution scenarios."""
        test_cases = [
            # (use_profile, gamescope_active, description)
            (False, False, "no profile, normal mode"),
            (True, False, "with profile, normal mode"),
            (False, True, "no profile, gamescope active"),
            (True, True, "with profile, gamescope active"),
        ]

        mock_config = {"test": "-f -H 1440"}

        for use_profile, gamescope_active, description in test_cases:
            with self.subTest(case=description):
                if use_profile:
                    sys.argv = ["nscb.py", "-p", "test", "-W", "2560", "--", "steam"]
                else:
                    sys.argv = ["nscb.py", "-W", "1920", "--", "steam"]

                with patch.object(
                    GameScopeChecker, "find_executable", return_value=True
                ), patch.object(
                    NSCBConfig,
                    "find_config_file",
                    return_value=Path("/config") if use_profile else None,
                ), patch.object(
                    NSCBConfig, "load_config", return_value=mock_config
                ), patch.object(
                    GameScopeChecker,
                    "is_gamescope_active",
                    return_value=gamescope_active,
                ), patch.object(
                    CommandBuilder, "run_with_pty", return_value=0
                ) as mock_run, patch(
                    "builtins.print"
                ), patch(
                    "sys.exit"
                ), self.mock_env(
                    {}
                ):
                    main()
                    # Verify execution occurred
                    if gamescope_active:
                        try:
                            dash_index = sys.argv.index("--")
                            app_command = " ".join(sys.argv[dash_index + 1 :])
                            if app_command:
                                mock_run.assert_called_once()
                                called_command = mock_run.call_args[0][0]
                                self.assertEqual(called_command, app_command)
                            else:
                                mock_run.assert_not_called()
                        except ValueError:
                            # No -- separator when gamescope active means no app to run
                            mock_run.assert_not_called()
                    else:
                        # Normal mode - gamescope command should be executed
                        mock_run.assert_called_once()
                        called_command = mock_run.call_args[0][0]

                        if use_profile:
                            # Should contain merged profile and command line args
                            self.assertIn("-f", called_command)  # from profile
                            self.assertIn("-H 1440", called_command)  # from config

                        self.assertIn("gamescope", called_command)

                        if "--" in " ".join(sys.argv):
                            self.assertIn("steam", called_command)

    def test_main_full_integration(self):
        """Test complete integration with all features."""
        sys.argv = ["nscb.py", "-p", "test", "-W", "2560", "--", "steam"]
        mock_config = {"test": "-f -H 1440"}
        env_vars = {"NSCB_PRE_CMD": "echo start", "NSCB_POST_CMD": "echo end"}

        with patch.object(
            GameScopeChecker, "find_executable", return_value=True
        ), patch.object(
            NSCBConfig, "find_config_file", return_value=Path("/config")
        ), patch.object(
            NSCBConfig, "load_config", return_value=mock_config
        ), patch.object(
            GameScopeChecker, "is_gamescope_active", return_value=False
        ), patch.object(
            CommandBuilder, "run_with_pty", return_value=0
        ) as mock_run, patch(
            "builtins.print"
        ), patch(
            "sys.exit"
        ), self.mock_env(
            env_vars
        ):

            main()

            called_command = mock_run.call_args[0][0]

            # Verify all components are present
            self.assertIn("echo start", called_command)  # Pre command
            self.assertIn("gamescope", called_command)  # Gamescope command
            self.assertIn("-f", called_command)  # Profile arg
            self.assertIn("-H 1440", called_command)  # Profile arg
            self.assertIn("-W 2560", called_command)  # Override arg
            self.assertIn("steam", called_command)  # Application
            self.assertIn("echo end", called_command)  # Post command


if __name__ == "__main__":
    unittest.main()
