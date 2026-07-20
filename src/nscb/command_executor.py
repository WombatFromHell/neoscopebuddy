"""Command building and execution functionality for NeoscopeBuddy."""

import os
import shlex
import subprocess

from .environment_helper import EnvironmentHelper, debug_log
from .system_detector import SystemDetector
from .types import ArgsList, CommandTuple, EnvExports, ExitCode


class CommandExecutor:
    """Handles command building and execution."""

    @staticmethod
    def run_nonblocking(cmd: str, extra_env: EnvExports | None = None) -> ExitCode:
        """Execute command, forwarding stdout/stderr in real-time."""
        # ponytail: subprocess.run inherits stdio by default, preserving
        # interleaving that the old Popen+readline selector loop lost.
        env = {**os.environ, **extra_env} if extra_env else None
        return subprocess.run(cmd, shell=True, env=env).returncode

    @staticmethod
    def get_env_commands() -> CommandTuple:
        """Get pre/post commands from environment."""
        return EnvironmentHelper.get_pre_post_commands()

    @staticmethod
    def build_command(parts: ArgsList) -> str:
        """Build command string from parts with proper filtering."""
        # Filter out empty strings before joining to avoid semicolon artifacts
        filtered_parts = [part for part in parts if part]
        return "; ".join(filtered_parts)

    @staticmethod
    def execute_gamescope_command(
        final_args: ArgsList, exports: EnvExports | None = None
    ) -> ExitCode:
        """Execute gamescope command with proper handling and return exit code."""
        debug_log(
            f"execute_gamescope_command: final_args={final_args}, exports={exports}"
        )

        if exports is None:
            exports = {}

        pre_cmd, post_cmd = CommandExecutor.get_env_commands()

        gamescope_active = SystemDetector.is_gamescope_active()
        debug_log(f"execute_gamescope_command: gamescope is active: {gamescope_active}")

        if gamescope_active:
            command = CommandExecutor._build_active_gamescope_command(
                final_args, pre_cmd, post_cmd
            )
        else:
            command = CommandExecutor._build_inactive_gamescope_command(
                final_args, pre_cmd, post_cmd
            )

        debug_log(f"execute_gamescope_command: built command: {command}")

        if not command:
            debug_log("execute_gamescope_command: no command to execute, returning 0")
            return 0

        print("Executing:", command, flush=True)
        # exports are passed as real subprocess environment so they apply
        # uniformly to gamescope AND the app - matching what a user gets by
        # exporting the var in their own shell before invoking nscb.
        return CommandExecutor.run_nonblocking(command, exports)

    @staticmethod
    def _build_inactive_gamescope_command(
        args: ArgsList, pre_cmd: str, post_cmd: str
    ) -> str:
        """Build command when gamescope is not active."""
        has_ld_preload = CommandExecutor._check_ld_preload_status()

        try:
            dash_index = args.index("--")
            gamescope_args = args[:dash_index]
            app_args = args[dash_index + 1 :]
            debug_log(
                f"_build_inactive_gamescope_command: gamescope_args={gamescope_args}, app_args={app_args}"
            )

            gamescope_cmd = CommandExecutor._build_gamescope_command_for_inactive(
                gamescope_args, has_ld_preload
            )
            final_app_cmd = CommandExecutor._build_final_app_command(
                app_args, has_ld_preload
            )

            full_cmd = f"{gamescope_cmd} -- {final_app_cmd}"
            final_command = CommandExecutor.build_command([pre_cmd, full_cmd, post_cmd])
        except ValueError:
            gamescope_cmd = CommandExecutor._build_gamescope_command_for_inactive(
                args, has_ld_preload
            )
            final_command = CommandExecutor.build_command(
                [pre_cmd, gamescope_cmd, post_cmd]
            )
        return final_command

    @staticmethod
    def _check_ld_preload_status() -> bool:
        """Check if LD_PRELOAD wrapping should be handled."""
        disable_ld_preload_wrap = EnvironmentHelper.should_disable_ld_preload_wrap()
        debug_log(
            f"_check_ld_preload_status: LD_PRELOAD wrapping disabled: {disable_ld_preload_wrap}"
        )

        original_ld_preload = os.environ.get("LD_PRELOAD")
        debug_log(
            f"_check_ld_preload_status: Original LD_PRELOAD value: {original_ld_preload}"
        )

        has_ld_preload = bool(original_ld_preload) and not disable_ld_preload_wrap
        debug_log(
            f"_check_ld_preload_status: LD_PRELOAD will be handled: {has_ld_preload}"
        )
        return has_ld_preload

    @staticmethod
    def _build_gamescope_command_for_inactive(
        gamescope_args: ArgsList, has_ld_preload: bool
    ) -> str:
        """Build gamescope command for inactive state."""
        if has_ld_preload:
            return CommandExecutor._build_app_command(
                ["env", "-u", "LD_PRELOAD", "gamescope"] + gamescope_args
            )
        else:
            return CommandExecutor._build_app_command(["gamescope"] + gamescope_args)

    @staticmethod
    def _build_active_gamescope_command(
        args: ArgsList, pre_cmd: str, post_cmd: str
    ) -> str:
        """Build command when gamescope is already active."""
        has_ld_preload = CommandExecutor._check_ld_preload_status()

        try:
            dash_index = args.index("--")
            app_args = args[dash_index + 1 :]
            debug_log(f"_build_active_gamescope_command: app_args={app_args}")

            final_app_cmd = CommandExecutor._build_final_app_command(
                app_args, has_ld_preload
            )

            if not pre_cmd and not post_cmd:
                return final_app_cmd
            else:
                return CommandExecutor.build_command([pre_cmd, final_app_cmd, post_cmd])
        except ValueError:
            return CommandExecutor.build_command([pre_cmd, post_cmd])

    @staticmethod
    def _build_final_app_command(app_args: ArgsList, has_ld_preload: bool) -> str:
        """Build the final application command, restoring LD_PRELOAD if needed.

        User exports are no longer spliced in here - they're passed as real
        subprocess environment (see execute_gamescope_command) so they apply
        to gamescope too, not just the app.
        """
        if has_ld_preload:
            ld_preload_value = os.environ.get("LD_PRELOAD", "")
            parts = ["env", f"LD_PRELOAD={shlex.quote(ld_preload_value)}"]
        else:
            parts = []
        parts.extend(app_args)
        return CommandExecutor._build_app_command(parts)

    @staticmethod
    def _build_app_command(args: ArgsList) -> str:
        """Build application command from arguments."""
        if not args:
            return ""
        quoted = [shlex.quote(arg) for arg in args]
        return " ".join(quoted)
