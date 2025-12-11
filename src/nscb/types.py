"""
Type aliases for NeoscopeBuddy.

This module provides centralized type definitions used throughout the application
to ensure consistency and maintainability.

Type Aliases:
    ArgsList: List of string arguments
    FlagTuple: Tuple representing a flag and its optional value
    ProfileArgs: Dictionary mapping profile names to arguments
    ConfigData: Dictionary representing configuration data
    EnvExports: Dictionary mapping environment variable names to values
    ExitCode: Integer representing exit codes
    ProfileArgsList: List of argument lists for multiple profiles
    CommandTuple: Tuple of two string commands (pre/post commands)
    ArgsPair: Tuple of two argument lists (before/after separator)
    FlagClassification: Tuple of conflict and non-conflict flags
    ProcessedArgs: Tuple of flags and positional arguments
"""

from typing import Dict, List, Optional, Tuple

# Common type aliases used throughout the application
ArgsList = List[str]
"""List of string arguments used for command-line arguments and profiles."""

FlagTuple = Tuple[str, Optional[str]]
"""Tuple representing a flag and its optional value (e.g., ('-f', None) or ('-W', '1920'))."""

ProfileArgs = Dict[str, str]
"""Dictionary mapping profile names to their argument strings."""

ConfigData = Dict[str, str]
"""Dictionary representing configuration data with string keys and values."""

EnvExports = Dict[str, str]
"""Dictionary mapping environment variable names to their values."""

ExitCode = int
"""Integer representing process exit codes (0 for success, non-zero for errors)."""

ProfileArgsList = List[ArgsList]
"""List of argument lists used for merging multiple profiles."""

# Tuple type aliases for common patterns
CommandTuple = Tuple[str, str]
"""Tuple representing pre and post command strings (e.g., ('pre_cmd', 'post_cmd'))."""

ArgsPair = Tuple[ArgsList, ArgsList]
"""Tuple representing arguments before and after separator (e.g., (gamescope_args, app_args))."""

FlagClassification = Tuple[List[FlagTuple], List[FlagTuple]]
"""Tuple representing classified flags (conflict_flags, non_conflict_flags)."""

ProcessedArgs = Tuple[List[FlagTuple], ArgsList]
"""Tuple representing processed arguments (flags, positionals)."""

# Type aliases for method return types
SplitResult = Tuple[ArgsList, ArgsList]
"""Result of splitting arguments at separator (before, after)."""

SeparatedArgs = Tuple[List[FlagTuple], ArgsList]
"""Result of separating flags and positionals (flags, positionals)."""

MergeResult = Tuple[List[FlagTuple], ArgsList, List[FlagTuple], ArgsList]
"""Result of processing arguments before separator (p_flags, p_pos, o_flags, o_pos)."""
