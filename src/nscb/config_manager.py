"""Configuration management functionality for NeoscopeBuddy."""

import re
from pathlib import Path

from .config_result import ConfigResult, ProfileEntry
from .exceptions import InvalidConfigError
from .path_helper import PathHelper
from .types import EnvExports


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

        Supports optional [profile] section headers. Lines before any section
        are global; lines inside a section are scoped to that profile.

        Args:
            config_file: Path to the configuration file

        Returns:
            ConfigResult containing profiles and environment exports

        Raises:
            InvalidConfigError: If config file has invalid format or content

        Security:
            - Validates profile names and variable names
            - Strips quotes from values safely
        """
        profiles: dict[str, ProfileEntry] = {}
        exports: EnvExports = {}
        current: str | None = None

        file_size = config_file.stat().st_size
        if file_size > 10 * 1024 * 1024:
            raise InvalidConfigError(
                str(config_file), message=f"Config file too large ({file_size} bytes)"
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if len(line) > 10000:
                        raise InvalidConfigError(
                            str(config_file),
                            line_num,
                            f"Line too long ({len(line)} characters)",
                        )

                    if m := re.fullmatch(r"\[([^\]]+)\]", line):
                        name = ConfigManager._strip_quotes(m.group(1).strip())
                        if not ConfigManager._is_valid_profile_name(name):
                            raise InvalidConfigError(
                                str(config_file),
                                line_num,
                                f"Invalid profile name: '{name}'",
                            )
                        profiles.setdefault(name, ProfileEntry(args=""))
                        current = name
                        continue

                    if line.startswith("export "):
                        target = profiles[current].exports if current else exports
                        ConfigManager._process_export_line(
                            line, line_num, str(config_file), target
                        )
                        continue

                    if line.startswith("gamescope_condition=") and current:
                        profiles[current].gamescope_condition = line[
                            len("gamescope_condition=") :
                        ]
                        continue

                    if current:
                        profiles[current].args = ConfigManager._strip_quotes(line)
                    elif "=" in line:
                        ConfigManager._process_profile_line(
                            line, line_num, str(config_file), profiles
                        )

        except UnicodeDecodeError as e:
            raise InvalidConfigError(
                str(config_file), message=f"Invalid file encoding: {e}"
            ) from e
        except InvalidConfigError:
            raise
        except Exception as e:
            raise InvalidConfigError(
                str(config_file), message=f"Failed to parse config: {e}"
            ) from e

        return ConfigResult(profiles, exports)

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

        value = ConfigManager._strip_quotes(value.strip())
        exports[key] = value

    @staticmethod
    def _process_profile_line(
        line: str, line_num: int, config_file: str, profiles: dict[str, ProfileEntry]
    ) -> None:
        """
        Process a legacy name=args profile line.

        Args:
            line: The configuration line to process
            line_num: Line number for error reporting
            config_file: Config file path for error reporting
            profiles: Dictionary to store profile configurations
        """
        key, value = line.split("=", 1)
        key = ConfigManager._strip_quotes(key.strip())

        ConfigManager._validate_and_store_profile(
            key, value.strip(), line_num, config_file, profiles
        )

    @staticmethod
    def _strip_quotes(value: str) -> str:
        """Strip one layer of matching " or ' quotes if present."""
        if len(value) >= 2 and (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            return value[1:-1]
        return value

    @staticmethod
    def _validate_and_store_profile(
        key: str,
        value: str,
        line_num: int,
        config_file: str,
        profiles: dict[str, ProfileEntry],
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
        key: str, value: str, profiles: dict[str, ProfileEntry]
    ) -> None:
        """Sanitize value and store in profiles if valid."""
        sanitized_value = ConfigManager._strip_quotes(value)
        if key:
            profiles[key] = ProfileEntry(args=sanitized_value)

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
        # Alphanumeric + underscore, must start with a letter or underscore
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
            return False

        # Prevent reserved variable names
        exact_reserved = {"PATH", "HOME", "USER", "SHELL", "LD_PRELOAD"}
        if name in exact_reserved or name.startswith("NSCB_"):
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
        reserved_names = ["help", "export"]
        if name.lower() in reserved_names:
            return False

        return True


