import sys
from pathlib import Path

import pytest
from conftest import SystemExitCalled

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
from nscb import (  # noqa: E402
    ArgumentProcessor,
    CommandExecutor,
    ConfigManager,
    ProfileManager,
    SystemDetector,
)


class TestParseProfileArgs:
    """Test profile argument parsing variations"""

    @pytest.mark.parametrize(
        "input_args,expected",
        [
            (["-p", "gaming"], (["gaming"], [])),
            (["--profile=streaming"], (["streaming"], [])),
            (["-p", "a", "--profile=b", "cmd"], (["a", "b"], ["cmd"])),
            (["--profiles=gaming,streaming"], (["gaming", "streaming"], [])),
            (["--profiles="], ([], [])),
        ],
    )
    def test_parse_profile_args_variations(self, input_args, expected):
        assert ProfileManager.parse_profile_args(input_args) == expected

    @pytest.mark.parametrize(
        "input_args,error_msg",
        [
            (["-p"], r"-p requires value"),
            (["--profile"], r"--profile requires value"),
        ],
    )
    def test_parse_profile_args_errors(self, input_args, error_msg):
        with pytest.raises(ValueError, match=error_msg):
            ProfileManager.parse_profile_args(input_args)


class TestSeparateFlagsAndPositionals:
    """Test flag and positional argument separation"""

    @pytest.mark.parametrize(
        "input_args,expected_flags,expected_positionals",
        [
            (["-W", "1920", "--nested"], [("-W", "1920"), ("--nested", None)], []),
            (
                ["-f", "app.exe", "--borderless"],
                [("-f", "app.exe"), ("--borderless", None)],
                [],
            ),
            (["-W", "1920", "-H", "1080"], [("-W", "1920"), ("-H", "1080")], []),
            (["app.exe", "arg1"], [], ["app.exe", "arg1"]),
            ([], [], []),
            (
                [
                    "-W",
                    "1920",
                    "--output-width",
                    "2560",
                    "-f",
                    "--mangoapp",
                    "game.exe",
                ],
                [
                    ("-W", "1920"),
                    ("--output-width", "2560"),
                    ("-f", None),
                    ("--mangoapp", "game.exe"),
                ],
                [],
            ),
            (
                ["-f", "--borderless", "--mangoapp"],
                [("-f", None), ("--borderless", None), ("--mangoapp", None)],
                [],
            ),
            (
                ["-W", "1920", "game.exe", "--fullscreen", "-H", "1080", "input.txt"],
                [("-W", "1920"), ("--fullscreen", None), ("-H", "1080")],
                ["game.exe", "input.txt"],
            ),
            (
                ["game.exe", "-W", "1920", "--", "-f", "extra_arg"],
                [("-W", "1920"), ("--", None), ("-f", "extra_arg")],
                ["game.exe"],
            ),
            (
                [
                    "-f",
                    "-W",
                    "1920",
                    "--nested-width",
                    "1280",
                    "game.exe",
                    "save1",
                    "--borderless",
                ],
                [
                    ("-f", None),
                    ("-W", "1920"),
                    ("--nested-width", "1280"),
                    ("--borderless", None),
                ],
                ["game.exe", "save1"],
            ),
        ],
    )
    def test_separate_flags_and_positionals_variations(
        self, input_args, expected_flags, expected_positionals
    ):
        flags, positionals = ArgumentProcessor.separate_flags_and_positionals(
            input_args
        )
        assert flags == expected_flags
        assert positionals == expected_positionals


class TestMergeArguments:
    """Test argument merging with conflict resolution"""

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
    def test_merge_arguments_variations(
        self, profile_args, override_args, expected_result
    ):
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
        # Profile has -W 1920, override doesn't touch width (should be preserved)
        result = ProfileManager.merge_arguments(["-f", "-W", "1920"], ["--borderless"])
        assert "-f" not in result
        assert "--borderless" in result
        assert "-W" in result
        assert "1920" in result

    def test_merge_arguments_width_override(self):
        # Profile has -W 1920, override explicitly sets different width
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
        # Using short and long form of same flag
        result = ProfileManager.merge_arguments(["-f"], ["--fullscreen"])
        assert ("-f" in result) ^ ("--fullscreen" in result)  # Exactly one

        # Test with width
        result = ProfileManager.merge_arguments(
            ["-W", "1920"], ["--output-width", "2560"]
        )
        assert "--output-width" in result or "-W" in result
        assert "2560" in result
        assert "1920" not in result


class TestMergeMultipleProfiles:
    """Test merging multiple profile argument lists"""

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


class TestFindExecutable:
    """Test executable discovery functionality"""

    def test_find_executable_true(self, mocker):
        mocker.patch.dict("os.environ", {"PATH": "/usr/bin:/bin"})
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch.object(Path, "is_dir", return_value=True)
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("os.access", return_value=True)

        assert SystemDetector.find_executable("gamescope") is True

    def test_find_executable_false(self, mocker):
        mocker.patch.dict("os.environ", {"PATH": ""}, clear=True)
        assert SystemDetector.find_executable("gamescope") is False

    def test_find_executable_permission_issues(self, mocker):
        mocker.patch.dict("os.environ", {"PATH": "/usr/bin"})
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch.object(Path, "is_dir", return_value=True)
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("os.access", return_value=False)
        assert SystemDetector.find_executable("gamescope") is False

    def test_find_executable_empty_path(self, mocker):
        mocker.patch("os.environ.get", return_value="")
        assert SystemDetector.find_executable("any_executable") is False

    def test_find_executable_path_scenarios(self, mocker):
        import shutil

        python_path = shutil.which("python")
        if python_path:
            mocker.patch.dict("os.environ", {"PATH": str(Path(python_path).parent)})
            mocker.patch.object(Path, "exists", return_value=True)
            mocker.patch.object(Path, "is_dir", return_value=True)
            mocker.patch.object(Path, "is_file", return_value=True)
            mocker.patch("os.access", return_value=True)
            result = SystemDetector.find_executable("python")
            assert result is True


class TestFindConfigFile:
    """Test config file discovery functionality"""

    def test_find_config_file_xdg_exists(self, temp_config_file, monkeypatch):
        with open(temp_config_file, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_file.parent))
        monkeypatch.delenv("HOME", raising=False)

        result = ConfigManager.find_config_file()
        assert result == temp_config_file

    def test_find_config_file_xdg_missing_fallback(self, temp_config_file, monkeypatch):
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent")
        monkeypatch.setenv("HOME", str(home_config_dir))

        result = ConfigManager.find_config_file()
        assert result == config_path

    def test_find_config_file_home_only(self, temp_config_file, monkeypatch):
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_config_dir))

        result = ConfigManager.find_config_file()
        assert result == config_path

    def test_find_config_file_no_config(self, monkeypatch):
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)

        result = ConfigManager.find_config_file()
        assert result is None

    def test_find_config_file_permission_error(self, mocker, monkeypatch):
        mocker.patch.object(Path, "exists", return_value=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)

        result = ConfigManager.find_config_file()
        assert result is None


class TestLoadConfig:
    """Test config file loading functionality"""

    @pytest.mark.parametrize(
        "content,expected",
        [
            (
                "gaming=-f -W 1920 -H 1080\nstreaming=--borderless -w 1280 -h 720\n",
                {
                    "gaming": "-f -W 1920 -H 1080",
                    "streaming": "--borderless -w 1280 -h 720",
                },
            ),
            (
                "gaming=\"-f -W 1920 -H 1080\"\nstreaming='--borderless -w 1280 -h 720'\n",
                {
                    "gaming": "-f -W 1920 -H 1080",
                    "streaming": "--borderless -w 1280 -h 720",
                },
            ),
            (
                "# This is a comment\n\ngaming=-f -W 1920 -H 1080\n# Another comment\n\nstreaming=--borderless\n",
                {"gaming": "-f -W 1920 -H 1080", "streaming": "--borderless"},
            ),
            (
                'gaming="-f -W 1920 -H 1080"\nspecial="test \'nested quotes\' here"\n',
                {
                    "gaming": "-f -W 1920 -H 1080",
                    "special": "test 'nested quotes' here",
                },
            ),
            ("", {}),
        ],
    )
    def test_load_config_variations(self, temp_config_with_content, content, expected):
        config_path = temp_config_with_content(content)
        result = ConfigManager.load_config(config_path)
        assert result == expected

    def test_load_config_invalid_formats(self, temp_config_file):
        with open(temp_config_file, "w") as f:
            f.write("invalid_line_without_equals_sign\n")

        # The function should handle this gracefully, not raise ValueError
        result = ConfigManager.load_config(temp_config_file)
        # Since there's no '=' in the line, the result would be an empty dict
        assert result == {}

        temp_config_file2 = temp_config_file.parent / "nscb2.conf"
        with open(temp_config_file2, "w") as f:
            f.write("multiple_equals=value=another_value\n")

        result = ConfigManager.load_config(temp_config_file2)
        expected = {"multiple_equals": "value=another_value"}
        assert result == expected

    def test_load_config_file_reading_errors(self):
        non_existent = Path("/non/existent/path/nscb.conf")
        with pytest.raises(FileNotFoundError):
            ConfigManager.load_config(non_existent)

    def test_load_config_malformed_config(self, temp_config_with_content):
        content = "gaming=-f -W 1920 -H 1080\n=\n=empty_key\nvalid=value\n"
        config_path = temp_config_with_content(content)
        result = ConfigManager.load_config(config_path)
        assert isinstance(result, dict)


class TestSplitAtSeparator:
    """Test argument splitting at separator"""

    @pytest.mark.parametrize(
        "input_args,expected_before,expected_after",
        [
            (["-f", "--", "app.exe"], ["-f"], ["--", "app.exe"]),
            (["-f", "--", "app1", "--", "app2"], ["-f"], ["--", "app1", "--", "app2"]),
            (["-f", "-W", "1920"], ["-f", "-W", "1920"], []),
            (["--", "app.exe"], [], ["--", "app.exe"]),
        ],
    )
    def test_split_at_separator_variations(
        self, input_args, expected_before, expected_after
    ):
        result_before, result_after = ArgumentProcessor.split_at_separator(input_args)
        assert result_before == expected_before
        assert result_after == expected_after


class TestIsGamescopeActive:
    """Test gamescope detection functionality"""

    def test_is_gamescope_active_xdg_method(self, mocker):
        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"})
        from nscb import SystemDetector

        assert SystemDetector.is_gamescope_active() is True

    def test_is_gamescope_active_ps_method(self, mocker):
        mocker.patch(
            "subprocess.check_output",
            return_value="1234 ?    Sl     0:00 gamescope -f -W 1920 -H 1080",
        )
        from nscb import SystemDetector

        assert SystemDetector.is_gamescope_active() is True

        mocker.patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 Xorg"
        )
        assert SystemDetector.is_gamescope_active() is False

    def test_is_gamescope_active_error_conditions(self, mocker):
        import subprocess

        mocker.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "ps"),
        )
        from nscb import SystemDetector

        assert SystemDetector.is_gamescope_active() is False

    def test_is_gamescope_active_both_methods(self, mocker):
        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"})
        mock_ps = mocker.patch("subprocess.check_output")
        from nscb import SystemDetector

        result = SystemDetector.is_gamescope_active()
        assert result is True
        mock_ps.assert_not_called()

        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "GNOME"})
        mocker.patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 gamescope"
        )
        result = SystemDetector.is_gamescope_active()
        assert result is True


class TestGetEnvCommands:
    """Test environment command retrieval"""

    @pytest.mark.parametrize(
        "env_vars,expected",
        [
            (
                {"NSCB_PRE_CMD": "before_cmd", "NSCB_POST_CMD": "after_cmd"},
                ("before_cmd", "after_cmd"),
            ),
            (
                {"NSCB_PRECMD": "legacy_before", "NSCB_POSTCMD": "legacy_after"},
                ("legacy_before", "legacy_after"),
            ),
            (
                {
                    "NSCB_PRE_CMD": "new_before",
                    "NSCB_POST_CMD": "new_after",
                    "NSCB_PRECMD": "legacy_before",
                    "NSCB_POSTCMD": "legacy_after",
                },
                ("new_before", "new_after"),
            ),
            (
                {"NSCB_PRE_CMD": "new_before", "NSCB_POSTCMD": "legacy_after"},
                ("new_before", "legacy_after"),
            ),
            ({}, ("", "")),
            ({"NSCB_PRE_CMD": "", "NSCB_POST_CMD": ""}, ("", "")),
        ],
    )
    def test_get_env_commands_variations(self, monkeypatch, env_vars, expected):
        # Clear all env vars first
        for var in ["NSCB_PRE_CMD", "NSCB_POST_CMD", "NSCB_PRECMD", "NSCB_POSTCMD"]:
            monkeypatch.delenv(var, raising=False)

        # Set the test vars
        for var, value in env_vars.items():
            monkeypatch.setenv(var, value)

        from nscb import CommandExecutor

        pre, post = CommandExecutor.get_env_commands()
        assert pre == expected[0]
        assert post == expected[1]


class TestBuildCommand:
    """Test command building functionality"""

    @pytest.mark.parametrize(
        "parts,expected",
        [
            (["pre_cmd", "app_cmd", "post_cmd"], "pre_cmd; app_cmd; post_cmd"),
            (["single_cmd"], "single_cmd"),
            (["pre_cmd", "", "post_cmd"], "pre_cmd; post_cmd"),
            (["", "cmd1", "", "", "cmd2", ""], "cmd1; cmd2"),
            (["", "", ""], ""),
            ([], ""),
        ],
    )
    def test_build_command_variations(self, parts, expected):
        from nscb import CommandExecutor

        result = CommandExecutor.build_command(parts)
        assert result == expected


class TestRunNonblocking:
    """Test non-blocking command execution"""

    def test_run_nonblocking_signature(self):
        import inspect

        from nscb import CommandExecutor

        sig = inspect.signature(CommandExecutor.run_nonblocking)
        assert len(sig.parameters) == 1
        assert "cmd" in sig.parameters

    def test_run_nonblocking_with_mocked_subprocess(self, mock_subprocess):
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from nscb import CommandExecutor

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = CommandExecutor.run_nonblocking("echo test")

        assert result == 0


class TestMainFunction:
    """Test main function error handling"""

    def test_main_keyerror_handling(
        self, mocker, mock_system_exit, temp_config_with_content
    ):
        config_content = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_content)

        mocker.patch("sys.argv", ["nscb.py", "-p", "gaming", "--", "game.exe"])
        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mocker.patch("nscb.ConfigManager.find_config_file", return_value=config_path)

        original_shlex_split = mocker.patch("shlex.split")

        def custom_split_side_effect(s):
            if s == "-f -W 1920 -H 1080":
                raise KeyError("Test KeyError")
            return ["-f", "-W", "1920", "-H", "1080"]

        original_shlex_split.side_effect = custom_split_side_effect

        from nscb import main

        result = main()
        assert result == 1  # main now returns an exit code instead of calling sys.exit

    def test_main_no_config_file_found(self, mocker, mock_system_exit):
        mocker.patch("sys.argv", ["nscb.py", "-p", "gaming", "--", "game.exe"])
        mocker.patch("nscb.SystemDetector.find_executable", return_value=True)
        mocker.patch("nscb.ConfigManager.find_config_file", return_value=None)

        from nscb import main

        result = main()
        assert result == 1  # main now returns an exit code instead of calling sys.exit


class TestExecuteGamescopeCommand:
    """Test gamescope command execution"""

    def test_execute_gamescope_command_normal_execution(self, mocker):
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch(
            "nscb.CommandExecutor.build_command",
            side_effect=lambda x: " ".join(filter(None, x)),
        )
        mocker.patch("builtins.print")
        mock_run = mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=0)

        from nscb import CommandExecutor

        final_args = ["-f", "-W", "1920", "--", "mygame.exe"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gamescope" in call_args
        assert "-f" in call_args
        assert "1920" in call_args
        assert "mygame.exe" in call_args
        assert result == 0  # Should return exit code

    def test_execute_gamescope_command_under_gamescope_with_separator(self, mocker):
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=True)
        mocker.patch(
            "nscb.CommandExecutor.build_command",
            side_effect=lambda x: " ".join(filter(None, x)),
        )
        mock_run = mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=0)

        from nscb import CommandExecutor

        final_args = ["-f", "-W", "1920", "--", "mygame.exe"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gamescope" not in call_args
        assert "mygame.exe" in call_args
        assert "-f" not in call_args
        assert result == 0  # Should return exit code

    def test_execute_gamescope_command_under_gamescope_no_separator(self, mocker):
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=True)
        _mock_run = mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=0)

        from nscb import CommandExecutor

        final_args = ["-f", "-W", "1920"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        # When under gamescope with no separator and no pre/post cmd, should return early
        assert result == 0  # Should return exit code

    def test_execute_gamescope_command_with_pre_post_commands(self, mocker):
        mocker.patch(
            "nscb.CommandExecutor.get_env_commands",
            return_value=("echo pre", "echo post"),
        )
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mocker.patch(
            "nscb.CommandExecutor.build_command",
            side_effect=lambda x: "; ".join(filter(None, x)),
        )
        mock_run = mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=0)

        from nscb import CommandExecutor

        final_args = ["-f", "--", "mygame.exe"]
        result = CommandExecutor.execute_gamescope_command(final_args)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "echo pre" in call_args
        assert "echo post" in call_args
        assert "gamescope" in call_args
        assert "mygame.exe" in call_args
        assert result == 0  # Should return exit code
