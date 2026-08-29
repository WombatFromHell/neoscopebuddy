"""Custom exceptions for NeoscopeBuddy."""


class NscbError(Exception):
    """Base exception for nscb errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ConfigNotFoundError(NscbError):
    """Raised when config file cannot be found."""

    def __init__(self, path: str | None = None):
        message = f"Config file not found{': ' + path if path else ''}"
        super().__init__(message)
        self.path = path


class ProfileNotFoundError(NscbError):
    """Raised when a specified profile is not found in config."""

    def __init__(self, profile_name: str, config_path: str | None = None):
        message = f"Profile '{profile_name}' not found"
        if config_path:
            message += f" in {config_path}"
        super().__init__(message)
        self.profile_name = profile_name
        self.config_path = config_path


class InvalidConfigError(NscbError):
    """Raised when config file has invalid format or content."""

    def __init__(
        self,
        path: str,
        line_num: int | None = None,
        message: str = "Invalid config format",
    ):
        full_message = f"Invalid config in {path}"
        if line_num:
            full_message += f" at line {line_num}"
        full_message += f": {message}"
        super().__init__(full_message)
        self.path = path
        self.line_num = line_num
