"""Cheat sheet display for AutoKey."""

from typing import Dict, List, Any


class CheatSheetPrinter:
    """Prints the AutoKey cheat sheet to the console."""

    def __init__(self, config: Dict[str, Any], dock_apps: List[str]):
        self.config = config
        self.dock_apps = dock_apps

    def print_cheat_sheet(self) -> None:
        """Print the full cheat sheet to the console."""
        print("\n" + "=" * 60)
        print("AutoKey Cheat Sheet".center(60))
        print("=" * 60)

        self._print_triplet_commands()
        self._print_function_key_commands()
        self._print_cmd_number_shortcuts()
        self._print_dock_commands()

        print("\n" + "=" * 60)

    def _print_triplet_commands(self) -> None:
        """Print triplet command section."""
        print("\nTriplet Commands:")
        print("-" * 60)
        for key, commands in self.config.items():
            if len(key) == 3:
                desc = self.get_description(key, commands)
                print(f"{key:<10} {desc}")

    def _print_function_key_commands(self) -> None:
        """Print function key command section."""
        print("\nFunction Key Commands:")
        print("-" * 60)
        for key, commands in self.config.items():
            if key.startswith('f') and key[1:].isdigit():
                desc = self.get_description(key, commands)
                print(f"{key.upper():<10} {desc}")

    def _print_cmd_number_shortcuts(self) -> None:
        """Print Command + number shortcuts section."""
        print("\nCommand + Number Shortcuts:")
        print("-" * 60)
        for key, commands in self.config.items():
            if key.startswith('cmd+'):
                desc = self.get_description(key, commands)
                print(f"{key:<10} {desc}")

    def _print_dock_commands(self) -> None:
        """Print dock commands section."""
        print("\nDock Commands (Function Keys):")
        print("-" * 60)
        for i, app in enumerate(self.dock_apps, 1):
            if i <= 12:
                print(f"F{i:<9} Activate {app}")

    def get_description(self, key: str, command_config: Any) -> str:
        """Get a human-readable description for a command."""
        if isinstance(command_config, list):
            command = command_config[0]
            if 'activate_command' in command:
                return f"Activate {command['activate_command']}"
            elif 'iterm_command' in command:
                return f"iTerm: {command['iterm_command'][:30]}..."
            elif 'python_command' in command:
                return f"Python: {command['python_command']}"
            elif 'url' in command:
                browser = command.get('browser', 'default')
                return f"URL: {command['url']} ({browser})"
            return "Unknown command"

        if "commands" in command_config:
            commands = command_config["commands"]
            if commands and 'url' in commands[0]:
                browser = commands[0].get('browser', 'default')
                return f"{command_config.get('description', 'URL')} ({browser})"

        return command_config.get("description", "No description provided")
