import os
import plistlib
import json
import time
import argparse
import subprocess
from pathlib import Path
import shlex as shlex_module
from pynput import keyboard
import csv
from datetime import datetime


class AutoKey:
    def __init__(self, config_path):
        self.script_dir = Path(__file__).resolve().parent
        self.config_path = self.script_dir / config_path
        self.config = self.load_config()
        self.current_keys = set()
        self.last_three_keys = []
        self.last_execution_time = 0
        self.cooldown_period = 5.0  # 5 second cooldown
        self.keyboard_controller = keyboard.Controller()
        self.dock_apps = []
        self.triplet_history_path = self.script_dir / 'data' / 'triplet_history.csv'

    def migrate_config(self, config):
        """Migrate old config format to new format with descriptions and commands."""
        migrated_config = {}

        for key, value in config.items():
            # Check if it's already in the new format
            if isinstance(value, dict) and "commands" in value:
                migrated_config[key] = value
                continue

            # If it's in the old format (array of commands)
            if isinstance(value, list):
                # Create new structure with empty description
                migrated_config[key] = {
                    "description": "No description provided",
                    "commands": value
                }

        return migrated_config

    def load_config(self):
        if not self.config_path.exists() or self.config_path.stat().st_size == 0:
            default_config = {
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
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config

        with open(self.config_path, 'r') as f:
            config = json.load(f)

        # Migrate the config if needed
        migrated_config = self.migrate_config(config)

        # If the config was migrated (different from original), save it back
        if migrated_config != config:
            print("Migrating config to new format...")
            with open(self.config_path, 'w') as f:
                json.dump(migrated_config, f, indent=2)

        return migrated_config

    def get_dock_apps(self):
        dock_plist_path = os.path.expanduser("~/Library/Preferences/com.apple.dock.plist")
        try:
            # Use plutil to convert binary plist to XML
            xml_plist = subprocess.run(['plutil', '-convert', 'xml1', '-o', '-', dock_plist_path],
                                       capture_output=True, text=True, check=True).stdout

            # Parse the XML plist
            plist_data = plistlib.loads(xml_plist.encode('utf-8'))

            # Extract app names from persistent-apps
            app_names = []
            for app in plist_data.get('persistent-apps', []):
                tile_data = app.get('tile-data', {})
                label = tile_data.get('file-label', '')
                if label:
                    app_names.append(label)

            return app_names
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while reading the Dock plist: {e}")
            print(f"Error output: {e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        return []

    def on_press(self, key):
        if isinstance(key, keyboard.KeyCode):
            char = key.char
            if char is not None:  # Only add non-None characters
                self.last_three_keys.append(char)
                if len(self.last_three_keys) > 3:
                    self.last_three_keys.pop(0)

                if len(self.last_three_keys) == 3:
                    pattern = ''.join(self.last_three_keys)
                    if pattern in self.config:
                        self.undo_triplet()
                        self.execute_commands(self.config[pattern])
                        self.update_triplet_history(pattern)
        elif isinstance(key, keyboard.Key):
            # Handle function keys
            if key.name.startswith('f') and key.name[1:].isdigit():
                f_num = int(key.name[1:])
                if key.name in self.config:
                    self.execute_commands(self.config[key.name])
                    print("\nCommand executed. Refreshing cheatsheet...")
                    self.print_cheat_sheet()
                elif f_num <= len(self.dock_apps):
                    app_name = self.dock_apps[f_num - 1]
                    self.activate_application(app_name)
                    print("\nDock app activated. Refreshing cheatsheet...")
                    self.print_cheat_sheet()

        self.current_keys.add(key)

        # Check for Command + number
        if keyboard.Key.cmd in self.current_keys:
            for num in range(10):
                if hasattr(keyboard.KeyCode, f'from_char') and keyboard.KeyCode.from_char(
                        str(num)) in self.current_keys:
                    command_key = f"cmd+{num}"
                    if command_key in self.config:
                        self.execute_commands(self.config[command_key])
                        print("\nCommand executed. Refreshing cheatsheet...")
                        self.print_cheat_sheet()

    def on_release(self, key):
        self.current_keys.discard(key)

    def undo_triplet(self):
        with self.keyboard_controller.pressed(keyboard.Key.cmd):
            self.keyboard_controller.press('z')
            self.keyboard_controller.release('z')

    def execute_python_command(self, command_string):
        """
        Execute a Python script using a specific Python interpreter with arguments.
        """
        try:
            args = shlex_module.split(command_string)

            if len(args) < 2:
                print(f"Warning: Invalid Python command format: {command_string}")
                print("Expected format: /path/to/python /path/to/script.py [args...]")
                return

            python_interpreter = args[0]
            script_path = args[1]
            script_args = args[2:] if len(args) > 2 else []

            if not Path(python_interpreter).exists():
                print(f"Warning: Python interpreter not found: {python_interpreter}")
                return

            if not Path(script_path).exists():
                print(f"Warning: Python script not found: {script_path}")
                return

            env = os.environ.copy()
            script_dir = str(Path(script_path).parent)

            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{script_dir}:{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = script_dir

            process = subprocess.Popen(
                [python_interpreter, script_path] + script_args,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            def handle_output():
                while True:
                    output = process.stdout.readline()
                    if output:
                        print(output.strip())
                    if process.poll() is not None:
                        break

                stdout, stderr = process.communicate()
                if stdout:
                    print(stdout.strip())
                if stderr:
                    print(f"Errors: {stderr.strip()}")

                # Reprint cheatsheet after command execution
                print("\nPython command completed. Refreshing cheatsheet...")
                self.print_cheat_sheet()

            import threading
            output_thread = threading.Thread(target=handle_output, daemon=True)
            output_thread.start()

            print(f"Started Python command: {command_string}")

        except Exception as e:
            print(f"Error executing Python command: {e}")
            self.print_cheat_sheet()

    def execute_commands(self, command_config):
        current_time = time.time()
        if current_time - self.last_execution_time < self.cooldown_period:
            return

        self.last_execution_time = current_time
        # If it's the old format (direct list of commands)
        if isinstance(command_config, list):
            commands = command_config
        # If it's the new format (dict with commands key)
        else:
            commands = command_config["commands"]

        for command in commands:
            if 'activate_command' in command:
                self.activate_application(command['activate_command'], command.get('window', ''))
            elif 'iterm_command' in command:
                self.execute_iterm_command(command['iterm_command'], command.get('window', ''))
            elif 'url' in command:
                self.find_or_create_chrome_tab(command['url'])
            elif 'python_command' in command:
                self.execute_python_command(command['python_command'])

            delay = command.get('delay', 0)
            time.sleep(delay)

    def get_command_description(self, key, command_config):
        # If it's the old format (direct list of commands)
        if isinstance(command_config, list):
            command = command_config[0]
            if 'activate_command' in command:
                return f"Activate {command['activate_command']}"
            elif 'iterm_command' in command:
                return f"iTerm: {command['iterm_command'][:30]}..."
            elif 'python_command' in command:
                return f"Python: {command['python_command']}"
            return "Unknown command"

        # If it's the new format with description
        return command_config.get("description", "No description provided")

    def activate_application(self, app_name, window=''):
        script = f'''
        tell application "{app_name}"
            activate
        '''

        if window:
            script += f'''
            set index of window "{window}" to 1
            '''

        script += '''
        end tell
        '''

        subprocess.run(['osascript', '-e', script])
        print(f"Activated {app_name} {window}")

    def execute_iterm_command(self, command, window_title):
        apple_script = f'''
        tell application "iTerm"
            create window with default profile
            tell current window
                tell current session
                    write text "{command}"
                end tell
            end tell

        end tell
        '''
        subprocess.run(["osascript", "-e", apple_script])
        print(f"Executed iTerm command: {command} in window: {window_title}")

    def print_cheat_sheet(self):
        print("\n" + "=" * 60)
        print("AutoKey Cheat Sheet".center(60))
        print("=" * 60)

        # Print triplet commands
        print("\nTriplet Commands:")
        print("-" * 60)
        for key, commands in self.config.items():
            if len(key) == 3:
                desc = self.get_command_description(key, commands)
                print(f"{key:<10} {desc}")

        # Print function key commands
        print("\nFunction Key Commands:")
        print("-" * 60)
        for key, commands in self.config.items():
            if key.startswith('f') and key[1:].isdigit():
                desc = self.get_command_description(key, commands)
                print(f"{key.upper():<10} {desc}")

        # Print Command + number shortcuts
        print("\nCommand + Number Shortcuts:")
        print("-" * 60)
        for key, commands in self.config.items():
            if key.startswith('cmd+'):
                desc = self.get_command_description(key, commands)
                print(f"{key:<10} {desc}")

        # Print dock commands
        print("\nDock Commands (Function Keys):")
        print("-" * 60)
        for i, app in enumerate(self.dock_apps, 1):
            if i <= 12:  # Assuming F1-F12 keys
                print(f"F{i:<9} Activate {app}")

        print("\n" + "=" * 60)

    def find_or_create_chrome_tab(self, url):
        """Open a URL in the default web browser (replacing the Chrome-specific function)."""
        # Ensure URL has http:// or https:// prefix
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            # Using subprocess.run with the 'open' command (macOS specific)
            subprocess.run(['open', url], check=True)
            print(f"Opened URL in default browser: {url}")
        except subprocess.CalledProcessError as e:
            print(f"Error opening URL: {e}")

    def update_triplet_history(self, triplet_key):
        # Ensure data directory exists
        self.triplet_history_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing history
        history = {}
        if self.triplet_history_path.exists():
            with open(self.triplet_history_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    history[row['key']] = row

        now = datetime.now().isoformat(timespec='seconds')
        desc = self.get_command_description(triplet_key, self.config[triplet_key])
        if triplet_key in history:
            row = history[triplet_key]
            row['count'] = str(int(row['count']) + 1)
            row['last used'] = now
            row['description'] = desc
        else:
            row = {
                'key': triplet_key,
                'count': '1',
                'last used': now,
                'description': desc
            }
            history[triplet_key] = row

        # Sort by count descending, then by last used descending
        sorted_rows = sorted(history.values(), key=lambda r: (-int(r['count']), r['last used']), reverse=False)

        # Write back to CSV
        with open(self.triplet_history_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'count', 'last used', 'description'])
            writer.writeheader()
            for row in sorted_rows:
                writer.writerow(row)

    def run(self):
        self.print_cheat_sheet()
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()


def main():
    parser = argparse.ArgumentParser(description="AutoKey: Keyboard shortcut listener")
    parser.add_argument('--config', default='config.json', help='Path to the configuration file')
    args = parser.parse_args()

    auto_key = AutoKey(args.config)
    auto_key.dock_apps = auto_key.get_dock_apps()
    auto_key.run()


if __name__ == "__main__":
    main()