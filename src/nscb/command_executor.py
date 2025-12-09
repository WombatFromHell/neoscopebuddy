"""Command building and execution functionality for NeoscopeBuddy."""

import os
import selectors
import shlex
import subprocess
import sys
from typing import TextIO, cast

from .environment_helper import EnvironmentHelper
from .system_detector import SystemDetector
from .types import ArgsList, EnvExports, ExitCode


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
                line = fileobj.readline()
                if not line:
                    sel.unregister(fileobj)
                    continue

                target = sys.stdout if fileobj is process.stdout else sys.stderr
                target.write(line)
                target.flush()

        return process.wait()

    @staticmethod
    def get_env_commands() -> tuple[str, str]:
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

        # Check if LD_PRELOAD wrapping should be disabled
        disable_ld_preload_wrap = EnvironmentHelper.should_disable_ld_preload_wrap()
        debug_log(
            f"_build_inactive_gamescope_command: LD_PRELOAD wrapping disabled: {disable_ld_preload_wrap}"
        )

        # Check if LD_PRELOAD is set in the environment
        original_ld_preload = os.environ.get("LD_PRELOAD")
        debug_log(
            f"_build_inactive_gamescope_command: Original LD_PRELOAD value: {original_ld_preload}"
        )

        has_ld_preload = original_ld_preload and not disable_ld_preload_wrap
        debug_log(
            f"_build_inactive_gamescope_command: LD_PRELOAD will be handled: {has_ld_preload}"
        )

        # Process the args to handle the -- separator properly
        try:
            dash_index = args.index("--")
            gamescope_args = args[:dash_index]
            app_args = args[dash_index + 1 :]
            debug_log(
                f"_build_inactive_gamescope_command: gamescope_args={gamescope_args}, app_args={app_args}"
            )

            # Build gamescope command - only use env -u LD_PRELOAD if LD_PRELOAD is set and not disabled
            if has_ld_preload:
                gamescope_cmd = CommandExecutor._build_app_command(
                    ["env", "-u", "LD_PRELOAD", "gamescope"] + gamescope_args
                )
            else:
                gamescope_cmd = CommandExecutor._build_app_command(
                    ["gamescope"] + gamescope_args
                )

            # Apply exports to the app command using env prefix
            if exports:
                # Add exports as env prefix to the app command
                env_prefix = ["env"] + [
                    f"{k}={shlex.quote(v)}" for k, v in exports.items()
                ]
                if has_ld_preload:
                    # If LD_PRELOAD is also being handled, combine both into a single env command
                    ld_preload_value = os.environ.get("LD_PRELOAD", "")
                    # Add LD_PRELOAD to the same env command to avoid nesting
                    env_prefix.append(f"LD_PRELOAD={shlex.quote(ld_preload_value)}")
                    final_app_cmd_parts = env_prefix + app_args
                    final_app_cmd = CommandExecutor._build_app_command(
                        final_app_cmd_parts
                    )
                else:
                    # Just add export env prefix to app_args
                    final_app_cmd_parts = env_prefix + app_args
                    final_app_cmd = CommandExecutor._build_app_command(
                        final_app_cmd_parts
                    )
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

            # Combine with the -- separator
            full_cmd = f"{gamescope_cmd} -- {final_app_cmd}"
            final_command = CommandExecutor.build_command([pre_cmd, full_cmd, post_cmd])
        except ValueError:
            # If no -- separator found, just run gamescope appropriately
            if has_ld_preload:
                gamescope_cmd = CommandExecutor._build_app_command(
                    ["env", "-u", "LD_PRELOAD", "gamescope"] + args
                )
            else:
                gamescope_cmd = CommandExecutor._build_app_command(["gamescope"] + args)

            # Apply exports to the command if there are no app args but there are exports
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

        # Check if LD_PRELOAD wrapping should be disabled
        disable_ld_preload_wrap = EnvironmentHelper.should_disable_ld_preload_wrap()
        debug_log(
            f"_build_active_gamescope_command: LD_PRELOAD wrapping disabled: {disable_ld_preload_wrap}"
        )

        # Check if LD_PRELOAD is set in the environment
        original_ld_preload = os.environ.get("LD_PRELOAD")
        debug_log(
            f"_build_active_gamescope_command: Original LD_PRELOAD value: {original_ld_preload}"
        )

        has_ld_preload = original_ld_preload and not disable_ld_preload_wrap
        debug_log(
            f"_build_active_gamescope_command: LD_PRELOAD will be handled: {has_ld_preload}"
        )

        try:
            dash_index = args.index("--")
            app_args = args[dash_index + 1 :]
            debug_log(f"_build_active_gamescope_command: app_args={app_args}")

            # Apply exports to the app command using env prefix
            if exports:
                # Add exports as env prefix to the app command
                env_prefix = ["env"] + [
                    f"{k}={shlex.quote(v)}" for k, v in exports.items()
                ]
                if has_ld_preload:
                    # If LD_PRELOAD is also being handled, combine both into a single env command
                    ld_preload_value = os.environ.get("LD_PRELOAD", "")
                    # Add LD_PRELOAD to the same env command to avoid nesting
                    env_prefix.append(f"LD_PRELOAD={shlex.quote(ld_preload_value)}")
                    final_app_cmd_parts = env_prefix + app_args
                    final_app_cmd = CommandExecutor._build_app_command(
                        final_app_cmd_parts
                    )
                else:
                    # Just add export env prefix to app_args
                    final_app_cmd_parts = env_prefix + app_args
                    final_app_cmd = CommandExecutor._build_app_command(
                        final_app_cmd_parts
                    )
            else:
                # If no exports but LD_PRELOAD exists, still need to handle LD_PRELOAD
                if has_ld_preload:
                    # Use shlex.quote to properly handle the LD_PRELOAD value
                    ld_preload_value = os.environ.get("LD_PRELOAD", "")
                    # Wrap app in env LD_PRELOAD="..." to preserve the original LD_PRELOAD
                    app_cmd_parts = [
                        "env",
                        f"LD_PRELOAD={shlex.quote(ld_preload_value)}",
                    ] + app_args
                    final_app_cmd = CommandExecutor._build_app_command(app_cmd_parts)
                else:
                    final_app_cmd = CommandExecutor._build_app_command(app_args)

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
            # Build command with exports if there are exports but no app args
            if exports:
                # Create env command for exports
                env_cmd_parts = ["env"] + [
                    f"{k}={shlex.quote(v)}" for k, v in exports.items()
                ]
                export_cmd = CommandExecutor._build_app_command(env_cmd_parts)
                if not pre_cmd and not post_cmd:
                    # If no pre/post commands, just run exports and exit
                    return export_cmd
                else:
                    final_command = CommandExecutor.build_command(
                        [pre_cmd, export_cmd, post_cmd]
                    )
                    return final_command
            elif not pre_cmd and not post_cmd:
                return ""
            else:
                final_command = CommandExecutor.build_command([pre_cmd, post_cmd])
                return final_command

    @staticmethod
    def _build_app_command(args: ArgsList) -> str:
        """Build application command from arguments."""
        if not args:
            return ""
        quoted = [shlex.quote(arg) for arg in args]
        return " ".join(quoted)
