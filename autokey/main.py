"""Main AutoKey orchestrator."""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from .dock import DockReader
from .history import HistoryTracker
from .display import CheatSheetPrinter
from .executor import CommandExecutor
from .listener import KeyboardListener


class AutoKey:
    """Main AutoKey application that wires all components together."""

    def __init__(self, config_path: str):
        self.script_dir = Path(__file__).resolve().parent.parent
        self.config_path = self.script_dir / config_path

        self.config_manager = ConfigManager(self.config_path)
        self.config = self.config_manager.load()

        self.dock_reader = DockReader()
        self.dock_apps = self.dock_reader.get_apps()

        self.history_tracker = HistoryTracker(
            self.script_dir / 'data' / 'triplet_history.csv'
        )

        self.display = CheatSheetPrinter(self.config, self.dock_apps)
        self.executor = CommandExecutor(
            cooldown=5.0,
            on_error=self.display.print_cheat_sheet
        )

        self.listener = KeyboardListener(
            on_triplet=self._handle_triplet,
            on_function_key=self._handle_function_key,
            on_cmd_number=self._handle_cmd_number
        )

    def _handle_triplet(self, pattern: str) -> None:
        """Handle a detected triplet pattern."""
        if pattern in self.config:
            self.listener.undo_triplet()
            if self.executor.execute(self.config[pattern]):
                description = self.display.get_description(pattern, self.config[pattern])
                self.history_tracker.update(pattern, description)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] {pattern} {description}")

    def _handle_function_key(self, key_name: str) -> None:
        """Handle a function key press."""
        if key_name in self.config:
            self.executor.execute(self.config[key_name])
        else:
            f_num = int(key_name[1:])
            if f_num <= len(self.dock_apps):
                app_name = self.dock_apps[f_num - 1]
                self.executor.activate_app(app_name)

    def _handle_cmd_number(self, command_key: str) -> None:
        """Handle a Command + number shortcut."""
        if command_key in self.config:
            self.executor.execute(self.config[command_key])
            print("\nCommand executed. Refreshing cheatsheet...")
            self.display.print_cheat_sheet()

    def run(self) -> None:
        """Start the AutoKey listener."""
        self.display.print_cheat_sheet()
        self.listener.start()


def main():
    """Entry point for the AutoKey application."""
    parser = argparse.ArgumentParser(description="AutoKey: Keyboard shortcut listener")
    parser.add_argument('--config', default='config.json', help='Path to the configuration file')
    args = parser.parse_args()

    auto_key = AutoKey(args.config)
    auto_key.run()


if __name__ == "__main__":
    main()
