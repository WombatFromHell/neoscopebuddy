"""Command building and execution functionality for NeoscopeBuddy."""

import os
import selectors
import shlex
import subprocess
import sys
from typing import TextIO, cast

from .environment_helper import EnvironmentHelper
from .system_detector import SystemDetector
from .types import ArgsList, CommandTuple, EnvExports, ExitCode


def debug_log(message: str) -> None:
    """Log debug message when NSCB_DEBUG=1 is set."""
    if os.environ.get("NSCB_DEBUG", "").lower() in ("1", "true", "yes", "on"):
        print(f"[DEBUG] {message}", file=sys.stderr, flush=True)


class CommandExecutor:
    """Handles command building and execution."""

    @staticmethod
    def run_nonblocking(cmd: str) -> ExitCode:
        """Execute command with non-blocking I/O, forwarding stdout/stderr in real-time."""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            bufsize=0,
            text=True,
        )

        sel = selectors.DefaultSelector()
        fileobjs = [cast(TextIO, process.stdout), cast(TextIO, process.stderr)]
        for fileobj in fileobjs:
            if fileobj:
                sel.register(cast(TextIO, fileobj), selectors.EVENT_READ)

        while sel.get_map():
            for key, _ in sel.select():
                fileobj: TextIO = cast(TextIO, key.fileobj)
                try:
                    line = fileobj.readline()
                    if not line:
                        sel.unregister(fileobj)
                        continue
                except (IOError, OSError):
                    # If we can't read from the fileobj, unregister it
                    sel.unregister(fileobj)
                    continue

                target = sys.stdout if fileobj is process.stdout else sys.stderr
                target.write(line)
                target.flush()

        return process.wait()

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
                final_args, pre_cmd, post_cmd, exports
            )
        else:
            command = CommandExecutor._build_inactive_gamescope_command(
                final_args, pre_cmd, post_cmd, exports
            )

        debug_log(f"execute_gamescope_command: built command: {command}")

        if not command:
            debug_log("execute_gamescope_command: no command to execute, returning 0")
            return 0

        print("Executing:", command, flush=True)
        return CommandExecutor.run_nonblocking(command)

    @staticmethod
    def _build_inactive_gamescope_command(
        args: ArgsList, pre_cmd: str, post_cmd: str, exports: EnvExports | None = None
    ) -> str:
        """Build command when gamescope is not active."""
        if exports is None:
            exports = {}

        # Check LD_PRELOAD status
        has_ld_preload = CommandExecutor._check_ld_preload_status()

        # Process the args to handle the -- separator properly
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
                app_args, exports, has_ld_preload
            )

            # Combine with the -- separator
            full_cmd = f"{gamescope_cmd} -- {final_app_cmd}"
            final_command = CommandExecutor.build_command([pre_cmd, full_cmd, post_cmd])
        except ValueError:
            # If no -- separator found, just run gamescope appropriately
            gamescope_cmd = CommandExecutor._build_gamescope_command_for_inactive(
                args, has_ld_preload
            )
            final_command = CommandExecutor._build_command_for_no_separator(
                pre_cmd, post_cmd, gamescope_cmd, exports
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

        # Check if LD_PRELOAD is set and not empty and not disabled
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
    def _build_final_app_command(
        app_args: ArgsList, exports: EnvExports, has_ld_preload: bool
    ) -> str:
        """Build the final application command with proper exports and LD_PRELOAD handling."""
        if exports:
            # Add exports as env prefix to the app command
            env_prefix = ["env"] + [f"{k}={shlex.quote(v)}" for k, v in exports.items()]
            if has_ld_preload:
                # If LD_PRELOAD is also being handled, combine both into a single env command
                ld_preload_value = os.environ.get("LD_PRELOAD", "")
                # Add LD_PRELOAD to the same env command to avoid nesting
                env_prefix.append(f"LD_PRELOAD={shlex.quote(ld_preload_value)}")
                final_app_cmd_parts = env_prefix + app_args
                final_app_cmd = CommandExecutor._build_app_command(final_app_cmd_parts)
            else:
                # Just add export env prefix to app_args
                final_app_cmd_parts = env_prefix + app_args
                final_app_cmd = CommandExecutor._build_app_command(final_app_cmd_parts)
        else:
            # No exports, but might still have LD_PRELOAD
            if has_ld_preload:
                # Wrap app in env LD_PRELOAD="..." to preserve the original LD_PRELOAD
                ld_preload_value = os.environ.get("LD_PRELOAD", "")
                app_cmd_parts = [
                    "env",
                    f"LD_PRELOAD={shlex.quote(ld_preload_value)}",
                ] + app_args
                final_app_cmd = CommandExecutor._build_app_command(app_cmd_parts)
            else:
                # No exports and no LD_PRELOAD, just build the app command
                final_app_cmd = CommandExecutor._build_app_command(app_args)
        return final_app_cmd

    @staticmethod
    def _build_command_for_no_separator(
        pre_cmd: str, post_cmd: str, gamescope_cmd: str, exports: EnvExports
    ) -> str:
        """Build command when no -- separator is found."""
        if exports:
            # Create env command to execute exports (this is for when there are no app args but exports exist)
            # We run the exports as a separate command since there's no app to prefix
            env_cmd = (
                ["env"]
                + [f"{k}={shlex.quote(v)}" for k, v in exports.items()]
                + ["true"]
            )
            export_cmd = CommandExecutor._build_app_command(env_cmd)
            final_command = CommandExecutor.build_command(
                [pre_cmd, export_cmd, gamescope_cmd, post_cmd]
            )
        else:
            final_command = CommandExecutor.build_command(
                [pre_cmd, gamescope_cmd, post_cmd]
            )
        return final_command

    @staticmethod
    def _build_active_gamescope_command(
        args: ArgsList, pre_cmd: str, post_cmd: str, exports: EnvExports | None = None
    ) -> str:
        """Build command when gamescope is already active."""

        if exports is None:
            exports = {}

        # Check LD_PRELOAD status
        has_ld_preload = CommandExecutor._check_ld_preload_status()

        try:
            dash_index = args.index("--")
            app_args = args[dash_index + 1 :]
            debug_log(f"_build_active_gamescope_command: app_args={app_args}")

            final_app_cmd = CommandExecutor._build_final_app_command(
                app_args, exports, has_ld_preload
            )

            # If pre_cmd and post_cmd are both empty, just execute the app args directly
            if not pre_cmd and not post_cmd:
                return final_app_cmd
            else:
                final_command = CommandExecutor.build_command(
                    [pre_cmd, final_app_cmd, post_cmd]
                )
                return final_command
        except ValueError:
            # If no -- separator found but we have pre/post commands, use those
            return CommandExecutor._build_command_for_active_no_separator(
                pre_cmd, post_cmd, exports
            )

    @staticmethod
    def _build_command_for_active_no_separator(
        pre_cmd: str, post_cmd: str, exports: EnvExports
    ) -> str:
        """Build command when no -- separator is found and gamescope is active."""
        return CommandExecutor._build_active_no_separator_command(
            pre_cmd, post_cmd, exports
        )

    @staticmethod
    def _build_active_no_separator_command(
        pre_cmd: str, post_cmd: str, exports: EnvExports
    ) -> str:
        """Build command for active gamescope with no separator and no app args."""
        if exports:
            return CommandExecutor._build_active_no_separator_with_exports(
                pre_cmd, post_cmd, exports
            )
        else:
            return CommandExecutor._build_active_no_separator_no_exports(
                pre_cmd, post_cmd
            )

    @staticmethod
    def _build_active_no_separator_with_exports(
        pre_cmd: str, post_cmd: str, exports: EnvExports
    ) -> str:
        """Build command with exports when no app args are present."""
        # Create env command for exports
        env_cmd_parts = ["env"] + [
            f"{k}={shlex.quote(v)}" for k, v in exports.items()
        ]
        export_cmd = CommandExecutor._build_app_command(env_cmd_parts)
        
        if not pre_cmd and not post_cmd:
            # If no pre/post commands, just run exports and exit
            return export_cmd
        else:
            # Combine pre/post commands with export command
            return CommandExecutor.build_command([pre_cmd, export_cmd, post_cmd])

    @staticmethod
    def _build_active_no_separator_no_exports(
        pre_cmd: str, post_cmd: str
    ) -> str:
        """Build command without exports when no app args are present."""
        if not pre_cmd and not post_cmd:
            return ""
        else:
            # Combine pre/post commands only
            return CommandExecutor.build_command([pre_cmd, post_cmd])

    @staticmethod
    def _build_app_command(args: ArgsList) -> str:
        """Build application command from arguments."""
        if not args:
            return ""
        quoted = [shlex.quote(arg) for arg in args]
        return " ".join(quoted)
