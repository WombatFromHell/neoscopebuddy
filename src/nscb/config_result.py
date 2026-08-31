"""Config result container for NeoscopeBuddy."""

from dataclasses import dataclass, field


@dataclass
class ProfileEntry:
    """A profile's args and per-profile environment exports."""

    args: str
    exports: dict[str, str] = field(default_factory=dict)
    gamescope_condition: str | None = None


@dataclass
class ConfigResult:
    """Class to hold both profile configurations and environment exports."""

    profiles: dict[str, ProfileEntry]
    exports: dict[str, str]
