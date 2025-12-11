"""Path operations for NeoscopeBuddy."""

import os
from pathlib import Path


class PathHelper:
    """Utility class for path operations."""

    @staticmethod
    def get_config_path() -> Path | None:
        """Get the path to the config file."""
        # Check XDG_CONFIG_HOME first (standard location)
        if xdg_config_home := os.getenv("XDG_CONFIG_HOME"):
            config_path = Path(xdg_config_home) / "nscb.conf"
            if config_path.exists():
                return config_path

        # Fall back to HOME/.config/nscb.conf
        home = os.getenv("HOME")
        if home:
            config_path = Path(home) / ".config" / "nscb.conf"
            if config_path.exists():
                return config_path

        return None

    @staticmethod
    def executable_exists(name: str) -> bool:
        """Check if executable exists in PATH."""
        path = os.environ.get("PATH", "")
        if not path:
            return False

        for path_dir in path.split(":"):
            if PathHelper._is_valid_path_directory(path_dir):
                if PathHelper._is_executable_in_directory(name, path_dir):
                    return True
        return False

    @staticmethod
    def _is_valid_path_directory(path_dir: str) -> bool:
        """Check if path directory is valid."""
        return path_dir and Path(path_dir).exists() and Path(path_dir).is_dir()

    @staticmethod
    def _is_executable_in_directory(name: str, path_dir: str) -> bool:
        """Check if executable exists in directory and is executable."""
        executable_path = Path(path_dir) / name
        return (
            executable_path.exists()
            and executable_path.is_file()
            and os.access(executable_path, os.X_OK)
        )
