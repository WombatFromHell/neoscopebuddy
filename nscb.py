#!/usr/bin/python3

import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple

def find_config_file() -> Optional[Path]:
    """Find and return the path to nscb.conf configuration file."""
    xdg_config_home = os.getenv('XDG_CONFIG_HOME')
    if xdg_config_home:
        config_path = Path(xdg_config_home) / 'nscb.conf'
        if config_path.exists():
            return config_path

    home_config_path = Path(os.getenv('HOME', '/')) / '.config' / 'nscb.conf'
    if home_config_path.exists():
        return home_config_path

    return None

def find_executable(name: str) -> bool:
    """Check if an executable is in the system PATH."""
    path_dirs = os.environ['PATH'].split(':')
    for path_dir in path_dirs:
        executable_path = Path(path_dir) / name
        if executable_path.exists() and executable_path.is_file() and os.access(executable_path, os.X_OK):
            return True
    return False

def load_config(config_file: Path) -> Dict[str, str]:
    """Load configuration from file and return as dictionary."""
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes if present
                if len(value) >= 2 and ((value.startswith('"') and value.endswith('"')) or 
                                       (value.startswith("'") and value.endswith("'"))):
                    value = value[1:-1]

                config[key] = value
    return config

def parse_profile_args(args: List[str]) -> Tuple[Optional[str], List[str]]:
    """Parse command line arguments to extract profile and remaining args.
    Returns:
        Tuple of (profile_name, remaining_args)
    """
    profile = None
    remaining_args = []
    i = 0

    while i < len(args):
        arg = args[i]
        if arg == '-p' or arg == '--profile':
            # Next argument should be the profile name
            if i + 1 < len(args):
                profile = args[i + 1]
                i += 2  # Skip both the flag and its value
            else:
                print(f"Error: {arg} requires a value", file=sys.stderr)
                sys.exit(1)
        elif arg.startswith('--profile='):
            # Handle --profile=value format
            profile = arg.split('=', 1)[1]
            i += 1
        else:
            # This argument is not related to profile, pass it through
            remaining_args.append(arg)
            i += 1

    return profile, remaining_args

def main() -> None:
    if not find_executable('gamescope'):
        print("Error: gamescope not found in PATH or is not executable", file=sys.stderr)
        sys.exit(1)

    # Skip the script name (sys.argv[0])
    command_args = sys.argv[1:]
    # Parse profile arguments manually
    profile, gamescope_args = parse_profile_args(command_args)

    profile_args = []
    if profile:
        # Only require config file if a profile is specified
        config_file = find_config_file()
        if not config_file:
            print("Error: Could not find nscb.conf in $XDG_CONFIG_HOME/nscb.conf or $HOME/.config/nscb.conf", file=sys.stderr)
            sys.exit(1)

        config = load_config(config_file)

        if profile in config:
            profile_args = config[profile].split()
        else:
            # Treat as literal gamescope args if it contains spaces
            if ' ' in profile:
                profile_args = profile.split()
            else:
                print(f"Error: Profile '{profile}' not found", file=sys.stderr)
                sys.exit(1)

    # Combine profile args and the remaining args from the command line
    gamescope_cmd = ['gamescope'] + profile_args + gamescope_args

    print('Executing:', ' '.join(gamescope_cmd))
    os.execvp('gamescope', gamescope_cmd[1:])

if __name__ == '__main__':
    main()
