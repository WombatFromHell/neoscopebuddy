"""Config result container for NeoscopeBuddy."""

from typing import Dict

from .types import ConfigData, EnvExports


class ConfigResult:
    """Class to hold both profile configurations and environment exports."""

    def __init__(self, profiles: ConfigData, exports: EnvExports):
        self.profiles = profiles
        self.exports = exports

    def __contains__(self, key):
        """Allow checking if a profile exists using 'in' operator."""
        return key in self.profiles

    def __getitem__(self, key):
        """Allow dictionary-style access to profiles."""
        return self.profiles[key]

    def __eq__(self, other):
        """Allow comparison with dictionary (for backward compatibility with tests)."""
        if isinstance(other, dict):
            return self.profiles == other
        return super().__eq__(other)

    def get(self, key, default=None):
        """Allow .get() method access to profiles."""
        return self.profiles.get(key, default)

    def keys(self):
        """Allow access to profile keys."""
        return self.profiles.keys()

    def values(self):
        """Allow access to profile values."""
        return self.profiles.values()

    def items(self):
        """Allow access to profile items."""
        return self.profiles.items()
