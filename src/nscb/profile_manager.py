"""Profile management functionality for NeoscopeBuddy."""

import shlex
from functools import reduce
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .argument_processor import ArgumentProcessor

from .gamescope_args import GAMESCOPE_ARGS_MAP
from .types import ArgsList, FlagTuple, ProfileArgsList


class ProfileManager:
    """Manages profile parsing and merging functionality."""

    @staticmethod
    def parse_profile_args(args: ArgsList) -> tuple[ArgsList, ArgsList]:
        """Extract profiles and remaining args from command line."""
        profiles, rest = [], []
        i = 0
        while i < len(args):
            arg = args[i]
            # Handle --profiles=profile1,profile2,...
            if arg.startswith("--profiles="):
                profile_list = arg[len("--profiles=") :].split(",")
                for p in profile_list:
                    if p.strip():
                        profiles.append(p.strip())
                i += 1
                continue
            # Handle -p and --profile (existing logic)
            if arg in ("-p", "--profile"):
                if i + 1 >= len(args):
                    raise ValueError(f"{arg} requires value")
                profiles.append(args[i + 1])  # Fixed: was "forms" before
                i += 2
                continue
            elif arg.startswith("--profile="):
                profile_name = arg.split("=", 1)[1]
                profiles.append(profile_name)
                i += 1
                continue

            rest.append(arg)
            i += 1
        return profiles, rest

    @staticmethod
    def merge_arguments(profile_args: ArgsList, override_args: ArgsList) -> ArgsList:
        """
        Merge a profile argument list with an override argument list.

        Override flags take precedence over profile flags.
        Display mode conflicts (-f/--fullscreen vs --borderless) are mutually exclusive.
        """
        # Split arguments at the '--' separator
        # Import here to avoid circular import
        from .argument_processor import ArgumentProcessor

        (p_before, _), (o_before, o_after) = (
            ArgumentProcessor.split_at_separator(profile_args),
            ArgumentProcessor.split_at_separator(override_args),
        )

        # Separate flags and positionals
        p_flags, p_pos = ArgumentProcessor.separate_flags_and_positionals(p_before)
        o_flags, o_pos = ArgumentProcessor.separate_flags_and_positionals(o_before)

        # Process flags
        final_flags = ProfileManager._merge_flags(p_flags, o_flags)

        # Convert to flat argument sequence
        result = ProfileManager._flags_to_args_list(final_flags)

        return result + p_pos + o_pos + o_after

    @staticmethod
    def _merge_flags(
        profile_flags: list[FlagTuple], override_flags: list[FlagTuple]
    ) -> list[FlagTuple]:
        """Merge profile and override flags with proper conflict resolution."""
        # Define conflict set
        conflict_canon_set = {
            ProfileManager._canon("-f"),  # fullscreen
            ProfileManager._canon("-b"),  # borderless
        }

        # Classify flags
        profile_conflicts = [
            f
            for f in profile_flags
            if ProfileManager._canon(f[0]) in conflict_canon_set
        ]
        profile_nonconflicts = [
            f
            for f in profile_flags
            if ProfileManager._canon(f[0]) not in conflict_canon_set
        ]
        override_conflicts = [
            f
            for f in override_flags
            if ProfileManager._canon(f[0]) in conflict_canon_set
        ]
        override_nonconflicts = [
            f
            for f in override_flags
            if ProfileManager._canon(f[0]) not in conflict_canon_set
        ]

        # Resolve conflicts
        final_conflicts = (
            override_conflicts if override_conflicts else profile_conflicts
        )

        # Handle non-conflicts
        override_canon_set = {
            ProfileManager._canon(f[0]) for f in override_nonconflicts
        }
        remaining_profile_nonconflicts = [
            f
            for f in profile_nonconflicts
            if ProfileManager._canon(f[0]) not in override_canon_set
        ]

        # Combine all flags
        return final_conflicts + remaining_profile_nonconflicts + override_nonconflicts

    @staticmethod
    def _canon(flag: str) -> str:
        """Convert flag to canonical form."""
        return GAMESCOPE_ARGS_MAP.get(flag, flag)

    @staticmethod
    def _flags_to_args_list(flags: list[FlagTuple]) -> ArgsList:
        """Convert flag tuples to flat argument list."""
        result = []
        for flag, val in flags:
            result.append(flag)
            if val is not None:
                result.append(val)
        return result

    @staticmethod
    def merge_multiple_profiles(profile_args_list: ProfileArgsList) -> ArgsList:
        """Merge multiple profile argument lists."""
        if not profile_args_list:
            return []
        if len(profile_args_list) == 1:
            return profile_args_list[0]
        return reduce(ProfileManager.merge_arguments, profile_args_list)
