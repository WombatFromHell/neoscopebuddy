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


class ExecutableNotFoundError(NscbError):
    """Raised when required executable cannot be found."""

    def __init__(self, executable: str):
        super().__init__(f"Required executable '{executable}' not found in PATH")
        self.executable = executable


class CommandExecutionError(NscbError):
    """Raised when command execution fails."""

    def __init__(self, command: str, exit_code: int, stderr: str = ""):
        message = f"Command execution failed: {command}"
        if exit_code is not None:
            message += f" (exit code: {exit_code})"
        if stderr:
            message += f"\nError output: {stderr}"
        super().__init__(message)
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr


class ArgumentParseError(NscbError):
    """Raised when argument parsing fails."""

    def __init__(self, argument: str, message: str):
        super().__init__(f"Failed to parse argument '{argument}': {message}")
        self.argument = argument


class GamescopeActiveError(NscbError):
    """Raised when gamescope is already active and should not be nested."""

    def __init__(self):
        super().__init__("Gamescope is already active - nesting not allowed")


class EnvironmentVariableError(NscbError):
    """Raised when environment variable handling fails."""

    def __init__(self, var_name: str, message: str):
        super().__init__(f"Environment variable '{var_name}' error: {message}")
        self.var_name = var_name
