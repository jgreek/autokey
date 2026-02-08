"""Command execution for AutoKey."""

import os
import subprocess
import shlex
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from .applescript import activate_app


class CommandExecutor:
    """Dispatches and executes AutoKey commands."""

    def __init__(self, cooldown: float = 5.0, on_error: Optional[Callable] = None):
        self.cooldown = cooldown
        self.last_execution_time = 0
        self.on_error = on_error

    def execute(self, command_config: Dict[str, Any]) -> bool:
        """Execute a command configuration, respecting cooldown.

        Returns True if command was executed, False if blocked by cooldown.
        """
        current_time = time.time()
        if current_time - self.last_execution_time < self.cooldown:
            return False

        self.last_execution_time = current_time

        if isinstance(command_config, list):
            commands = command_config
        else:
            commands = command_config.get("commands", [])

        for command in commands:
            self._execute_single(command)
            delay = command.get('delay', 0)
            if delay:
                time.sleep(delay)

        return True

    def _execute_single(self, command: Dict[str, Any]) -> None:
        """Execute a single command."""
        if 'activate_command' in command:
            self.activate_app(command['activate_command'], command.get('window', ''))
        elif 'iterm_command' in command:
            self.execute_iterm(command['iterm_command'], command.get('window', ''))
        elif 'url' in command:
            self.open_url(command['url'], command.get('browser'))
        elif 'python_command' in command:
            self.execute_python(command['python_command'])

    def execute_python(self, command_string: str) -> None:
        """Execute a Python script using a specific Python interpreter with arguments."""
        try:
            args = shlex.split(command_string)

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

            output_thread = threading.Thread(target=handle_output, daemon=True)
            output_thread.start()

            print(f"Started Python command: {command_string}")

        except Exception as e:
            print(f"Error executing Python command: {e}")
            if self.on_error:
                self.on_error()

    def activate_app(self, app_name: str, window: str = '') -> None:
        """Activate a macOS application."""
        activate_app(app_name, window)

    def execute_iterm(self, command: str, window_title: str = '') -> None:
        """Execute a command in a new iTerm window."""
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

    def open_url(self, url: str, browser: Optional[str] = None) -> None:
        """Open a URL in the specified browser or default browser."""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            if browser:
                subprocess.run(['open', '-a', browser, url], check=True)
                print(f"Opened URL in {browser}: {url}")
            else:
                subprocess.run(['open', url], check=True)
                print(f"Opened URL in default browser: {url}")
        except subprocess.CalledProcessError as e:
            print(f"Error opening URL: {e}")
