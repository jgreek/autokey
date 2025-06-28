#!/usr/bin/env python3
"""
Keyboard and Mouse Activity Recorder/Replayer for macOS
Requires: pip install pynput
"""

import json
import time
from datetime import datetime
from pynput import mouse, keyboard
from pynput.mouse import Button, Listener as MouseListener
from pynput.keyboard import Key, Listener as KeyboardListener
from pynput.mouse import Button as MouseButton
from pynput.keyboard import Key as KeyboardKey
import threading


class ActivityRecorder:
    def __init__(self):
        self.events = []
        self.recording = False
        self.start_time = None
        self.mouse_listener = None
        self.keyboard_listener = None

    def start_recording(self):
        """Start recording keyboard and mouse events"""
        self.events = []
        self.recording = True
        self.start_time = time.time()

        print("Recording started... Press ESC to stop recording")

        # Start mouse listener
        self.mouse_listener = MouseListener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll
        )

        # Start keyboard listener
        self.keyboard_listener = KeyboardListener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

        # Wait for ESC key to stop recording
        self.keyboard_listener.join()

    def stop_recording(self):
        """Stop recording"""
        self.recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        print("Recording stopped!")

    def on_mouse_move(self, x, y):
        """Record mouse movement"""
        if self.recording:
            event = {
                'type': 'mouse_move',
                'x': x,
                'y': y,
                'timestamp': time.time() - self.start_time
            }
            self.events.append(event)

    def on_mouse_click(self, x, y, button, pressed):
        """Record mouse clicks"""
        if self.recording:
            event = {
                'type': 'mouse_click',
                'x': x,
                'y': y,
                'button': button.name,
                'pressed': pressed,
                'timestamp': time.time() - self.start_time
            }
            self.events.append(event)

    def on_mouse_scroll(self, x, y, dx, dy):
        """Record mouse scroll"""
        if self.recording:
            event = {
                'type': 'mouse_scroll',
                'x': x,
                'y': y,
                'dx': dx,
                'dy': dy,
                'timestamp': time.time() - self.start_time
            }
            self.events.append(event)

    def on_key_press(self, key):
        """Record key press"""
        if key == Key.esc:
            self.stop_recording()
            return False

        if self.recording:
            try:
                key_name = key.char
            except AttributeError:
                key_name = str(key)

            event = {
                'type': 'key_press',
                'key': key_name,
                'timestamp': time.time() - self.start_time
            }
            self.events.append(event)

    def on_key_release(self, key):
        """Record key release"""
        if self.recording and key != Key.esc:
            try:
                key_name = key.char
            except AttributeError:
                key_name = str(key)

            event = {
                'type': 'key_release',
                'key': key_name,
                'timestamp': time.time() - self.start_time
            }
            self.events.append(event)

    def save_recording(self, filename):
        """Save recorded events to file"""
        data = {
            'recorded_at': datetime.now().isoformat(),
            'events': self.events
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Recording saved to {filename}")
        print(f"Total events recorded: {len(self.events)}")


class ActivityReplayer:
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()

    def load_recording(self, filename):
        """Load recorded events from file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            return data['events']
        except FileNotFoundError:
            print(f"File {filename} not found!")
            return None
        except json.JSONDecodeError:
            print(f"Invalid JSON in {filename}!")
            return None

    def replay_recording(self, filename):
        """Replay recorded events"""
        events = self.load_recording(filename)
        if not events:
            return

        print(f"Loaded {len(events)} events")
        print("Starting replay in 3 seconds...")
        time.sleep(3)

        last_timestamp = 0

        for event in events:
            # Wait for the appropriate time delay
            delay = event['timestamp'] - last_timestamp
            if delay > 0:
                time.sleep(delay)

            # Execute the event
            self.execute_event(event)
            last_timestamp = event['timestamp']

        print("Replay completed!")

    def execute_event(self, event):
        """Execute a single event"""
        try:
            if event['type'] == 'mouse_move':
                self.mouse_controller.position = (event['x'], event['y'])

            elif event['type'] == 'mouse_click':
                button = MouseButton.left if event['button'] == 'left' else MouseButton.right
                if event['pressed']:
                    self.mouse_controller.press(button)
                else:
                    self.mouse_controller.release(button)

            elif event['type'] == 'mouse_scroll':
                self.mouse_controller.scroll(event['dx'], event['dy'])

            elif event['type'] == 'key_press':
                key = self.parse_key(event['key'])
                self.keyboard_controller.press(key)

            elif event['type'] == 'key_release':
                key = self.parse_key(event['key'])
                self.keyboard_controller.release(key)

        except Exception as e:
            print(f"Error executing event: {e}")

    def parse_key(self, key_string):
        """Parse key string back to key object"""
        if len(key_string) == 1:
            return key_string

        # Handle special keys
        key_map = {
            'Key.space': Key.space,
            'Key.enter': Key.enter,
            'Key.tab': Key.tab,
            'Key.shift': Key.shift,
            'Key.shift_l': Key.shift_l,
            'Key.shift_r': Key.shift_r,
            'Key.ctrl': Key.ctrl,
            'Key.ctrl_l': Key.ctrl_l,
            'Key.ctrl_r': Key.ctrl_r,
            'Key.alt': Key.alt,
            'Key.alt_l': Key.alt_l,
            'Key.alt_r': Key.alt_r,
            'Key.cmd': Key.cmd,
            'Key.cmd_l': Key.cmd_l,
            'Key.cmd_r': Key.cmd_r,
            'Key.backspace': Key.backspace,
            'Key.delete': Key.delete,
            'Key.up': Key.up,
            'Key.down': Key.down,
            'Key.left': Key.left,
            'Key.right': Key.right,
        }

        return key_map.get(key_string, key_string)


def main():
    recorder = ActivityRecorder()
    replayer = ActivityReplayer()
    filename = "recorded_sequence.json"

    while True:
        print("\n" + "=" * 50)
        print("Keyboard & Mouse Activity Recorder/Replayer")
        print("=" * 50)
        print("1. Record new sequence")
        print("2. Replay saved sequence")
        print("3. Exit")

        choice = input("\nEnter your choice (1-3): ").strip()

        if choice == '1':
            print("\nPreparing to record...")
            print("Position your cursor and get ready!")
            print("Recording will start in 3 seconds...")
            time.sleep(3)

            recorder.start_recording()
            recorder.save_recording(filename)

        elif choice == '2':
            print(f"\nReplaying sequence from {filename}...")
            replayer.replay_recording(filename)

        elif choice == '3':
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    print("Make sure you have installed pynput: pip install pynput")
    print("\nIMPORTANT: This program needs accessibility permissions on macOS.")
    print("Go to System Preferences > Security & Privacy > Privacy > Accessibility")
    print("and add your Terminal or Python to the allowed applications.\n")

    main()