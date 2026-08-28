"""Profile management functionality for NeoscopeBuddy."""

from functools import reduce
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .argument_processor import ArgumentProcessor  # noqa: F401

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
            # Handle -p and --profile (supports comma-separated values)
            if arg in ("-p", "--profile"):
                if i + 1 >= len(args):
                    raise ValueError(f"{arg} requires value")
                profile_list = args[i + 1].split(",")
                for p in profile_list:
                    if p.strip():
                        profiles.append(p.strip())
                i += 2
                continue
            elif arg.startswith("--profile="):
                profile_list = arg.split("=", 1)[1].split(",")
                for p in profile_list:
                    if p.strip():
                        profiles.append(p.strip())
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

        (p_before, _), (o_before, o_app) = (
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

        return result + p_pos + o_pos + (["--", *o_app] if o_app else [])

    @staticmethod
    def _merge_flags(
        profile_flags: list[FlagTuple], override_flags: list[FlagTuple]
    ) -> list[FlagTuple]:
        """Merge profile and override flags; override wins on conflicts."""
        conflict_canon_set = {
            ProfileManager._canon("-f"),  # fullscreen
            ProfileManager._canon("-b"),  # borderless
            ProfileManager._canon("--backend"),
        }
        profile_conflicts, profile_nonconflicts = (
            ProfileManager._classify_flags_by_conflict(profile_flags, conflict_canon_set)
        )
        override_conflicts, override_nonconflicts = (
            ProfileManager._classify_flags_by_conflict(override_flags, conflict_canon_set)
        )
        # Conflicts: override takes precedence
        final_conflicts = override_conflicts if override_conflicts else profile_conflicts
        # Non-conflicts: drop profile flags the override also set
        override_canon_set = {ProfileManager._canon(f[0]) for f in override_nonconflicts}
        final_nonconflicts = [
            f
            for f in profile_nonconflicts
            if ProfileManager._canon(f[0]) not in override_canon_set
        ] + override_nonconflicts
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
    def _canon(flag: str) -> str:
        """Convert flag to canonical form."""
        name, _, _ = flag.partition("=")
        return GAMESCOPE_ARGS_MAP.get(name, name)

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
