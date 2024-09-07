import os
import plistlib
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from pynput import keyboard


class AutoKey:
    def __init__(self, config_path):
        self.script_dir = Path(__file__).resolve().parent
        self.config_path = self.script_dir / config_path
        self.config = self.load_config()
        self.current_keys = set()
        self.last_three_keys = []
        self.keyboard_controller = keyboard.Controller()
        self.dock_apps = self.get_dock_apps()

    def load_config(self):
        if not self.config_path.exists() or self.config_path.stat().st_size == 0:
            default_config = {
                "aaa": [
                    {"activate_command": "Google Chrome", "window": "", "delay": 3}
                ],
                "nnn": [
                    {"iterm_command": "echo 'My command'", "window": "Main Window"}
                ],
                "f12": [
                    {"iterm_command": "ls -lat", "window": "File List"}
                ]
            }
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config

        with open(self.config_path, 'r') as f:
            return json.load(f)

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
            self.last_three_keys.append(char)
            if len(self.last_three_keys) > 3:
                self.last_three_keys.pop(0)

            if len(set(self.last_three_keys)) == 1 and len(self.last_three_keys) == 3:
                triplet = ''.join(self.last_three_keys)
                if triplet in self.config:
                    self.undo_triplet()
                    self.execute_commands(self.config[triplet])
        elif isinstance(key, keyboard.Key):
            # Handle function keys
            if key.name.startswith('f') and key.name[1:].isdigit():
                f_num = int(key.name[1:])
                if key.name in self.config:
                    self.execute_commands(self.config[key.name])
                elif f_num <= len(self.dock_apps):
                    app_name = self.dock_apps[f_num - 1]
                    self.activate_application(app_name)

        self.current_keys.add(key)

        # Check for Command + number
        if keyboard.Key.cmd in self.current_keys:
            for num in range(10):
                if hasattr(keyboard.KeyCode, f'from_char') and keyboard.KeyCode.from_char(
                        str(num)) in self.current_keys:
                    command_key = f"cmd+{num}"
                    if command_key in self.config:
                        self.execute_commands(self.config[command_key])

    def on_release(self, key):
        self.current_keys.discard(key)

    def undo_triplet(self):
        with self.keyboard_controller.pressed(keyboard.Key.cmd):
            self.keyboard_controller.press('z')
            self.keyboard_controller.release('z')

    def execute_commands(self, commands):
        for command in commands:
            if 'activate_command' in command:
                self.activate_application(command['activate_command'], command.get('window', ''))
            elif 'iterm_command' in command:
                self.execute_iterm_command(command['iterm_command'], command.get('window', ''))
            elif 'url' in command:
                self.find_or_create_chrome_tab(command['url'])

            delay = command.get('delay', 0)
            time.sleep(delay)

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
            tell application "System Events"
                tell process "iTerm2"
                    click menu item "Edit Window Title" of menu "Window" of menu bar 1
                    delay 0.5
                    keystroke "{window_title}"
                    key code 36 -- Press Return
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
        for triplet, commands in self.config.items():
            if len(triplet) == 3:
                command_desc = self.get_command_description(commands[0])
                print(f"{triplet:<10} {command_desc}")

        # Print function key commands
        print("\nFunction Key Commands:")
        print("-" * 60)
        for key, commands in self.config.items():
            if key.startswith('f') and key[1:].isdigit():
                command_desc = self.get_command_description(commands[0])
                print(f"{key.upper():<10} {command_desc}")

        # Print dock commands
        print("\nDock Commands (Function Keys):")
        print("-" * 60)
        for i, app in enumerate(self.dock_apps, 1):
            if i <= 12:  # Assuming F1-F12 keys
                print(f"F{i:<9} Activate {app}")

        print("\n" + "=" * 60)

    def get_command_description(self, command):
        if 'activate_command' in command:
            return f"Activate {command['activate_command']}"
        elif 'iterm_command' in command:
            return f"iTerm: {command['iterm_command'][:30]}..."  # Truncate long commands
        return "Unknown command"

    def find_or_create_chrome_tab(self, url_substring):
        applescript = f'''
           on run argv
               set urlSubstring to item 1 of argv

               tell application "Google Chrome"
                   activate

                   set found to false
                   set windowIndex to 1
                   repeat with w in windows
                       set tabIndex to 1
                       repeat with t in tabs of w
                           if urlSubstring is in (URL of t as string) then
                               set found to true
                               set active tab index of w to tabIndex
                               set index of w to 1
                               return "Tab found and activated."
                           end if
                           set tabIndex to tabIndex + 1
                       end repeat
                       set windowIndex to windowIndex + 1
                   end repeat

                   if not found then
                       tell front window
                           make new tab with properties {{URL:"http://" & urlSubstring}}
                       end tell
                       return "New tab created with URL: http://" & urlSubstring
                   end if
               end tell
           end run
           '''

        try:
            result = subprocess.run(
                ["osascript", "-e", applescript, url_substring],
                capture_output=True,
                text=True,
                check=True
            )
            print(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            print(f"Script output: {e.stdout}")
    def run(self):
        self.print_cheat_sheet()
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()


def main():
    parser = argparse.ArgumentParser(description="AutoKey: Keyboard shortcut listener")
    parser.add_argument('--config', default='config.json', help='Path to the configuration file')
    args = parser.parse_args()

    auto_key = AutoKey(args.config)
    auto_key.run()


if __name__ == "__main__":
    main()
