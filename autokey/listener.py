"""Keyboard listener for AutoKey."""

from typing import Callable, Optional, Set, List
from pynput import keyboard


class KeyboardListener:
    """Handles pynput keyboard listening and pattern detection."""

    def __init__(
        self,
        on_triplet: Callable[[str], None],
        on_function_key: Callable[[str], None],
        on_cmd_number: Callable[[str], None]
    ):
        self.on_triplet = on_triplet
        self.on_function_key = on_function_key
        self.on_cmd_number = on_cmd_number

        self.current_keys: Set = set()
        self.last_three_keys: List[str] = []
        self.keyboard_controller = keyboard.Controller()
        self._listener: Optional[keyboard.Listener] = None

    def start(self) -> None:
        """Start listening for keyboard events (blocking)."""
        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        ) as listener:
            self._listener = listener
            listener.join()

    def stop(self) -> None:
        """Stop the keyboard listener."""
        if self._listener:
            self._listener.stop()

    def undo_triplet(self) -> None:
        """Send Cmd+Z to undo the typed triplet."""
        with self.keyboard_controller.pressed(keyboard.Key.cmd):
            self.keyboard_controller.press('z')
            self.keyboard_controller.release('z')

    def _on_press(self, key) -> None:
        """Handle key press events."""
        if isinstance(key, keyboard.KeyCode):
            char = key.char
            if char is not None:
                self.last_three_keys.append(char)
                if len(self.last_three_keys) > 3:
                    self.last_three_keys.pop(0)

                if len(self.last_three_keys) == 3:
                    pattern = ''.join(self.last_three_keys)
                    self.on_triplet(pattern)

        elif isinstance(key, keyboard.Key):
            if key.name.startswith('f') and key.name[1:].isdigit():
                self.on_function_key(key.name)

        self.current_keys.add(key)

        if keyboard.Key.cmd in self.current_keys:
            for num in range(10):
                key_code = keyboard.KeyCode.from_char(str(num))
                if key_code in self.current_keys:
                    self.on_cmd_number(f"cmd+{num}")
                    break

    def _on_release(self, key) -> None:
        """Handle key release events."""
        self.current_keys.discard(key)
