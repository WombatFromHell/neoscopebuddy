#!/usr/bin/env python3
"""Main application orchestrator for NeoscopeBuddy."""

import logging
import sys
from typing import Optional

from .command_executor import CommandExecutor
from .config_manager import ConfigManager
from .exceptions import NscbError
from .profile_manager import ProfileManager
from .system_detector import SystemDetector
from .types import ArgsList, EnvExports, ExitCode


def debug_log(message: str) -> None:
    """Log debug message when NSCB_DEBUG=1 is set."""
    import os

    if os.environ.get("NSCB_DEBUG", "").lower() in ("1", "true", "yes", "on"):
        print(f"[DEBUG] {message}", file=sys.stderr, flush=True)


def print_help() -> None:
    """Print concise help message about nscb functionality."""
    help_text = """neoscopebuddy - gamescope wrapper
Usage:
  nscb.pyz -p fullscreen -- /bin/mygame                 # Single profile
  nscb.pyz --profiles=profile1,profile2 -- /bin/mygame  # Multiple profiles
  nscb.pyz -p profile1 -p profile2 -- /bin/mygame       # Multiple profiles
  nscb.pyz -p profile1 -W 3140 -H 2160 -- /bin/mygame   # Profile with overrides

  Config file: $XDG_CONFIG_HOME/nscb.conf or $HOME/.config/nscb.conf
  Config format: KEY=VALUE (e.g., "fullscreen=-f")
  Supports NSCB_PRE_CMD=.../NSCB_POST_CMD=... environment hooks
"""
    print(help_text)


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
            from .exceptions import ConfigNotFoundError

            raise ConfigNotFoundError("could not find nscb.conf")

        config_result = self.config_manager.load_config(config_file)
        merged_profiles = []

        for profile in profiles:
            if profile not in config_result.profiles:
                from .exceptions import ProfileNotFoundError

                raise ProfileNotFoundError(f"profile {profile} not found")
            import shlex

            merged_profiles.append(shlex.split(config_result.profiles[profile]))

        final_args = self.profile_manager.merge_multiple_profiles(
            merged_profiles + [args]
        )
        return final_args, config_result.exports


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
