#!/usr/bin/python3
import os
import sys
import argparse
from pathlib import Path

def find_config_file():
    # Try XDG_CONFIG_HOME first, then fallback to $HOME/.config
    xdg_config_home = os.getenv('XDG_CONFIG_HOME')
    if xdg_config_home:
        config_path = Path(xdg_config_home) / 'nscb.conf'
        if config_path.exists():
            return config_path

    home_dir = os.getenv('HOME', '/')
    home_config_path = Path(home_dir) / '.config' / 'nscb.conf'
    if home_config_path.exists():
        return home_config_path

    return None

def find_gamescope():
    """Check if gamescope is in the system PATH."""
    path_dirs = os.environ['PATH'].split(':')
    for directory in path_dirs:
        gamescope_path = Path(directory) / 'gamescope'
        if gamescope_path.exists() and gamescope_path.is_file() and os.access(gamescope_path, os.X_OK):
            return True
    return False

def load_config(config_file):
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    return config

def main():
    if not find_gamescope():
        print("Error: gamescope not found in PATH or is not executable", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(prog='nscb.py')
    parser.add_argument('-p', '--profile', help='Profile name to use')
    parser.add_argument('app', nargs='?', help='Application to run')
    parser.add_argument('app_args', nargs='*', help='Arguments for the application')

    args = parser.parse_args()

    config_file = find_config_file()
    if not config_file:
        print("Error: Could not find nscb.conf in $XDG_CONFIG_HOME/nscb.conf or $HOME/.config/nscb.conf", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_file)

    profile_args = []
    if args.profile:
        if args.profile in config:
            profile_args = config[args.profile].split()
        else:
            print(f"Error: Profile '{args.profile}' not found in {config_file}", file=sys.stderr)
            sys.exit(1)

    # Build the gamescope command
    gamescope_cmd = ['gamescope'] + profile_args
    if args.app:
        gamescope_cmd.extend(['--', args.app])
        gamescope_cmd.extend(args.app_args)

    print('Executing:', ' '.join(gamescope_cmd))
    os.execvp('gamescope', gamescope_cmd)  # This will replace the current process with gamescope

if __name__ == '__main__':
    main()

