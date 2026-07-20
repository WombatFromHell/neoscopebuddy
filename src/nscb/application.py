#!/usr/bin/env python3
"""Main application orchestrator for NeoscopeBuddy."""

import logging
import shlex
import sys
from typing import Optional

from .command_executor import CommandExecutor
from .config_manager import ConfigManager
from .exceptions import ConfigNotFoundError, NscbError, ProfileNotFoundError
from .profile_manager import ProfileManager
from .system_detector import SystemDetector
from .types import ArgsList, EnvExports, ExitCode

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

  Legacy flat syntax still works:
    gaming=-f -W 1920 -H 1080
    export MANGOHUD=1

ENVIRONMENT HOOKS (optional)
  NSCB_PRE_CMD=command      Run before gamescope
  NSCB_POST_CMD=command     Run after gamescope exits
  NSCB_DEBUG=1              Enable debug logging to stderr
  NSCB_DISABLE_LD_PRELOAD_WRAP=1
                            Skip preserving LD_PRELOAD to child process
                            (by default, nscb re-injects LD_PRELOAD after
                            gamescope strips it; set this to disable)
  (Legacy names: NSCB_PRECMD, NSCB_POSTCMD)"""
    )


class Application:
    """Main application orchestrator."""

    def __init__(
        self,
        profile_manager: Optional[ProfileManager] = None,
        config_manager: Optional[ConfigManager] = None,
        command_executor: Optional[CommandExecutor] = None,
        system_detector: Optional[SystemDetector] = None,
    ):
        self.profile_manager = profile_manager or ProfileManager()
        self.config_manager = config_manager or ConfigManager()
        self.command_executor = command_executor or CommandExecutor()
        self.system_detector = system_detector or SystemDetector()

    def run(self, args: ArgsList) -> ExitCode:
        """Run the application with the given arguments."""
        # Handle help request
        if not args or "--help" in args:
            print_help()
            return 0

        # Validate dependencies
        if not self.system_detector.find_executable("gamescope"):
            logging.error("'gamescope' not found in PATH")
            return 1

        # Parse profiles and remaining args
        profiles, remaining_args = self.profile_manager.parse_profile_args(args)

        # Process profiles if any
        if profiles:
            try:
                final_args, exports = self._process_profiles(profiles, remaining_args)
            except NscbError as e:
                logging.error(str(e))
                return 1
        else:
            final_args = remaining_args
            exports = {}

        # Execute the command
        return self.command_executor.execute_gamescope_command(final_args, exports)

    def _process_profiles(
        self, profiles: ArgsList, args: ArgsList
    ) -> tuple[ArgsList, EnvExports]:
        """Process profiles and merge with arguments, returning both arguments and exports."""
        config_file = self.config_manager.find_config_file()
        if not config_file:
            raise ConfigNotFoundError("could not find nscb.conf")

        config_result = self.config_manager.load_config(config_file)
        merged_profiles = []
        exports = dict(config_result.exports)

        for profile in profiles:
            if profile not in config_result.profiles:
                raise ProfileNotFoundError(profile)
            entry = config_result.profiles[profile]
            merged_profiles.append(shlex.split(entry.args))
            exports.update(entry.exports)

        final_args = self.profile_manager.merge_multiple_profiles(
            merged_profiles + [args]
        )
        return final_args, exports


def main() -> ExitCode:
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
