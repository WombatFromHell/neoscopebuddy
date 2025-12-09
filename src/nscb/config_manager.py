"""Configuration management functionality for NeoscopeBuddy."""

from pathlib import Path
from typing import Dict

from .config_result import ConfigResult
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
        """Load configuration from file including both profiles and environment exports."""
        profiles: ConfigData = {}
        exports: EnvExports = {}

        with open(config_file, "r") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue

                # Handle lines without equals signs gracefully
                if "=" not in line:
                    continue

                # Check if this is an export statement
                line = line.strip()
                if line.startswith("export "):
                    # Parse export VAR_NAME=value
                    export_part = line[7:]  # Remove "export " prefix
                    if "=" in export_part:
                        key, value = export_part.split("=", 1)
                        exports[key.strip()] = value.strip().strip("\"'")
                else:
                    # Regular profile definition
                    key, value = line.split("=", 1)
                    profiles[key.strip()] = value.strip().strip("\"'")

        return ConfigResult(profiles, exports)
