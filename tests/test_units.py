import os
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
        # Should return a ConfigResult which has dict-like behavior for profiles
        assert hasattr(result, "profiles") and isinstance(result.profiles, dict)

    @pytest.mark.parametrize(
        "content,expected_profiles,expected_exports",
        [
            # Basic export functionality
            (
                "export SOME_VAR=value\ngaming=-f",
                {"gaming": "-f"},
                {"SOME_VAR": "value"},
            ),
            # Multiple exports
            (
                "export VAR1=value1\nexport VAR2=value2\ngaming=-f",
                {"gaming": "-f"},
                {"VAR1": "value1", "VAR2": "value2"},
            ),
            # Export with quotes
            (
                'export QUOTED_VAR="quoted value here"\nstreaming=--borderless',
                {"streaming": "--borderless"},
                {"QUOTED_VAR": "quoted value here"},
            ),
            # Mixed profiles and exports
            (
                "gaming=-f -W 1920\nexport DISPLAY=:0\nstreaming=--borderless\nexport WAYLAND_DISPLAY=wayland-0",
                {"gaming": "-f -W 1920", "streaming": "--borderless"},
                {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"},
            ),
            # Export only config (no profiles)
            (
                "export ONLY_VAR=value\nexport ANOTHER_VAR=test",
                {},
                {"ONLY_VAR": "value", "ANOTHER_VAR": "test"},
            ),
            # Profile only config (no exports)
            (
                "gaming=-f\nstreaming=--borderless",
                {"gaming": "-f", "streaming": "--borderless"},
                {},
            ),
            # Empty config with exports
            ("export EMPTY_VAR=", {}, {"EMPTY_VAR": ""}),
        ],
    )
    def test_load_config_with_exports(
        self, temp_config_with_content, content, expected_profiles, expected_exports
    ):
        """Test loading config with export statements."""
        config_path = temp_config_with_content(content)
        result = ConfigManager.load_config(config_path)
        assert result.profiles == expected_profiles
        assert result.exports == expected_exports


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

    def test_build_inactive_gamescope_command_with_ld_preload(self, mocker):
        # Test that LD_PRELOAD is properly handled when gamescope is not active
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Test with LD_PRELOAD environment variable
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"
        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_inactive_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # Check that the command includes the proper LD_PRELOAD handling
            assert "env -u LD_PRELOAD gamescope" in result
            assert "LD_PRELOAD=" in result  # Should contain LD_PRELOAD assignment
            assert "mygame.exe" in result
            assert "arg1" in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            else:
                os.environ.pop("LD_PRELOAD", None)

    def test_build_inactive_gamescope_command_without_ld_preload(self, mocker):
        # Test when there's no LD_PRELOAD environment variable
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Test without LD_PRELOAD environment variable
        original_ld_preload = os.environ.get("LD_PRELOAD")
        if "LD_PRELOAD" in os.environ:
            del os.environ["LD_PRELOAD"]
        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_inactive_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # Should NOT use env -u LD_PRELOAD when LD_PRELOAD is not originally set
            assert "env -u LD_PRELOAD gamescope" not in result
            assert "gamescope -f --" in result  # Basic check for the expected format
            assert "mygame.exe" in result
            assert "arg1" in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload

    def test_build_inactive_gamescope_command_with_empty_ld_preload(self, mocker):
        # Test when LD_PRELOAD is set to an empty string
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Test with LD_PRELOAD environment variable set to empty string
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = ""
        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_inactive_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # Should NOT use env -u LD_PRELOAD when LD_PRELOAD is empty
            assert "env -u LD_PRELOAD gamescope" not in result
            assert "gamescope -f --" in result  # Basic check for the expected format
            assert "mygame.exe" in result
            assert "arg1" in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            else:
                if "LD_PRELOAD" in os.environ:
                    del os.environ["LD_PRELOAD"]

    def test_build_active_gamescope_command_with_ld_preload(self, mocker):
        # Test LD_PRELOAD handling when gamescope is already active
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Test with LD_PRELOAD environment variable
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"
        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_active_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # When already in gamescope, should preserve LD_PRELOAD for the app
            assert "LD_PRELOAD=" in result  # Should contain LD_PRELOAD assignment
            assert "mygame.exe" in result
            assert "arg1" in result
            assert "gamescope" not in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            else:
                os.environ.pop("LD_PRELOAD", None)

    def test_build_active_gamescope_command_with_empty_ld_preload(self, mocker):
        # Test LD_PRELOAD handling when gamescope is already active and LD_PRELOAD is empty
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Test with LD_PRELOAD environment variable set to empty string
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = ""
        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_active_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # When LD_PRELOAD is empty, should not wrap with LD_PRELOAD
            assert (
                "LD_PRELOAD=" not in result
            )  # Should NOT contain LD_PRELOAD assignment
            assert "mygame.exe" in result
            assert "arg1" in result
            assert "gamescope" not in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            else:
                if "LD_PRELOAD" in os.environ:
                    del os.environ["LD_PRELOAD"]

    def test_build_active_gamescope_command_without_ld_preload(self, mocker):
        # Test when gamescope is active and no LD_PRELOAD variable
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        original_ld_preload = os.environ.get("LD_PRELOAD")
        if "LD_PRELOAD" in os.environ:
            del os.environ["LD_PRELOAD"]
        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_active_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # When no LD_PRELOAD, should just execute the app without env wrapper
            assert "env LD_PRELOAD" not in result
            assert "mygame.exe" in result
            assert "arg1" in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload

    def test_execute_gamescope_command_with_ld_preload(self, mocker):
        # Test full execution flow with LD_PRELOAD
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        mocker.patch("nscb.SystemDetector.is_gamescope_active", return_value=False)
        mock_run = mocker.patch("nscb.CommandExecutor.run_nonblocking", return_value=0)

        from nscb import CommandExecutor

        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"
        try:
            final_args = ["-f", "--", "mygame.exe"]
            result = CommandExecutor.execute_gamescope_command(final_args)

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "env -u LD_PRELOAD gamescope" in call_args
            assert "LD_PRELOAD=" in call_args  # Should contain LD_PRELOAD assignment
            assert "mygame.exe" in call_args
            assert result == 0
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            else:
                os.environ.pop("LD_PRELOAD", None)

    def test_should_disable_ld_preload_wrap(self, mocker):
        from nscb import EnvironmentHelper

        # Test truthy values
        truthy_values = ["1", "true", "yes", "on", "TRUE", "YES", "ON"]
        for value in truthy_values:
            mocker.patch.dict("os.environ", {"NSCB_DISABLE_LD_PRELOAD_WRAP": value})
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

        # Test falsy values
        falsy_values = ["0", "false", "no", "off", "other_value", ""]
        for value in falsy_values:
            mocker.patch.dict("os.environ", {"NSCB_DISABLE_LD_PRELOAD_WRAP": value})
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is False

        # Test when variable is not set
        mocker.patch.dict("os.environ", {}, clear=True)
        assert EnvironmentHelper.should_disable_ld_preload_wrap() is False

    def test_should_disable_ld_preload_wrap_with_faugus_log(self, mocker):
        from nscb import EnvironmentHelper

        # Save original environment
        original_faugus_log = os.environ.get("FAUGUS_LOG")
        original_disable_flag = os.environ.get("NSCB_DISABLE_LD_PRELOAD_WRAP")

        try:
            # Test that LD_PRELOAD wrapping is disabled when FAUGUS_LOG is set
            os.environ["FAUGUS_LOG"] = "/path/to/log"
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

            # Test that LD_PRELOAD wrapping is still disabled with a different FAUGUS_LOG value
            os.environ["FAUGUS_LOG"] = "some_value"
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

            # Clear FAUGUS_LOG and test with other variables
            if "FAUGUS_LOG" in os.environ:
                del os.environ["FAUGUS_LOG"]
            os.environ["OTHER_VAR"] = "value"
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is False

            # Test that FAUGUS_LOG takes precedence over NSCB_DISABLE_LD_PRELOAD_WRAP being falsy
            os.environ["FAUGUS_LOG"] = "/path/to/log"
            os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = "0"
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

            # Test with FAUGUS_LOG present but NSCB_DISABLE_LD_PRELOAD_WRAP as truthy (both should disable)
            os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = "1"
            assert EnvironmentHelper.should_disable_ld_preload_wrap() is True

        finally:
            # Restore original environment
            if original_faugus_log is not None:
                os.environ["FAUGUS_LOG"] = original_faugus_log
            elif "FAUGUS_LOG" in os.environ:
                del os.environ["FAUGUS_LOG"]

            if original_disable_flag is not None:
                os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = original_disable_flag
            elif "NSCB_DISABLE_LD_PRELOAD_WRAP" in os.environ:
                del os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"]

    def test_build_inactive_gamescope_command_with_disabled_ld_preload_wrap(
        self, mocker
    ):
        # Test that LD_PRELOAD wrapping is disabled when NSCB_DISABLE_LD_PRELOAD_WRAP is set
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Set up environment with both LD_PRELOAD and the disable flag
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"
        original_disable_flag = os.environ.get("NSCB_DISABLE_LD_PRELOAD_WRAP")
        os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = "1"

        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_inactive_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # When LD_PRELOAD wrapping is disabled, should NOT use env -u LD_PRELOAD
            assert "env -u LD_PRELOAD gamescope" not in result
            assert "gamescope -f --" in result  # Basic check for the expected format
            assert "mygame.exe" in result
            assert "arg1" in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            elif "LD_PRELOAD" in os.environ:
                del os.environ["LD_PRELOAD"]

            # Restore original disable flag
            if original_disable_flag is not None:
                os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = original_disable_flag
            elif "NSCB_DISABLE_LD_PRELOAD_WRAP" in os.environ:
                del os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"]

    def test_build_inactive_gamescope_command_with_enabled_ld_preload_wrap_different_values(
        self, mocker
    ):
        # Test that LD_PRELOAD wrapping works normally when NSCB_DISABLE_LD_PRELOAD_WRAP is set to falsy values
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Set up environment with LD_PRELOAD
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"

        falsy_values = ["0", "false", "no", "off", "other_value", ""]
        for value in falsy_values:
            # Set the disable flag to a falsy value
            os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = value
            try:
                args = ["-f", "--", "mygame.exe", "arg1"]
                pre_cmd, post_cmd = "", ""

                result = CommandExecutor._build_inactive_gamescope_command(
                    args, pre_cmd, post_cmd
                )

                # When LD_PRELOAD wrapping is not disabled (falsy value), should use env -u LD_PRELOAD
                assert "env -u LD_PRELOAD gamescope" in result
                assert (
                    "LD_PRELOAD=" in result
                )  # Should contain LD_PRELOAD assignment for app
                assert "mygame.exe" in result
                assert "arg1" in result
            finally:
                # Only remove the disable flag we just set, don't remove LD_PRELOAD
                if "NSCB_DISABLE_LD_PRELOAD_WRAP" in os.environ:
                    del os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"]

        # Restore original LD_PRELOAD value at the end if needed
        if original_ld_preload is not None:
            os.environ["LD_PRELOAD"] = original_ld_preload
        elif "LD_PRELOAD" in os.environ:
            del os.environ["LD_PRELOAD"]

    def test_build_inactive_gamescope_command_with_faugus_log(self, mocker):
        # Test that LD_PRELOAD wrapping is disabled when FAUGUS_LOG is set
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Set up environment with LD_PRELOAD and FAUGUS_LOG
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"
        original_faugus_log = os.environ.get("FAUGUS_LOG")
        os.environ["FAUGUS_LOG"] = "/path/to/log"

        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_inactive_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # When LD_PRELOAD wrapping is disabled via FAUGUS_LOG, should NOT use env -u LD_PRELOAD
            assert "env -u LD_PRELOAD gamescope" not in result
            assert "gamescope -f --" in result  # Basic check for the expected format
            assert "mygame.exe" in result
            assert "arg1" in result
            # Should not contain LD_PRELOAD assignment for the app since wrapping is disabled
            assert "LD_PRELOAD=" not in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            elif "LD_PRELOAD" in os.environ:
                del os.environ["LD_PRELOAD"]

            # Restore original FAUGUS_LOG value
            if original_faugus_log is not None:
                os.environ["FAUGUS_LOG"] = original_faugus_log
            elif "FAUGUS_LOG" in os.environ:
                del os.environ["FAUGUS_LOG"]

    def test_build_active_gamescope_command_with_disabled_ld_preload_wrap(self, mocker):
        # Test that LD_PRELOAD wrapping is disabled when NSCB_DISABLE_LD_PRELOAD_WRAP is set in active mode
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Set up environment with both LD_PRELOAD and the disable flag
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"
        original_disable_flag = os.environ.get("NSCB_DISABLE_LD_PRELOAD_WRAP")
        os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = "1"

        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_active_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # When LD_PRELOAD wrapping is disabled and gamescope is active, should NOT wrap with LD_PRELOAD
            assert (
                "LD_PRELOAD=" not in result
            )  # Should NOT contain LD_PRELOAD assignment
            assert "mygame.exe" in result
            assert "arg1" in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            elif "LD_PRELOAD" in os.environ:
                del os.environ["LD_PRELOAD"]

            # Restore original disable flag
            if original_disable_flag is not None:
                os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"] = original_disable_flag
            elif "NSCB_DISABLE_LD_PRELOAD_WRAP" in os.environ:
                del os.environ["NSCB_DISABLE_LD_PRELOAD_WRAP"]

    def test_build_active_gamescope_command_with_faugus_log(self, mocker):
        # Test that LD_PRELOAD wrapping is disabled when FAUGUS_LOG is set in active mode
        mocker.patch("nscb.CommandExecutor.get_env_commands", return_value=("", ""))
        from nscb import CommandExecutor

        # Set up environment with both LD_PRELOAD and FAUGUS_LOG
        original_ld_preload = os.environ.get("LD_PRELOAD")
        os.environ["LD_PRELOAD"] = "/path/to/library.so"
        original_faugus_log = os.environ.get("FAUGUS_LOG")
        os.environ["FAUGUS_LOG"] = "/path/to/log"

        try:
            args = ["-f", "--", "mygame.exe", "arg1"]
            pre_cmd, post_cmd = "", ""

            result = CommandExecutor._build_active_gamescope_command(
                args, pre_cmd, post_cmd
            )

            # When LD_PRELOAD wrapping is disabled via FAUGUS_LOG and gamescope is active,
            # should NOT wrap with LD_PRELOAD
            assert (
                "LD_PRELOAD=" not in result
            )  # Should NOT contain LD_PRELOAD assignment
            assert "mygame.exe" in result
            assert "arg1" in result
        finally:
            # Restore original LD_PRELOAD value
            if original_ld_preload is not None:
                os.environ["LD_PRELOAD"] = original_ld_preload
            elif "LD_PRELOAD" in os.environ:
                del os.environ["LD_PRELOAD"]

            # Restore original FAUGUS_LOG value
            if original_faugus_log is not None:
                os.environ["FAUGUS_LOG"] = original_faugus_log
            elif "FAUGUS_LOG" in os.environ:
                del os.environ["FAUGUS_LOG"]
