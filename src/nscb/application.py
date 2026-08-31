#!/usr/bin/env python3
"""Main application orchestrator for NeoscopeBuddy."""

import logging
import os
import shlex
import shutil
import sys
from typing import Optional

from .command_executor import CommandExecutor
from .config_manager import ConfigManager
from .environment_helper import EnvironmentHelper, debug_log
from .exceptions import ConfigNotFoundError, NscbError, ProfileNotFoundError
from .profile_manager import ProfileManager

__version__ = "{{VERSION}}"  # Replaced at build time


def print_help() -> None:
    """Print concise help message about nscb functionality."""
    print(
        f"""\
neoscopebuddy v{__version__} – gamescope wrapper
USAGE
  nscb.pyz [--help]
  nscb.pyz [-p profile[,...]] [--profile=profile[,...]]
           [--profiles=profile[,...]] [gamescope flags] [-- app...]

  If -- is present, everything after it is passed to the application.
  Gamescope flags before -- override matching profile flags.

PROFILES
  -p, --profile       Select one or more comma-separated profiles
  --profiles=         Same as --profile (alternative spelling)
  Reserved names: help, export
  Profile overrides:
    nscb.pyz -p gaming -W 2560 -H 1440 -- /bin/mygame

CONFIG FILE
  Path: $XDG_CONFIG_HOME/nscb.conf  or  ~/.config/nscb.conf
  Lines starting with # are comments.
  Sections group args and exports per profile:

    [gaming]
    -f -W 1920 -H 1080
    export MANGOHUD=1
    [quiet]
    -b

  Global exports (before any section) always apply:
    export DISPLAY=:0

  Legacy flat syntax also works:
    gaming=-f -W 1920 -H 1080
    export MANGOHUD=1

  gamescope_condition=<predicate>
    Checked before launching. If it evaluates false, the app runs
    directly without gamescope — pre/post hooks still apply on the
    fallback path.

    Supported predicates:
      env:VAR=value   true if the environment variable VAR equals value
      env:VAR         true if VAR is set to any non-empty value
      cmd:name        true if `name` is found on PATH
      file:/path      true if the given path exists

    [gaming]
    gamescope_condition=env:XDG_CURRENT_DESKTOP=niri
    -f -W 1920 -H 1080

    No shell is invoked; unrecognized predicate forms fail closed
    (treated as false) rather than erroring.
    If multiple selected profiles define gamescope_condition, last wins.

ENVIRONMENT HOOKS (optional)
  NSCB_PRE_CMD=command              Run before gamescope
  NSCB_POST_CMD=command             Run after gamescope exits
  NSCB_DEBUG=1                      Enable debug logging to stderr
  NSCB_DISABLE_LD_PRELOAD_WRAP=1    Skip preserving LD_PRELOAD to child process 
                                     (by default, nscb re-injects LD_PRELOAD after
                                     gamescope strips it; set this to disable)
  NSCB_FRAMELIMIT=<hz>               Force -r/--nested-refresh, overriding any
                                      profile or explicit -r (ignored when gamescope
                                      is already active)
  NSCB_AUTO_RES=<0|1|true|false>     Auto-inject -W/-H from the active display
                                       (niri/KDE). On by default when no -w/-h/-W/-H
                                       flag is given; explicit flags always win
  NSCB_FORCE_NESTED=1                Force launching a nested gamescope even when one
                                       is already active (default: stay inside the
                                       existing session)
          """
    )


class Application:
    """Main application orchestrator."""

    def __init__(
        self,
        profile_manager: Optional[ProfileManager] = None,
        config_manager: Optional[ConfigManager] = None,
        command_executor: Optional[CommandExecutor] = None,
    ):
        self.profile_manager = profile_manager or ProfileManager()
        self.config_manager = config_manager or ConfigManager()
        self.command_executor = command_executor or CommandExecutor()

    def run(self, args: list[str]) -> int:
        """Run the application with the given arguments."""
        # ponytail: always capture saved LD_PRELOAD when NSCB_DEBUG=1, even for --help (which bypasses execute path).
        debug_log(
            f"startup: argv={args!r} NSCB_ORIG_LD_PRELOAD={os.environ.get('NSCB_ORIG_LD_PRELOAD')!r} LD_PRELOAD={os.environ.get('LD_PRELOAD')!r} NSCB_ORIG_LD_LIBRARY_PATH={os.environ.get('NSCB_ORIG_LD_LIBRARY_PATH')!r} LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')!r}"
        )
        # Handle help request
        if not args or "--help" in args:
            print_help()
            return 0

        # Validate dependencies
        if shutil.which("gamescope") is None:
            logging.error("'gamescope' not found in PATH")
            return 1

        # Parse profiles and remaining args
        profiles, remaining_args = self.profile_manager.parse_profile_args(args)

        # Process profiles if any
        if profiles:
            try:
                final_args, exports, gamescope_condition = self._process_profiles(
                    profiles, remaining_args
                )
            except NscbError as e:
                logging.error(str(e))
                return 1
        else:
            final_args = remaining_args
            exports = {}
            gamescope_condition = None

        # gamescope_condition only applies to the initial launch decision —
        # once gamescope is active we're already committed to running inside it
        # (unless NSCB_FORCE_NESTED overrides us into launching a nested session)
        if gamescope_condition is not None and not (
            EnvironmentHelper.is_gamescope_active()
            and not EnvironmentHelper.force_nested()
        ):
            if not self.command_executor.evaluate_condition(gamescope_condition):
                return self.command_executor.execute_bare(final_args, exports)

        # Execute the command
        return self.command_executor.execute_gamescope_command(final_args, exports)

    def _process_profiles(
        self, profiles: list[str], args: list[str]
    ) -> tuple[list[str], dict[str, str], str | None]:
        """Process profiles and merge with arguments, returning args, exports, and gamescope_condition."""
        config_file = self.config_manager.find_config_file()
        if not config_file:
            raise ConfigNotFoundError("could not find nscb.conf")

        config_result = self.config_manager.load_config(config_file)
        merged_profiles = []
        exports = dict(config_result.exports)
        gamescope_condition = None

        for profile in profiles:
            if profile not in config_result.profiles:
                raise ProfileNotFoundError(profile)
            entry = config_result.profiles[profile]
            merged_profiles.append(shlex.split(entry.args))
            exports.update(entry.exports)
            if entry.gamescope_condition is not None:
                gamescope_condition = entry.gamescope_condition

        final_args = self.profile_manager.merge_multiple_profiles(
            merged_profiles + [args]
        )
        return final_args, exports, gamescope_condition


def main() -> int:
    """Main entry point."""
    try:
        app = Application()
        return app.run(sys.argv[1:])
    except NscbError as e:
        logging.error(str(e))
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1
