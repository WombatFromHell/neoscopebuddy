"""Configuration management functionality for NeoscopeBuddy."""

import re
from pathlib import Path

from .config_result import ConfigResult
from .exceptions import InvalidConfigError
from .path_helper import PathHelper
from .types import ConfigData, EnvExports


class ConfigManager:
    """Manages configuration file loading and management."""

    @staticmethod
    def find_config_file() -> Path | None:
        """Find nscb.conf config file path."""
        return PathHelper.get_config_path()

    @staticmethod
    def load_config(config_file: Path) -> ConfigResult:
        """
        Load configuration from file including both profiles and environment exports.

        Args:
            config_file: Path to the configuration file

        Returns:
            ConfigResult containing profiles and environment exports

        Raises:
            InvalidConfigError: If config file has invalid format or content

        Security:
            - Validates profile names and variable names
            - Sanitizes input to prevent injection
            - Strips quotes from values safely
        """
        profiles: ConfigData = {}
        exports: EnvExports = {}

        # Validate that we're reading a reasonable file size to prevent DoS
        file_size = config_file.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise InvalidConfigError(
                str(config_file), message=f"Config file too large ({file_size} bytes)"
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    ConfigManager._process_config_line(
                        line, line_num, str(config_file), profiles, exports
                    )

        except UnicodeDecodeError as e:
            raise InvalidConfigError(
                str(config_file), message=f"Invalid file encoding: {e}"
            ) from e
        except Exception as e:
            raise InvalidConfigError(
                str(config_file), message=f"Failed to parse config: {e}"
            ) from e

        return ConfigResult(profiles, exports)

    @staticmethod
    def _process_config_line(
        line: str,
        line_num: int,
        config_file: str,
        profiles: ConfigData,
        exports: EnvExports,
    ) -> None:
        """
        Process a single configuration line.

        Args:
            line: The configuration line to process
            line_num: Line number for error reporting
            config_file: Config file path for error reporting
            profiles: Dictionary to store profile configurations
            exports: Dictionary to store environment exports
        """
        # Skip empty lines and comments
        if not line.strip() or line.startswith("#"):
            return

        # Handle lines without equals signs gracefully
        if "=" not in line:
            return

        # Security: Validate line length to prevent excessively long lines
        if len(line) > 10000:  # 10KB line limit
            raise InvalidConfigError(
                config_file,
                line_num,
                f"Line too long ({len(line)} characters)",
            )

        line = line.strip()

        # Route to appropriate handler based on line type
        if line.startswith("export "):
            ConfigManager._process_export_line(line, line_num, config_file, exports)
        else:
            ConfigManager._process_profile_line(line, line_num, config_file, profiles)

    @staticmethod
    def _process_export_line(
        line: str, line_num: int, config_file: str, exports: EnvExports
    ) -> None:
        """
        Process an export configuration line.

        Args:
            line: The export line to process
            line_num: Line number for error reporting
            config_file: Config file path for error reporting
            exports: Dictionary to store environment exports
        """
        # Parse export VAR_NAME=value
        export_part = line[7:]  # Remove "export " prefix
        if "=" not in export_part:
            return

        key, value = export_part.split("=", 1)
        key = key.strip()

        # Security: Validate environment variable name
        if not ConfigManager._is_valid_env_var_name(key):
            raise InvalidConfigError(
                config_file,
                line_num,
                f"Invalid environment variable name: '{key}'",
            )

        # Security: Sanitize value
        try:
            value = ConfigManager._sanitize_config_value(value.strip())
            exports[key] = value
        except InvalidConfigError:
            # Skip malformed values instead of failing completely
            pass

    @staticmethod
    def _process_profile_line(
        line: str, line_num: int, config_file: str, profiles: ConfigData
    ) -> None:
        """
        Process a profile configuration line.

        Args:
            line: The profile line to process
            line_num: Line number for error reporting
            config_file: Config file path for error reporting
            profiles: Dictionary to store profile configurations
        """
        key, value = line.split("=", 1)
        key = ConfigManager._strip_quotes_from_key(key.strip())

        ConfigManager._validate_and_store_profile(
            key, value.strip(), line_num, config_file, profiles
        )

    @staticmethod
    def _strip_quotes_from_key(key: str) -> str:
        """Strip quotes from key if present for backward compatibility."""
        if not key:
            return key

        return ConfigManager._strip_quotes_from_key_if_quoted(key)

    @staticmethod
    def _strip_quotes_from_key_if_quoted(key: str) -> str:
        """Strip quotes from key if it's quoted."""
        if ConfigManager._is_key_quoted(key):
            return key[1:-1].strip()
        return key

    @staticmethod
    def _is_key_quoted(key: str) -> bool:
        """Check if key is quoted with matching quotes."""
        return (key.startswith('"') and key.endswith('"')) or (
            key.startswith("'") and key.endswith("'")
        )

    @staticmethod
    def _validate_and_store_profile(
        key: str, value: str, line_num: int, config_file: str, profiles: ConfigData
    ) -> None:
        """Validate profile name and store if valid."""
        # Security: Validate profile name (allow empty keys for backward compatibility)
        if key and not ConfigManager._is_valid_profile_name(key):
            raise InvalidConfigError(
                config_file,
                line_num,
                f"Invalid profile name: '{key}'",
            )

        ConfigManager._sanitize_and_store_profile_value(key, value, profiles)

    @staticmethod
    def _sanitize_and_store_profile_value(
        key: str, value: str, profiles: ConfigData
    ) -> None:
        """Sanitize value and store in profiles if valid."""
        try:
            sanitized_value = ConfigManager._sanitize_config_value(value)
            if key:  # Only add to profiles if key is not empty
                profiles[key] = sanitized_value
        except InvalidConfigError:
            # Skip malformed values instead of failing completely
            pass

    @staticmethod
    def _is_valid_env_var_name(name: str) -> bool:
        """
        Validate environment variable name for security.

        Args:
            name: Environment variable name to validate

        Returns:
            True if valid, False otherwise

        Security:
            - Only allows alphanumeric characters and underscores
            - Prevents variable names that could cause issues
            - Follows standard environment variable naming conventions
        """
        if not name:
            return False

        # Must start with letter or underscore
        if not (name[0].isalpha() or name[0] == "_"):
            return False

        # Can only contain alphanumeric characters and underscores
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            return False

        # Prevent reserved variable names
        reserved_names = ["PATH", "HOME", "USER", "SHELL", "LD_PRELOAD", "NSCB_"]
        if any(name.startswith(reserved) for reserved in reserved_names):
            return False

        return True

    @staticmethod
    def _is_valid_profile_name(name: str) -> bool:
        """
        Validate profile name for security.

        Args:
            name: Profile name to validate

        Returns:
            True if valid, False otherwise

        Security:
            - Only allows alphanumeric characters, underscores, and hyphens
            - Prevents profile names that could cause issues
            - Follows standard naming conventions
        """
        if not name:
            return False

        # Can only contain alphanumeric characters, underscores, and hyphens
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            return False

        # Prevent reserved profile names
        reserved_names = ["help", "debug", "test", "config", "export", "env"]
        if name.lower() in reserved_names:
            return False

        return True

    @staticmethod
    def _sanitize_config_value(value: str) -> str:
        """
        Sanitize configuration values for security.

        Args:
            value: Configuration value to sanitize

        Returns:
            Sanitized value

        Security:
            - Strips quotes safely
            - Prevents command injection attempts
            - Handles edge cases
        """
        if not value:
            return value

        value = ConfigManager._strip_quotes_from_value(value)
        ConfigManager._check_for_command_injection(value)
        return value

    @staticmethod
    def _strip_quotes_from_value(value: str) -> str:
        """Strip quotes from value if present."""
        if ConfigManager._is_value_quoted(value):
            return value[1:-1]
        return value

    @staticmethod
    def _is_value_quoted(value: str) -> bool:
        """Check if value is quoted with matching quotes."""
        return (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        )

    @staticmethod
    def _check_for_command_injection(value: str) -> None:
        """Check for and prevent command injection attempts."""
        dangerous_patterns = [";", "&&", "||", "`", "$(", "${"]
        for pattern in dangerous_patterns:
            if pattern in value:
                raise InvalidConfigError(
                    "config",
                    message=f"Potential command injection detected in value: '{value}'",
                )
