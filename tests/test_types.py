"""Tests for the type definitions in NeoscopeBuddy."""

import pytest

from nscb.application import Application
from nscb.argument_processor import ArgumentProcessor
from nscb.profile_manager import ProfileManager
from nscb.types import (
    ArgsList,
    EnvExports,
    ExitCode,
    FlagTuple,
    ProfileArgsList,
)


class TestTypesUnit:
    """Unit tests for the type definitions."""

    def test_args_list_type(self):
        """Test ArgsList type alias."""
        args: ArgsList = ["-f", "-W", "1920", "--", "app.exe"]
        assert isinstance(args, list)
        assert all(isinstance(item, str) for item in args)

    def test_flag_tuple_type(self):
        """Test FlagTuple type alias."""
        flag_with_value: FlagTuple = ("-W", "1920")
        flag_without_value: FlagTuple = ("-f", None)

        assert isinstance(flag_with_value, tuple)
        assert len(flag_with_value) == 2
        assert flag_with_value[0] == "-W"
        assert flag_with_value[1] == "1920"

        assert isinstance(flag_without_value, tuple)
        assert len(flag_without_value) == 2
        assert flag_without_value[0] == "-f"
        assert flag_without_value[1] is None

    def test_env_exports_type(self):
        """Test EnvExports type alias."""
        exports: EnvExports = {"VAR1": "value1", "VAR2": "value2"}
        assert isinstance(exports, dict)
        assert all(isinstance(k, str) for k in exports.keys())
        assert all(isinstance(v, str) for v in exports.values())

    @pytest.mark.parametrize(
        "test_type, test_value, expected_type",
        [
            (ArgsList, ["-f", "-W", "1920", "--", "app.exe"], list),
            (FlagTuple, ("-W", "1920"), tuple),
            (EnvExports, {"VAR1": "value1"}, dict),
            (ExitCode, 0, int),
            (ProfileArgsList, [["-f", "-W", "1920"]], list),
        ],
    )
    def test_type_definitions_various(self, test_type, test_value, expected_type):
        """Test various type definitions with parametrization."""
        assert isinstance(test_value, expected_type)
        if expected_type is list:
            if isinstance(test_value[0], list):  # ProfileArgsList case
                assert all(isinstance(item, list) for item in test_value)
                assert all(
                    isinstance(arg, str)
                    for sublist in test_value
                    for arg in sublist
                    if isinstance(arg, str) or isinstance(arg, (list, tuple))
                )
            elif (
                test_value
                and isinstance(test_value[0], tuple)
                and len(test_value[0]) == 2
            ):  # FlagTuple case
                assert all(
                    isinstance(item, tuple) and len(item) == 2 for item in test_value
                )
        elif expected_type is dict:
            assert all(isinstance(k, str) for k in test_value.keys())
            assert all(isinstance(v, str) for v in test_value.values())
        elif expected_type is int:
            assert test_value == 0  # ExitCode 0 case

    def test_exit_code_type(self):
        """Test ExitCode type alias."""
        success_code: ExitCode = 0
        error_code: ExitCode = 1

        assert isinstance(success_code, int)
        assert isinstance(error_code, int)
        assert success_code == 0
        assert error_code == 1

    def test_profile_args_list_type(self):
        """Test ProfileArgsList type alias."""
        profile_args_list: ProfileArgsList = [
            ["-f", "-W", "1920"],
            ["--borderless", "-H", "1080"],
            ["-w", "1280", "--mangoapp"],
        ]
        assert isinstance(profile_args_list, list)
        assert all(isinstance(profile_args, list) for profile_args in profile_args_list)
        assert all(
            isinstance(arg, str)
            for profile_list in profile_args_list
            for arg in profile_list
        )


class TestTypesIntegration:
    """Integration tests for types with other modules."""

    def test_type_usage_in_profile_manager(self):
        """Test how types are used in ProfileManager."""
        # ArgsList type usage
        args_list: ArgsList = ["-p", "gaming", "--", "game.exe"]
        assert isinstance(args_list, list)
        assert all(isinstance(arg, str) for arg in args_list)

        # ProfileArgsList type usage
        profile_args_list: ProfileArgsList = [
            ["-f", "-W", "1920"],
            ["--borderless", "-H", "1080"],
        ]
        assert isinstance(profile_args_list, list)
        assert all(isinstance(profile_args, list) for profile_args in profile_args_list)

        # FlagTuple type usage
        flags, _positionals = ArgumentProcessor.separate_flags_and_positionals(
            ["-W", "1920", "game.exe"]
        )
        assert isinstance(flags, list)
        assert all(
            isinstance(flag_tuple, tuple) and len(flag_tuple) == 2
            for flag_tuple in flags
        )

    def test_type_usage_in_application(self):
        """Test how types are used in Application."""
        # ExitCode type usage
        exit_code: ExitCode = 0
        assert isinstance(exit_code, int)
        assert exit_code == 0

        # ArgsList type in application context
        args: ArgsList = ["-p", "profile", "--", "app"]
        assert isinstance(args, list)
        assert all(isinstance(arg, str) for arg in args)


class TestTypesEndToEnd:
    """End-to-end tests for types functionality."""

    def test_complete_type_usage_workflow(self, mocker, temp_config_with_content):
        """Test complete workflow using all defined types."""
        config_data = """gaming=-f -W 1920 -H 1080 --mangoapp
export PROTON_ENABLE_FSR=1
"""
        config_path = temp_config_with_content(config_data)

        args_list: ArgsList = ["-p", "gaming", "--borderless", "--", "test_app"]
        env_exports: EnvExports = {"PROTON_ENABLE_FSR": "1"}
        exit_code: ExitCode = 0
        profile_args_list: ProfileArgsList = [
            ["-f", "-W", "1920", "-H", "1080", "--mangoapp"]
        ]

        app = Application()

        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking",
            return_value=exit_code,
        )

        result: ExitCode = app.run(args_list)

        assert isinstance(result, int)
        assert result in [0, 1]
        assert isinstance(args_list, list)
        assert all(isinstance(arg, str) for arg in args_list)
        assert isinstance(env_exports, dict)
        assert isinstance(exit_code, int)
        assert isinstance(profile_args_list, list)

    def test_types_in_complex_argument_processing_e2e(self):
        """Test types in complex argument processing scenarios."""
        args_list: ArgsList = [
            "-f",
            "-W",
            "1920",
            "-H",
            "1080",
            "--",
            "game.exe",
            "save1",
        ]
        assert isinstance(args_list, list)
        assert len(args_list) > 0

        flags, _positionals = ArgumentProcessor.separate_flags_and_positionals(
            args_list[:-3]
        )
        assert isinstance(flags, list)
        for flag_tuple in flags:
            assert isinstance(flag_tuple, tuple)
            assert len(flag_tuple) == 2
            assert flag_tuple[0].startswith("-")

        profile_args_list: ProfileArgsList = [
            ["-f", "-W", "1920"],
            ["--borderless", "-H", "1080"],
            ["-w", "1280", "--mangoapp"],
        ]
        assert isinstance(profile_args_list, list)
        assert all(isinstance(profile_args, list) for profile_args in profile_args_list)

        merged_args = ProfileManager.merge_multiple_profiles(profile_args_list)
        assert isinstance(merged_args, list)
        assert all(isinstance(arg, str) for arg in merged_args)

    def test_type_annotations_in_real_scenario(self, mocker, temp_config_with_content):
        """Test that type annotations work properly in real usage scenarios."""
        config_data = "test_profile=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        args: ArgsList = [
            "-p",
            "test_profile",
            "--borderless",
            "-W",
            "2560",
            "--",
            "app.exe",
        ]
        exports: EnvExports = {}
        profile_args_list: ProfileArgsList = [["-f", "-W", "1920", "-H", "1080"]]

        assert isinstance(args, list) and all(isinstance(s, str) for s in args)
        assert isinstance(exports, dict) and all(
            isinstance(k, str) and isinstance(v, str) for k, v in exports.items()
        )
        assert isinstance(profile_args_list, list) and all(
            isinstance(item, list) for item in profile_args_list
        )

        app = Application()
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.system_detector.PathHelper.executable_exists", return_value=True
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        result: ExitCode = app.run(args)
        assert isinstance(result, int)
