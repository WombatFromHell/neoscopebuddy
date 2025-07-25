#!/usr/bin/python3

import re
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import shlex


def find_config_file() -> Optional[Path]:
    """Find and return the path to nscb.conf configuration file."""
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_path = Path(xdg_config_home) / "nscb.conf"
        if config_path.exists():
            return config_path

    # Fix: Use HOME environment variable correctly for the .config path
    home = os.getenv("HOME")
    if home:
        home_config_path = Path(home) / ".config" / "nscb.conf"
        if home_config_path.exists():
            return home_config_path

    return None


def find_executable(name: str) -> bool:
    """Check if an executable is in the system PATH."""
    path_dirs = os.environ["PATH"].split(":")
    for path_dir in path_dirs:
        executable_path = Path(path_dir) / name
        if (
            executable_path.exists()
            and executable_path.is_file()
            and os.access(executable_path, os.X_OK)
        ):
            return True
    return False


def load_config(config_file: Path) -> Dict[str, str]:
    """Load configuration from file and return as dictionary."""
    config = {}
    with open(config_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes if present
                if len(value) >= 2 and (
                    (value.startswith('"') and value.endswith('"'))
                    or (value.startswith("'") and value.endswith("'"))
                ):
                    value = value[1:-1]

                config[key] = value
    return config


def parse_arguments(args: List[str]) -> Tuple[Optional[str], List[str]]:
    """Parse command line arguments to extract profile and remaining args.
    Returns:
        Tuple of (profile_name, remaining_args)
    """
    profile = None
    remaining_args = []
    i = 0

    while i < len(args):
        arg = args[i]
        if arg == "-p" or arg == "--profile":
            # Next argument should be the profile name
            if i + 1 < len(args):
                profile = args[i + 1]
                i += 2  # Skip both the flag and its value
            else:
                print(f"Error: {arg} requires a value", file=sys.stderr)
                sys.exit(1)
        elif arg.startswith("--profile="):
            # Handle --profile=value format
            profile = arg.split("=", 1)[1]
            i += 1
        else:
            # This argument is not related to profile, pass it through
            remaining_args.append(arg)
            i += 1

    return profile, remaining_args


def merge_arguments(profile_args: List[str], override_args: List[str]) -> List[str]:
    """Merge profile arguments with override arguments.
    Override arguments take precedence over profile arguments for conflicting options.
    """
    if not profile_args:
        return override_args
    if not override_args:
        return profile_args

    # Define which flags take values
    value_flags = {"-W", "-H"}
    # Define mutually exclusive flag groups
    exclusives = [{"--windowed", "-f"}, {"--grab-cursor", "--force-grab-cursor"}]

    # Split at '--'
    def split_dash(args: List[str]) -> Tuple[List[str], List[str]]:
        if "--" in args:
            idx = args.index("--")
            return args[:idx], args[idx:]
        return args, []

    prof_before, prof_after = split_dash(profile_args)
    over_before, over_after = split_dash(override_args)

    # Parse into sequences of flag/value and positionals
    def separate(
        arg_list: List[str],
    ) -> Tuple[List[Tuple[str, Optional[str]]], List[str]]:
        flags_seq: List[Tuple[str, Optional[str]]] = []
        pos_seq: List[str] = []
        i = 0
        while i < len(arg_list):
            arg = arg_list[i]
            if arg.startswith("-"):
                if (
                    arg in value_flags
                    and i + 1 < len(arg_list)
                    and not arg_list[i + 1].startswith("-")
                ):
                    flags_seq.append((arg, arg_list[i + 1]))
                    i += 2
                else:
                    flags_seq.append((arg, None))
                    i += 1
            else:
                pos_seq.append(arg)
                i += 1
        return flags_seq, pos_seq

    p_flags, p_pos = separate(prof_before)
    o_flags, o_pos = separate(over_before)

    # Start with profile flags, then apply overrides
    merged_flags: List[Tuple[str, Optional[str]]] = []
    # Use set to track which flags have been added
    for flag, val in p_flags:
        merged_flags.append((flag, val))

    for flag, val in o_flags:
        # Remove any exclusive-group flags that conflict
        for group in exclusives:
            if flag in group:
                merged_flags = [(f, v) for (f, v) in merged_flags if f not in group]
                break
        # Also remove same flag if present earlier
        merged_flags = [(f, v) for (f, v) in merged_flags if f != flag]
        # Append this override
        merged_flags.append((flag, val))

        # Build final ordered flags: use profile order, then any override-only flags, then any remaining
    # Create a map of merged flags
    merged_map: Dict[str, Optional[str]] = {f: v for f, v in merged_flags}
    ordered_flags: List[Tuple[str, Optional[str]]] = []
    # 1. Flags in profile sequence
    for f, _ in p_flags:
        if f in merged_map:
            ordered_flags.append((f, merged_map.pop(f)))
    # 2. Flags in override sequence that weren't in profile
    for f, _ in o_flags:
        if f in merged_map:
            ordered_flags.append((f, merged_map.pop(f)))
    # 3. Any remaining flags
    for f, v in merged_flags:
        if f in merged_map:
            ordered_flags.append((f, merged_map.pop(f)))

    # Flatten into result
    result: List[str] = []
    for f, v in ordered_flags:
        result.append(f)
        if v is not None:
            result.append(v)
    # Add positionals
    result.extend(p_pos)
    result.extend(o_pos)
    # Add suffix
    if over_after:
        result.extend(over_after)
    else:
        result.extend(prof_after)

    return result


def is_gamescope_active() -> bool:
    """Determine whether the system is already running under an existing gamescope compositor."""

    # Check XDG_CURRENT_DESKTOP == "gamescope"
    if os.environ.get("XDG_CURRENT_DESKTOP", "") == "gamescope":
        return True

    # Check for a process that matches the pattern:
    # steam.sh -.+ -steampal
    try:
        result = subprocess.run(
            ["ps", "ax"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # Ignore errors from ps
            text=True,
            check=False,
        )
        output = result.stdout

        if re.search(r"steam\.sh .+ -steampal", output):
            return True

    except Exception:
        # Ignore errors, assume no such process is running
        pass

    return False


def parse_env_and_command(cmd_line: str) -> Tuple[Dict[str, str], List[str]]:
    """Parse environment variables and command from a command line string."""
    # Use shlex to properly handle quotes
    tokens = shlex.split(cmd_line)

    # Extract environment variables (key=value at the start)
    env_vars = {}
    app_index = 0

    for i, token in enumerate(tokens):
        if "=" in token and not token.startswith(("-", "/")):
            key, value = token.split("=", 1)
            env_vars[key] = value
            app_index = i + 1
        else:
            app_index = i
            break

    # Extract the command part
    command_parts = tokens[app_index:]
    return env_vars, command_parts


def extract_nscb_args(
    command_parts: List[str],
) -> Tuple[Optional[str], List[str], List[str]]:
    """Extract profile, nscb args, and gamescope+app args from command parts.
    Returns:
        Tuple of (profile_name, nscb_args, gamescope_app_args)
    """
    # Find nscb.py and process arguments
    try:
        nscb_index = command_parts.index("nscb.py")
        # Get everything after nscb.py
        remaining_parts = command_parts[nscb_index + 1 :]
    except ValueError:
        # nscb.py not found, treat everything as gamescope+app args
        return None, [], command_parts

    # Parse nscb.py arguments and separate gamescope arguments
    profile = None
    nscb_args = []
    gamescope_app_args = []
    i = 0

    # Process nscb.py reserved arguments
    while i < len(remaining_parts):
        token = remaining_parts[i]

        # Check for reserved nscb.py arguments
        if token in ["-p", "--profile"]:
            # Next argument should be the profile name or value
            if i + 1 < len(remaining_parts):
                profile = remaining_parts[i + 1]
                i += 2  # Skip both the flag and its value
            else:
                print(f"Error: {token} requires a value", file=sys.stderr)
                sys.exit(1)
        elif token.startswith("--profile="):
            # Handle --profile=value format
            profile = token.split("=", 1)[1]
            i += 1
        elif token == "--":
            # Found the separator, everything after this goes to gamescope+app
            gamescope_app_args = remaining_parts[i:]
            break
        else:
            # This is a gamescope argument that should be passed through
            nscb_args.append(token)
            i += 1

    return profile, nscb_args, gamescope_app_args


def build_interpolated_string(cmd_line: str) -> str:
    """Build the interpolated command string from a full command line."""
    # Parse environment variables and command
    env_vars, command_parts = parse_env_and_command(cmd_line)

    # Extract profile and separate arguments
    _, nscb_args, gamescope_app_args = extract_nscb_args(command_parts)

    # Extract specific environment variables
    ldpreload_str = env_vars.get("LD_PRELOAD", "")
    if ldpreload_str:
        ldpreload_str = f"LD_PRELOAD={ldpreload_str}"

    pre_cmd = env_vars.get("NSCB_PRE_CMD", env_vars.get("NSCB_PRECMD", ""))
    post_cmd = env_vars.get("NSCB_POST_CMD", env_vars.get("NSCB_POSTCMD", ""))

    # Build the gamescope command
    # Fix: Preserve the -- separator when building the command
    if gamescope_app_args:
        try:
            separator_index = gamescope_app_args.index("--")
            gamescope_args = gamescope_app_args[:separator_index]
            app_command = gamescope_app_args[separator_index + 1 :]

            # Combine nscb_args and gamescope_args
            combined_gamescope_args = nscb_args + gamescope_args

            if ldpreload_str:
                gamescope_cmd = ["gamescope", "-f"] + combined_gamescope_args
                app_cmd = ["env", ldpreload_str] + app_command
                result = f'{pre_cmd}; env -u LD_PRELOAD {" ".join(gamescope_cmd)} -- {" ".join(app_cmd)}; {post_cmd}'
            else:
                gamescope_cmd = ["gamescope", "-f"] + combined_gamescope_args
                if app_command:
                    result = f'{pre_cmd}; {" ".join(gamescope_cmd)} -- {" ".join(app_command)}; {post_cmd}'
                else:
                    result = f'{pre_cmd}; {" ".join(gamescope_cmd)}; {post_cmd}'
        except ValueError:
            # No -- separator, treat everything as gamescope args
            combined_gamescope_args = nscb_args + gamescope_app_args
            gamescope_cmd = ["gamescope", "-f"] + combined_gamescope_args
            if ldpreload_str:
                result = f'{pre_cmd}; env -u LD_PRELOAD {" ".join(gamescope_cmd)}; {post_cmd}'
            else:
                result = f'{pre_cmd}; {" ".join(gamescope_cmd)}; {post_cmd}'
    else:
        # No gamescope_app_args, just use nscb_args
        gamescope_cmd = ["gamescope", "-f"] + nscb_args
        if ldpreload_str:
            result = (
                f'{pre_cmd}; env -u LD_PRELOAD {" ".join(gamescope_cmd)}; {post_cmd}'
            )
        else:
            result = f'{pre_cmd}; {" ".join(gamescope_cmd)}; {post_cmd}'

    return result.strip("; ")


def main() -> None:
    if not find_executable("gamescope"):
        print(
            "Error: gamescope not found in PATH or is not executable", file=sys.stderr
        )
        sys.exit(1)

    # Skip the script name (sys.argv[0])
    command_args = sys.argv[1:]

    # Parse profile arguments manually
    profile, gamescope_args = parse_arguments(command_args)

    profile_args: List[str] = []
    if profile:
        config_file = find_config_file()
        if not config_file:
            print(
                "Error: Could not find nscb.conf in $XDG_CONFIG_HOME/nscb.conf or $HOME/.config/nscb.conf",
                file=sys.stderr,
            )
            sys.exit(1)

        config = load_config(config_file)

        if profile in config:
            # Use shlex.split to properly handle quoted arguments
            profile_args = shlex.split(config[profile])
        else:
            print(f"Error: Profile '{profile}' not found", file=sys.stderr)
            sys.exit(1)

    # Merge profile args with command line args (command line takes precedence)
    final_args = merge_arguments(profile_args, gamescope_args)

    # Get pre and post commands from environment variables
    pre_cmd = os.environ.get("NSCB_PRE_CMD", os.environ.get("NSCB_PRECMD", ""))
    post_cmd = os.environ.get("NSCB_POST_CMD", os.environ.get("NSCB_POSTCMD", ""))

    # Build the final command parts properly
    if not is_gamescope_active():
        gamescope_cmd = ["gamescope"] + final_args
        gamescope_str = " ".join(shlex.quote(arg) for arg in gamescope_cmd)

        # Build full command with pre/post commands
        command_parts = []
        if pre_cmd.strip():
            command_parts.append(pre_cmd.strip())
        command_parts.append(gamescope_str)
        if post_cmd.strip():
            command_parts.append(post_cmd.strip())

        full_command = "; ".join(command_parts)
    else:
        # Extract the application to run (after '--')
        try:
            dash_index = final_args.index("--")
            app_args = final_args[dash_index + 1 :]
        except ValueError:
            app_args = []

        # Construct the command that runs the application directly, with pre/post commands
        command_parts = []
        if pre_cmd.strip():
            command_parts.append(pre_cmd.strip())
        if app_args:
            app_str = " ".join(shlex.quote(arg) for arg in app_args)
            command_parts.append(app_str)
        if post_cmd.strip():
            command_parts.append(post_cmd.strip())

        full_command = "; ".join(command_parts) if command_parts else ""

    print("Executing:", full_command)
    if full_command:
        os.system(full_command)


if __name__ == "__main__":
    main()
