"""System detection functionality for NeoscopeBuddy."""

from .environment_helper import EnvironmentHelper
from .path_helper import PathHelper


class SystemDetector:
    """Handles environment detection functionality."""

    @staticmethod
    def find_executable(name: str) -> bool:
        """Check if executable exists in PATH."""
        return PathHelper.executable_exists(name)

    @staticmethod
    def is_gamescope_active() -> bool:
        """Determine if system runs under gamescope."""
        return EnvironmentHelper.is_gamescope_active()
