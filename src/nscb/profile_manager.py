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
    def parse_profile_args(args: ArgsList) -> tuple[list[str], list[str]]:
        """Extract profiles and remaining args from command line."""
        profiles: list[str] = []
        rest: list[str] = []
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
    def merge_arguments(profile_args: ArgsList, override_args: ArgsList) -> list[str]:
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
    def _process_args_before_separator(
        profile_args: ArgsList, override_args: ArgsList
    ) -> tuple[list[FlagTuple], ArgsList, list[FlagTuple], ArgsList]:
        """
        Process the arguments before the '--' separator to separate flags and positionals.
        """
        from .argument_processor import ArgumentProcessor

        p_before, o_before = (
            ArgumentProcessor.split_at_separator(profile_args)[0],
            ArgumentProcessor.split_at_separator(override_args)[0],
        )

        # Separate flags and positionals
        p_flags, p_pos = ArgumentProcessor.separate_flags_and_positionals(p_before)
        o_flags, o_pos = ArgumentProcessor.separate_flags_and_positionals(o_before)

        return p_flags, p_pos, o_flags, o_pos

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

        # Classify flags into conflict and non-conflict categories
        profile_conflicts, profile_nonconflicts = (
            ProfileManager._classify_flags_by_conflict(
                profile_flags, conflict_canon_set
            )
        )
        override_conflicts, override_nonconflicts = (
            ProfileManager._classify_flags_by_conflict(
                override_flags, conflict_canon_set
            )
        )

        # Resolve conflicts - override flags take precedence
        final_conflicts = ProfileManager._resolve_conflicts(
            profile_conflicts, override_conflicts
        )

        # Handle non-conflicts - remove conflicting flags from profile if overridden
        final_nonconflicts = ProfileManager._handle_non_conflicts(
            profile_nonconflicts, override_nonconflicts
        )

        # Combine all flags
        return final_conflicts + final_nonconflicts

    @staticmethod
    def _classify_flags_by_conflict(
        flags: list[FlagTuple], conflict_canon_set: set[str]
    ) -> tuple[list[FlagTuple], list[FlagTuple]]:
        """Classify flags into conflict and non-conflict lists."""
        conflicts = [
            f for f in flags if ProfileManager._canon(f[0]) in conflict_canon_set
        ]
        nonconflicts = [
            f for f in flags if ProfileManager._canon(f[0]) not in conflict_canon_set
        ]
        return conflicts, nonconflicts

    @staticmethod
    def _resolve_conflicts(
        profile_conflicts: list[FlagTuple], override_conflicts: list[FlagTuple]
    ) -> list[FlagTuple]:
        """Resolve conflicting flags - override flags take precedence."""
        return override_conflicts if override_conflicts else profile_conflicts

    @staticmethod
    def _handle_non_conflicts(
        profile_nonconflicts: list[FlagTuple], override_nonconflicts: list[FlagTuple]
    ) -> list[FlagTuple]:
        """Handle non-conflicting flags - remove profile flags if overridden."""
        # Get canonical forms of override flags to check for duplicates
        override_canon_set = {
            ProfileManager._canon(f[0]) for f in override_nonconflicts
        }
        # Keep only profile non-conflicts that aren't overridden
        remaining_profile_nonconflicts = [
            f
            for f in profile_nonconflicts
            if ProfileManager._canon(f[0]) not in override_canon_set
        ]
        return remaining_profile_nonconflicts + override_nonconflicts

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
    def merge_multiple_profiles(profile_args_list: ProfileArgsList) -> list[str]:
        """Merge multiple profile argument lists."""
        if not profile_args_list:
            return []
        if len(profile_args_list) == 1:
            return profile_args_list[0]
        return reduce(ProfileManager.merge_arguments, profile_args_list)
