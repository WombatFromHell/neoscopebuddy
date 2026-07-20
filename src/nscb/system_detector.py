"""System detection functionality for NeoscopeBuddy."""

from .environment_helper import EnvironmentHelper
from .path_helper import PathHelper


# ponytail: thin pass-through; exists as a mock seam for tests that need to
# stub find_executable / is_gamescope_active without patching PathHelper or
# EnvironmentHelper directly.
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
