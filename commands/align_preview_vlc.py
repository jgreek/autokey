import subprocess
import time
from typing import Optional
import os
import shutil
from datetime import datetime


def transfer_files_to_yearly_archive(source_dir: str, destination_base: str) -> None:
    """
    Move all files from source directory to a year-based destination directory.

    Args:
        source_dir: Source directory containing files to move
        destination_base: Base destination directory where year folders will be created
    """
    current_year = str(datetime.now().year)
    destination_dir = os.path.join(destination_base, current_year)

    # Create destination directory if it doesn't exist
    os.makedirs(destination_dir, exist_ok=True)

    # Move all files from source to destination
    for item in os.listdir(source_dir):
        source_item = os.path.join(source_dir, item)
        destination_item = os.path.join(destination_dir, item)

        if os.path.exists(destination_item):
            print(f"Warning: {item} already exists in destination. Skipping...")
            continue

        try:
            shutil.move(source_item, destination_item)
            print(f"Moved: {item}")
        except Exception as e:
            print(f"Error moving {item}: {str(e)}")


def switch_to_app(app_name: str) -> None:
    """
    Switch to the specified macOS application using osascript.

    Args:
        app_name: Name of the application to switch to
    """
    apple_script = f'tell application "{app_name}" to activate'
    subprocess.run(['osascript', '-e', apple_script])
    # Small delay to ensure app switch completes
    time.sleep(0.5)


def send_keyboard_shortcut(cmd: bool = False, opt: bool = False,
                           shift: bool = False, key: str = '') -> None:
    """
    Send a keyboard shortcut using osascript.

    Args:
        cmd: Include command key in shortcut
        opt: Include option key in shortcut
        shift: Include shift key in shortcut
        key: The main key to press (e.g., '1', 'r', 'e')
    """
    modifiers = []
    if cmd:
        modifiers.append('command down')
    if opt:
        modifiers.append('option down')
    if shift:
        modifiers.append('shift down')

    modifier_str = ', '.join(modifiers)

    apple_script = f'''
    tell application "System Events"
        keystroke "{key}" using {{{modifier_str}}}
    end tell
    '''

    subprocess.run(['osascript', '-e', apple_script])
    time.sleep(0.2)  # Small delay between keypresses


def run_preview_vlc_sequence() -> None:
    """Execute the specific Preview and VLC shortcut sequence."""
    # Switch to VLC and send shortcut
    # time.sleep(1)
    send_keyboard_shortcut(cmd=True, opt=True, key='h')

    switch_to_app("Preview")
    send_keyboard_shortcut(cmd=True, opt=True, key='1')
    send_keyboard_shortcut(cmd=True, opt=True, key='e')

    time.sleep(1)
    switch_to_app("VLC")
    send_keyboard_shortcut(cmd=True, opt=True, key='r')

    switch_to_app("Preview")


if __name__ == "__main__":
    # Example usage of both functions
    source_dir = "/Users/johngreek/Desktop"
    destination_base = "/Users/johngreek/Archives/pictures"

    # First copy the files
    transfer_files_to_yearly_archive(source_dir, destination_base)

    # Then run the original sequence
    run_preview_vlc_sequence()