"""Path operations for NeoscopeBuddy."""

import os
import shutil
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
        return shutil.which(name) is not None
