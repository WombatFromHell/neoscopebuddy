"""Config result container for NeoscopeBuddy."""

from dataclasses import dataclass, field

from .types import EnvExports


@dataclass
class ProfileEntry:
    """A profile's args and per-profile environment exports."""

    args: str
    exports: EnvExports = field(default_factory=dict)
    gamescope_condition: str | None = None


@dataclass
class ConfigResult:
    """Class to hold both profile configurations and environment exports."""

    profiles: dict[str, ProfileEntry]
    exports: EnvExports
