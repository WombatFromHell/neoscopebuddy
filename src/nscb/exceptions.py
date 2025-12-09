"""Custom exceptions for NeoscopeBuddy."""


class NscbError(Exception):
    """Base exception for nscb errors."""

    pass


class ConfigNotFoundError(NscbError):
    """Raised when config file cannot be found."""

    pass


class ProfileNotFoundError(NscbError):
    """Raised when a specified profile is not found in config."""

    pass
