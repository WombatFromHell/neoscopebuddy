"""Command building and execution functionality for NeoscopeBuddy."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

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
        except ValueError:
            gamescope_args = args
            app_args = []

        gamescope_args = CommandExecutor._apply_framelimit(gamescope_args)
        debug_log(
            f"_build_inactive_gamescope_command: gamescope_args={gamescope_args}, app_args={app_args}"
        )

        if app_args:
            gamescope_cmd = CommandExecutor._build_gamescope_command_for_inactive(
                gamescope_args, has_ld_preload
            )
            final_app_cmd = CommandExecutor._build_final_app_command(
                app_args, has_ld_preload
            )
            full_cmd = f"{gamescope_cmd} -- {final_app_cmd}"
            final_command = CommandExecutor.build_command([pre_cmd, full_cmd, post_cmd])
        else:
            gamescope_cmd = CommandExecutor._build_gamescope_command_for_inactive(
                gamescope_args, has_ld_preload
            )
            final_command = CommandExecutor.build_command(
                [pre_cmd, gamescope_cmd, post_cmd]
            )
        return final_command

    @staticmethod
    def _apply_framelimit(gamescope_args: ArgsList) -> ArgsList:
        """Prepend NSCB_FRAMELIMIT as -r, overriding any existing -r/--nested-refresh."""
        # ponytail: env force-wins; only matters at gamescope launch (inactive path).
        refresh = EnvironmentHelper.get_framelimit()
        if refresh is None:
            return gamescope_args
        stripped = CommandExecutor._strip_flag(
            gamescope_args, {"-r", "--nested-refresh"}
        )
        debug_log(f"_apply_framelimit: injecting -r {refresh}")
        return ["-r", str(refresh)] + stripped

    @staticmethod
    def _strip_flag(args: ArgsList, names: set[str]) -> ArgsList:
        """Remove the given flags and their values (two-token or --name=val form)."""
        result: ArgsList = []
        i = 0
        while i < len(args):
            token = args[i]
            if token in names:
                i += 2 if i + 1 < len(args) else 1
                continue
            if any(token.startswith(f"{n}=") for n in names):
                i += 1
                continue
            result.append(token)
            i += 1
        return result

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

    @staticmethod
    def evaluate_condition(condition: str) -> bool:
        """Evaluate a structured gamescope_condition predicate.

        Supported forms:
        env:VAR=value   - true if os.environ.get(VAR) == value
        env:VAR         - true if VAR is set (any non-empty value)
        cmd:name        - true if `name` is found on PATH (shutil.which)
        file:/path       - true if path exists

        No shell is invoked - this is pure Python string matching against
        os.environ / shutil.which / Path.exists, so there is no command
        injection surface regardless of what's written in nscb.conf.
        """
        if condition.startswith("env:"):
            rest = condition[4:]
            if "=" in rest:
                var, _, value = rest.partition("=")
                return os.environ.get(var) == value
            return bool(os.environ.get(rest))
        if condition.startswith("cmd:"):
            return shutil.which(condition[4:]) is not None
        if condition.startswith("file:"):
            return Path(condition[5:]).exists()
        return False  # unrecognized form - fail closed, don't guess

    @staticmethod
    def execute_bare(args: ArgsList, exports: EnvExports | None = None) -> ExitCode:
        """Run the app command directly, bypassing gamescope.

        Applies NSCB_PRE_CMD / NSCB_POST_CMD consistently with the gamescope
        paths so condition-triggered fallback doesn't silently drop hooks.
        """
        try:
            dash_index = args.index("--")
            app_args = args[dash_index + 1 :]
        except ValueError:
            debug_log("execute_bare: no '--' separator found")
            return 1

        if not app_args:
            return 0

        cmd = CommandExecutor._build_app_command(app_args)
        pre_cmd, post_cmd = CommandExecutor.get_env_commands()
        final_command = CommandExecutor.build_command([pre_cmd, cmd, post_cmd])

        print("Executing (no gamescope):", final_command, flush=True)
        return CommandExecutor.run_nonblocking(final_command, exports)
