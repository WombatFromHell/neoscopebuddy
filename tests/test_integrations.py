import sys
from pathlib import Path

import pytest
from conftest import SystemExitCalled

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
from nscb import (  # noqa: E402
    CommandExecutor,
    SystemDetector,
    main,
)


def cmd_has_flag(cmd: str, flag: str) -> bool:
    """
    Check if a command string contains a specific flag as a separate argument.
    This prevents false positives when searching for substrings like '-f' in '--framerate-limit'.
    """
    import shlex

    cmd_parts = shlex.split(cmd.replace(";", " "))
    return flag in cmd_parts


class TestMainWorkflow:
    """Test main workflow with various scenarios"""

    def test_main_complete_workflow_with_profiles(
        self, mock_integration_setup, mock_system_exit, mocker, mock_config_file
    ):
        config_data = """
# Config file with comments
gaming=-f -W 1920 -H 1080
streaming=--borderless -W 1280 -H 720
"""
        cmd = "nscb --profiles=gaming,streaming -W 1600 -- app".split(" ")

        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch("sys.argv", cmd)
        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "gamescope" in called_cmd
        assert "-W 1600" in called_cmd
        assert "app" in called_cmd

    def test_main_error_scenarios(self, mocker):
        # Test missing gamescope executable
        mocker.patch("nscb.SystemDetector.find_executable", return_value=False)
        mock_log = mocker.patch("logging.error")
        mocker.patch(
            "sys.argv", ["nscb", "-p", "gaming"]
        )  # Provide a profile to avoid help

        result = main()
        assert result == 1
        mock_log.assert_called_with("'gamescope' not found in PATH")

    def test_main_error_missing_gamescope(self, mocker):
        mocker.patch("nscb.SystemDetector.find_executable", return_value=False)
        mock_log = mocker.patch("logging.error")
        mocker.patch("sys.argv", ["nscb", "-p", "gaming"])

        result = main()
        assert result == 1
        mock_log.assert_called_with("'gamescope' not found in PATH")

    def test_main_error_missing_config(self, mocker):
        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mocker.patch("nscb.ConfigManager.find_config_file", return_value=None)
        mock_log = mocker.patch("logging.error")
        mocker.patch("sys.argv", ["nscb", "-p", "gaming"])

        result = main()
        assert result == 1
        mock_log.assert_called_with("could not find nscb.conf")

    def test_main_error_missing_profiles(self, mocker, mock_config_file):
        config_data = "existing=-f -W 1920 -H 1080\n"

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mock_log = mocker.patch("logging.error")
        mocker.patch("sys.argv", ["nscb", "-p", "nonexistent"])

        result = main()
        assert result == 1
        mock_log.assert_called_with("profile nonexistent not found")

    @pytest.mark.parametrize(
        "cmd_args,expected_flags",
        [
            (["nscb", "-p", "gaming"], ["-f", "1920", "1080"]),
            (["nscb", "--profiles=gaming,streaming"], ["--borderless", "1280", "720"]),
            (["nscb", "-p", "gaming", "-W", "2560"], ["-f", "2560", "1080"]),
            (["nscb", "-p", "gaming", "--", "myapp"], ["-f", "1920", "1080"]),
        ],
    )
    def test_main_different_arg_combinations(
        self,
        mock_integration_setup,
        mocker,
        mock_config_file,
        cmd_args,
        expected_flags,
    ):
        config_data = (
            "gaming=-f -W 1920 -H 1080\nstreaming=--borderless -W 1280 -H 720\n"
        )

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch("sys.argv", cmd_args)

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "gamescope" in called_cmd

        for flag in expected_flags:
            assert flag in called_cmd

    def test_main_profile_loading_real_workflow(
        self, mock_integration_setup, mocker, mock_config_file
    ):
        config_data = """
# Complex config with various settings
performance=-f -W 2560 -H 1440 --mangoapp
quality=--borderless -W 1920 -H 1080 --framerate-limit=60
balanced=-W 1920 -H 1080 --fsr-sharpness 8
"""

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch("sys.argv", ["nscb", "-p", "performance", "-W", "3200"])

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "gamescope" in called_cmd
        assert "-f" in called_cmd
        assert "3200" in called_cmd
        assert "--mangoapp" in called_cmd

    def test_main_environment_variable_integration(
        self,
        mock_integration_setup,
        mocker,
        mock_config_file,
        mock_env_commands,
    ):
        config_data = "gaming=-f -W 1920 -H 1080\n"

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mock_env_commands("before_cmd", "after_cmd")
        mocker.patch("sys.argv", ["nscb", "-p", "gaming", "--", "app"])

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "before_cmd" in called_cmd
        assert "after_cmd" in called_cmd
        assert "app" in called_cmd


class TestProfileCombinations:
    """Test profile combinations and merging"""

    def test_profile_complex_combinations(
        self, mock_integration_setup, mocker, mock_config_file
    ):
        config_data = """
performance=-f -W 2560 -H 1440 --mangoapp --framerate-limit=120
quality=--borderless -W 1920 -H 1080 --framerate-limit=60
compatibility=-W 1280 -H 720 --fsr-sharpness 5 --backend sdl2
ultrawide=-f -W 3440 -H 1440
"""

        mock_integration_setup["run_nonblocking"].reset_mock()

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch(
            "sys.argv", ["nscb", "--profiles=performance,quality", "--", "game"]
        )

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        assert mock_integration_setup["run_nonblocking"].call_count > 0

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "--borderless" in called_cmd
        assert not cmd_has_flag(called_cmd, "-f")
        assert "--mangoapp" in called_cmd
        assert "1920" in called_cmd
        assert "1080" in called_cmd
        assert "60" in called_cmd
        assert "game" in called_cmd

    def test_profile_override_precedence_real_scenarios(
        self, mock_integration_setup, mocker, mock_config_file
    ):
        config_data = "gaming=-f -W 1920 -H 1080 --mangoapp\n"

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch("sys.argv", ["nscb", "-p", "gaming", "--borderless", "-W", "3200"])

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "--borderless" in called_cmd
        assert "-f" not in called_cmd
        assert "3200" in called_cmd
        assert "1920" not in called_cmd
        assert "--mangoapp" in called_cmd

    def test_profile_error_non_existent(self, mocker, mock_config_file):
        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file("existing=--borderless\n")
        mock_log = mocker.patch("logging.error")
        mocker.patch("sys.argv", ["nscb", "-p", "nonexistent"])

        result = main()
        assert result == 1
        mock_log.assert_called_with("profile nonexistent not found")

    def test_profile_config_format_variations(self):
        import os
        import tempfile

        from nscb import ConfigManager

        config_data = """# Performance profile
performance="-f -W 2560 -H 1440"

# Compatibility profile with mixed quotes
"compatibility"=-W 1280 -H 720

# Empty line above this line

# Profile with no value
empty_profile=
# Another profile
gaming=--borderless -W 1920 -H 1080
"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".conf"
        ) as temp_file:
            temp_file.write(config_data)
            temp_config_path = temp_file.name

        try:
            config = ConfigManager.load_config(Path(temp_config_path))

            assert "performance" in config
            assert config["performance"] == "-f -W 2560 -H 1440"
            assert "gaming" in config
            assert config["gaming"] == "--borderless -W 1920 -H 1080"
            assert "empty_profile" in config
            assert config["empty_profile"] == ""

            compat_key_found = "compatibility" in config or '"compatibility"' in config
            assert compat_key_found

            compat_key = (
                "compatibility" if "compatibility" in config else '"compatibility"'
            )
            assert config[compat_key] == "-W 1280 -H 720"
        finally:
            os.unlink(temp_config_path)

    def test_profile_multiple_interaction_scenarios(
        self, mock_integration_setup, mocker, mock_config_file
    ):
        config_data = """
gaming=-f -W 1920 -H 1080 --mangoapp
streaming=--borderless -W 1280 -H 720
performance=-H 1440 --framerate-limit=120
"""

        mock_integration_setup["run_nonblocking"].reset_mock()

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch(
            "sys.argv",
            ["nscb", "--profiles=gaming,streaming,performance", "--", "game"],
        )

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        assert mock_integration_setup["run_nonblocking"].call_count > 0

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "--borderless" in called_cmd
        assert not cmd_has_flag(called_cmd, "-f")
        assert "1280" in called_cmd
        assert "1440" in called_cmd
        assert "--mangoapp" in called_cmd
        assert "--framerate-limit=120" in called_cmd

    def test_profile_argument_merging_real_workflow(
        self, mock_integration_setup, mocker, mock_config_file
    ):
        config_data = "mixed=-f -W 1920 -H 1080 --mangoapp --fsr-sharpness 5\n"

        mock_integration_setup["run_nonblocking"].reset_mock()

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch(
            "sys.argv",
            ["nscb", "-p", "mixed", "--borderless", "-W", "3840", "-H", "2160"],
        )

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        assert mock_integration_setup["run_nonblocking"].call_count > 0

        called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
        assert "--borderless" in called_cmd
        assert not cmd_has_flag(called_cmd, "-f")
        assert "3840" in called_cmd
        assert "2160" in called_cmd
        assert "--mangoapp" in called_cmd
        assert "5" in called_cmd


class TestExecutionFlow:
    """Test command execution flow"""

    def test_execution_full_command_building(self, mocker):
        from nscb import CommandExecutor

        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "echo start", "NSCB_POST_CMD": "echo end"},
            clear=True,
        )
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()

        parts = [pre_cmd, "gamescope -f -- myapp", post_cmd]
        built_cmd = CommandExecutor.build_command(parts)

        assert "echo start" in built_cmd
        assert "gamescope -f -- myapp" in built_cmd
        assert "echo end" in built_cmd
        assert "start; gamescope" in built_cmd or "start;gamescope" in built_cmd

    def test_execution_environment_command_integration(
        self, mock_integration_setup, mocker
    ):
        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "export VAR=test", "NSCB_POST_CMD": "echo done"},
            clear=True,
        )
        from nscb import CommandExecutor

        pre_cmd, post_cmd = CommandExecutor.get_env_commands()
        command_parts = [pre_cmd, "gamescope test", post_cmd]
        full_cmd = CommandExecutor.build_command(command_parts)

        assert "export VAR=test" in full_cmd
        assert "echo done" in full_cmd
        assert "gamescope test" in full_cmd

    def test_execution_nonblocking_flow(self):
        import inspect

        from nscb import CommandExecutor

        sig = inspect.signature(CommandExecutor.run_nonblocking)
        assert len(sig.parameters) == 1
        assert "cmd" in sig.parameters

    def test_execution_command_execution_variations(self, mocker):
        from nscb import CommandExecutor

        # Test with gamescope not active
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mock_run = mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=0)
        mocker.patch("builtins.print")
        mocker.patch("sys.exit")

        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 0

        # Test with gamescope active
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=True)
        mock_run = mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=0)
        mocker.patch("builtins.print")

        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 0

    def test_execution_error_handling_in_engine(self, mocker):
        from nscb import CommandExecutor

        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=1)
        mocker.patch("builtins.print")

        result = CommandExecutor.execute_gamescope_command(["-f", "--", "testapp"])
        assert result == 1


class TestEnvironmentVariables:
    """Test environment variable handling"""

    @pytest.mark.parametrize(
        "env_vars,expected",
        [
            ({"NSCB_PRE_CMD": "pre", "NSCB_POST_CMD": "post"}, ("pre", "post")),
            (
                {"NSCB_PRECMD": "old_pre", "NSCB_POSTCMD": "old_post"},
                ("old_pre", "old_post"),
            ),
            (
                {
                    "NSCB_PRE_CMD": "new_pre",
                    "NSCB_POST_CMD": "new_post",
                    "NSCB_PRECMD": "old_pre",
                    "NSCB_POSTCMD": "old_post",
                },
                ("new_pre", "new_post"),
            ),
            (
                {"NSCB_PRE_CMD": "new_pre", "NSCB_POSTCMD": "old_post"},
                ("new_pre", "old_post"),
            ),
        ],
    )
    def test_environment_commands_integration(self, mocker, env_vars, expected):
        mocker.patch.dict("os.environ", env_vars, clear=True)
        result = CommandExecutor.get_env_commands()
        assert result == expected

    def test_env_pre_post_command_flow(self, mocker):
        from nscb import CommandExecutor

        mocker.patch.dict(
            "os.environ",
            {"NSCB_PRE_CMD": "echo 'starting'", "NSCB_POST_CMD": "echo 'finished'"},
            clear=True,
        )
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()

        command_parts = [pre_cmd, "gamescope -f -- testapp", post_cmd]
        full_cmd = CommandExecutor.build_command(command_parts)

        assert "echo 'starting'" in full_cmd
        assert "echo 'finished'" in full_cmd
        assert "gamescope -f -- testapp" in full_cmd

    def test_env_variable_fallback_behavior(self, mocker):
        from nscb import CommandExecutor

        test_cases = [
            (
                {"NSCB_PRE_CMD": "new_pre", "NSCB_POST_CMD": "new_post"},
                ("new_pre", "new_post"),
            ),
            (
                {"NSCB_PRECMD": "old_pre", "NSCB_POSTCMD": "old_post"},
                ("old_pre", "old_post"),
            ),
            (
                {
                    "NSCB_PRE_CMD": "new_pre",
                    "NSCB_POST_CMD": "new_post",
                    "NSCB_PRECMD": "old_pre",
                    "NSCB_POSTCMD": "old_post",
                },
                ("new_pre", "new_post"),
            ),
            (
                {"NSCB_PRE_CMD": "new_pre", "NSCB_POSTCMD": "old_post"},
                ("new_pre", "old_post"),
            ),
        ]

        for env_vars, expected in test_cases:
            mocker.patch.dict("os.environ", env_vars, clear=True)
            result = CommandExecutor.get_env_commands()
            assert result == expected

    def test_env_command_chaining_scenarios(self):
        from nscb import CommandExecutor

        test_cases = [
            (["cmd1", "cmd2"], "cmd1; cmd2"),
            (["cmd1", "", "cmd2", ""], "cmd1; cmd2"),
            (["single"], "single"),
            (["", "", ""], ""),
            (["export X=1", "gamescope -f", "app"], "export X=1; gamescope -f; app"),
        ]

        for parts, expected_contains in test_cases:
            result = CommandExecutor.build_command(parts)
            if expected_contains:
                for part in expected_contains.split("; "):
                    if part.strip():
                        assert part.strip() in result

    def test_env_empty_variable_handling(self, mocker):
        from nscb import CommandExecutor

        mocker.patch.dict(
            "os.environ", {"NSCB_PRE_CMD": "", "NSCB_POST_CMD": ""}, clear=True
        )
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()
        assert pre_cmd == ""
        assert post_cmd == ""

        full_cmd = CommandExecutor.build_command([pre_cmd, "gamescope test", post_cmd])
        assert "gamescope test" in full_cmd

    def test_env_mixed_scenario_execution(
        self, mock_integration_setup, mocker, mock_config_file, mock_env_commands
    ):
        config_data = "test_profile=-f -W 1920 -H 1080\n"

        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mock_config_file(config_data)
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mock_env_commands("before", "after")
        mocker.patch("sys.argv", ["nscb", "-p", "test_profile", "--", "myapp"])

        result = main()
        assert result == 0  # main now returns an exit code instead of calling sys.exit

        if mock_integration_setup["run_nonblocking"].call_args:
            called_cmd = mock_integration_setup["run_nonblocking"].call_args[0][0]
            assert "before" in called_cmd
            assert "gamescope" in called_cmd
            assert "-f" in called_cmd
            assert "myapp" in called_cmd
            assert "after" in called_cmd


class TestGamescopeDetection:
    """Test gamescope detection functionality"""

    def test_gamescope_detection_and_execution_modes(self, mocker):
        mocker.patch.dict(
            "os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True
        )
        assert SystemDetector.is_gamescope_active() is True
