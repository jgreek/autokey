"""Configuration management for AutoKey."""

import json
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Handles loading, saving, and migrating AutoKey configuration."""

    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load(self) -> Dict[str, Any]:
        """Load configuration from file, creating default if needed."""
        if not self.config_path.exists() or self.config_path.stat().st_size == 0:
            default_config = self._get_default_config()
            self.save(default_config)
            return default_config

        with open(self.config_path, 'r') as f:
            config = json.load(f)

        migrated_config = self.migrate(config)

        if migrated_config != config:
            print("Migrating config to new format...")
            self.save(migrated_config)

        return migrated_config

    def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)

    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate old config format to new format with descriptions and commands."""
        migrated_config = {}

        for key, value in config.items():
            if isinstance(value, dict) and "commands" in value:
                migrated_config[key] = value
                continue

            if isinstance(value, list):
                migrated_config[key] = {
                    "description": "No description provided",
                    "commands": value
                }

        return migrated_config

    def _get_default_config(self) -> Dict[str, Any]:
        """Return the default configuration."""
        return {
            "aaa": {
                "description": "Open Google Chrome",
                "commands": [
                    {"activate_command": "Google Chrome", "window": "", "delay": 3}
                ]
            },
            "py1": {
                "description": "Run test script",
                "commands": [
                    {
                        "python_command": "/Users/user/venv/bin/python /path/to/script.py -n 5"
                    }
                ]
            }
        }
