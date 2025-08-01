#!/usr/bin/python3

import unittest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from nscb import main, is_gamescope_active, get_env_commands


class TestNSCBIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_run_nonblocking = patch(
            "nscb.run_nonblocking", return_value=0
        ).start()
        self.mock_subprocess = patch("subprocess.Popen").start()
        self.mock_exit = patch("sys.exit").start()
        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        mock_process.stdout = None
        mock_process.stderr = None
        self.mock_subprocess.return_value = mock_process

    def tearDown(self):
        patch.stopall()

    def test_main_chained_profiles(self):
        """Test end-to-end with chained -p profile invocations"""
        config_content = """
gaming=-f -W 1920 -H 1080
desktop=-b -W 2560
"""
        with (
            patch("nscb.find_executable", return_value=True),
            patch(
                "sys.argv",
                ["nscb", "-p", "gaming", "-p", "desktop", "--", "steam"],
            ),
            patch("nscb.find_config_file", return_value=Path("/fake/config")),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch("nscb.is_gamescope_active", return_value=False),
            patch("builtins.print", lambda *_: None),
        ):
            main()

            expected_cmd = "gamescope -b -W 2560 -H 1080 -- steam"
            self.mock_run_nonblocking.assert_called_once_with(expected_cmd)
            self.mock_exit.assert_called_once_with(0)

    def test_is_gamescope_active_all_scenarios(self):
        """Verify all three gamescope detection scenarios in single method"""
        import os
        import subprocess

        # Scenario 1: Environment variable match (gamescope active)
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "gamescope"}):
            self.assertTrue(
                is_gamescope_active(), "Should detect gamescope via XDG_CURRENT_DESKTOP"
            )

        # Scenario 2: Process detection - fixed negative case
        for ps_output, expected in [
            ("1234 ? 00:00:00 gamescope", True),  # Positive case (contains "gamescope")
            (
                "system processes running normally",
                False,
            ),  # Negative case (no "gamescope" substring)
        ]:
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "subprocess.check_output", return_value=ps_output
                ) as mock_check:
                    self.assertEqual(
                        is_gamescope_active(),
                        expected,
                        f"Should detect {'gamescope' if expected else 'no gamescope'}",
                    )
                    mock_check.assert_called_once_with(
                        ["ps", "ax"], stderr=subprocess.STDOUT, text=True
                    )

    def test_build_command_string_integration(self):
        """Integration test command building across common env var permutations"""
        import os

        config_content = "gaming=-f -W 1920 -H 1080"
        test_cases = [
            (
                {"NSCB_PRE_CMD": "", "NSCB_POST_CMD": ""},
                "gamescope -f -W 1920 -H 1080 -- steam",
            ),
            (
                {"NSCB_PRE_CMD": "echo 'Starting...'", "NSCB_POST_CMD": ""},
                "echo 'Starting...'; gamescope -f -W 1920 -H 1080 -- steam",
            ),
            (
                {"NSCB_PRE_CMD": "", "NSCB_POST_CMD": "echo 'Finishing...'"},
                "gamescope -f -W 1920 -H 1080 -- steam; echo 'Finishing...'",
            ),
            (
                {
                    "NSCB_PRE_CMD": "echo 'Starting...'",
                    "NSCB_POST_CMD": "echo 'Finishing...'",
                },
                "echo 'Starting...'; gamescope -f -W 1920 -H 1080 -- steam; echo 'Finishing...'",
            ),
        ]

        for env_vars, expected_cmd in test_cases:
            with (
                patch("nscb.find_executable", return_value=True),
                patch("sys.argv", ["nscb", "-p", "gaming", "--", "steam"]),
                patch("nscb.find_config_file", return_value=Path("/fake/config")),
                patch("builtins.open", mock_open(read_data=config_content)),
                patch("nscb.is_gamescope_active", return_value=False),
                patch("builtins.print", lambda *_: None),
                patch.dict(os.environ, env_vars),
            ):
                pre_cmd, post_cmd = get_env_commands()
                self.assertEqual(pre_cmd, env_vars["NSCB_PRE_CMD"])
                self.assertEqual(post_cmd, env_vars["NSCB_POST_CMD"])

                with patch("nscb.run_nonblocking") as mock_run:
                    main()
                    mock_run.assert_called_once_with(expected_cmd)


if __name__ == "__main__":
    unittest.main()
