import os
import sys
import tempfile
from pathlib import Path

import pytest

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
from nscb import (  # noqa: E402
    main,
)


class TestE2EProfileExecution:
    """Test end-to-end profile execution scenarios"""

    def test_e2e_simple_profile_execution(self, mocker):
        config_content = (
            "gaming=-f -W 1920 -H 1080\nstreaming=--borderless -W 1280 -H 720\n"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch("sys.argv", ["nscb", "-p", "gaming", "--", "fake_app"])
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "gamescope" in call_args
            assert "-f" in call_args
            assert "1920" in call_args
            assert "1080" in call_args
            assert "fake_app" in call_args
        finally:
            os.unlink(config_path)

    def test_e2e_override_functionality(self, mocker):
        config_content = "gaming=-f -W 1920 -H 1080 --mangoapp\n"

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch(
                "sys.argv",
                ["nscb", "-p", "gaming", "--borderless", "-W", "2560", "--", "app"],
            )
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "--borderless" in call_args
            assert "-f" not in call_args
            assert "2560" in call_args
            assert "1920" not in call_args
            assert "--mangoapp" in call_args
            assert "app" in call_args
        finally:
            os.unlink(config_path)

    def test_e2e_separator_handling(self, mocker):
        config_content = "test_profile=-f -W 1920\n"

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch(
                "sys.argv",
                ["nscb", "-p", "test_profile", "--", "my_game", "arg1", "arg2"],
            )
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "gamescope" in call_args
            assert "-f" in call_args
            assert "1920" in call_args
            assert "my_game" in call_args
            assert "arg1" in call_args
            assert "arg2" in call_args
        finally:
            os.unlink(config_path)

    def test_e2e_multiple_profile_execution(self, mocker):
        config_content = """
gaming=-f -W 1920 -H 1080 --mangoapp
streaming=--borderless -W 1280 -H 720
performance=-H 1440 --framerate-limit=120
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch(
                "sys.argv",
                ["nscb", "--profiles=gaming,streaming,performance", "--", "game"],
            )
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "--borderless" in call_args
            assert "--mangoapp" in call_args
            assert "1280" in call_args
            assert "1440" in call_args
            assert "120" in call_args
            assert "game" in call_args
        finally:
            os.unlink(config_path)

    def test_e2e_complex_config_scenarios(self, mocker):
        config_content = """
# Performance profile
performance=-f -W 2560 -H 1440 --mangoapp --framerate-limit=120
# Quality profile
quality=--borderless -W 1920 -H 1080 --framerate-limit=60
# Compatibility profile
compatibility=-W 1280 -H 720 --fsr-sharpness 5 --backend sdl2
# High resolution profile
highres=-f -W 3840 -H 2160
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch(
                "sys.argv",
                [
                    "nscb",
                    "--profiles=performance,quality,compatibility",
                    "--",
                    "complex_game",
                ],
            )
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "gamescope" in call_args
            assert "--borderless" in call_args
            assert "--mangoapp" in call_args
            assert "1280" in call_args
            assert "720" in call_args
            assert "--fsr-sharpness" in call_args
            assert "5" in call_args
            assert "complex_game" in call_args
        finally:
            os.unlink(config_path)


class TestE2EErrorHandling:
    """Test end-to-end error handling scenarios"""

    def test_e2e_basic_error_handling(self, mocker):
        mocker.patch("sys.argv", ["nscb", "-p", "nonexistent"])
        mocker.patch("nscb.ConfigManager.find_config_file", return_value=None)
        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mocker.patch("builtins.print")
        mock_log = mocker.patch("logging.error")

        result = main()

        assert result == 1
        mock_log.assert_called_with("could not find nscb.conf")

    def test_e2e_advanced_error_condition_handling(self, mocker):
        mocker.patch("sys.argv", ["nscb", "-p", "gaming", "--invalid-arg"])
        mocker.patch("nscb.ConfigManager.find_config_file", return_value=None)
        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mocker.patch("builtins.print")
        mock_log = mocker.patch("logging.error")

        result = main()

        assert result == 1
        mock_log.assert_called_with("could not find nscb.conf")


class TestE2EConflictResolution:
    """Test end-to-end conflict resolution scenarios"""

    def test_e2e_conflict_resolution_real_world(self, mocker):
        config_content = """
# Different display modes that conflict
fullscreen=-f -W 2560 -H 1440 --fsr-sharpness 5
borderless=--borderless -W 1920 -H 1080 --backend sdl2
windowed=-W 1280 -H 720 -o HDMI-1
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch(
                "sys.argv", ["nscb", "-p", "fullscreen", "--borderless", "--", "app"]
            )
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "--borderless" in call_args
            assert "2560" in call_args
            assert "app" in call_args
        finally:
            os.unlink(config_path)


class TestE2EGamescopeDetection:
    """Test end-to-end gamescope detection scenarios"""

    def test_e2e_gamescope_detection_different_environments(self, mocker):
        config_content = "test_profile=-f -W 1920 -H 1080\n"

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            # Test when gamescope is active
            mocker.patch("sys.argv", ["nscb", "-p", "test_profile", "--", "game"])
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"})
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "game" in call_args

            # Test when gamescope is NOT active
            mock_run.reset_mock()
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            if mock_run.call_args:
                call_args = mock_run.call_args[0][0]
                assert "gamescope" in call_args
                assert "-f" in call_args
                assert "game" in call_args
        finally:
            os.unlink(config_path)


class TestE2EEnvironmentHooks:
    """Test end-to-end environment hook scenarios"""

    def test_e2e_environment_hook_execution(self, mocker):
        config_content = "gaming=-f -W 1920 -H 1080\n"

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch("sys.argv", ["nscb", "-p", "gaming", "--", "game"])
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mocker.patch.dict(
                "os.environ",
                {"NSCB_PRE_CMD": "before_cmd", "NSCB_POST_CMD": "after_cmd"},
            )
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "before_cmd" in call_args
            assert "after_cmd" in call_args
            assert "game" in call_args
        finally:
            os.unlink(config_path)


class TestE2ESystemStateTransitions:
    """Test end-to-end system state transition scenarios"""

    def test_e2e_system_state_transitions(self, mocker):
        config_content = "transition_test=-W 1920 -H 1080 --mangoapp\n"

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as config_file:
            config_file.write(config_content)
            config_path = Path(config_file.name)

        try:
            mocker.patch(
                "sys.argv", ["nscb", "-p", "transition_test", "--", "test_app"]
            )
            mocker.patch(
                "nscb.ConfigManager.find_config_file", return_value=config_path
            )
            mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
            mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
            mock_run = mocker.patch(
                "nscb.CommandExecutor.run_nonblocking", return_value=0
            )
            mocker.patch("builtins.print")

            result = main()

            assert (
                result == 0
            )  # main now returns an exit code instead of calling sys.exit
            call_args = mock_run.call_args[0][0]
            assert "gamescope" in call_args
            assert "1920" in call_args
            assert "1080" in call_args
            assert "test_app" in call_args
            assert "--mangoapp" in call_args
        finally:
            os.unlink(config_path)
