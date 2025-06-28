#!/usr/bin/env python3
import subprocess
import sys
import os
import argparse
import glob
from pathlib import Path


def get_most_recent_file(folder_path, extensions=None):
    """Get the most recent file from the specified folder with specified extensions."""
    folder = Path(folder_path).expanduser()

    if not folder.exists():
        print(f"Folder does not exist: {folder}")
        return None

    # Default extensions if none provided
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png']

    # Get all files with specified extensions
    files = []
    for ext in extensions:
        # Case insensitive search
        files.extend(folder.glob(f'*{ext}'))
        files.extend(folder.glob(f'*{ext.upper()}'))

    if not files:
        print(f"No files with extensions {extensions} found in: {folder}")
        return None

    # Sort by modification time (newest first)
    most_recent = max(files, key=lambda f: f.stat().st_mtime)
    return str(most_recent)


def main():
    parser = argparse.ArgumentParser(description='VLC Controller')
    parser.add_argument('--delay', '-d', type=float, default=1.0,
                        help='Delay between VLC command and file open (seconds)')
    parser.add_argument('--folder', '-f', default='~/Desktop', help='Folder to search for recent file')
    parser.add_argument('--keys', '-k', default='cmd+option+s', help='Key combination to send to VLC')
    parser.add_argument('--extensions', '-e', nargs='+', default=['.jpg', '.jpeg', '.png'],
                        help='File extensions to search for')

    args = parser.parse_args()

    # Get the most recent file
    recent_file = get_most_recent_file(args.folder, args.extensions)
    if not recent_file:
        return

    # Parse key combination
    key_parts = args.keys.lower().split('+')
    key_modifiers = []
    key_char = None

    for part in key_parts:
        if part in ['cmd', 'command']:
            key_modifiers.append('command down')
        elif part in ['opt', 'option', 'alt']:
            key_modifiers.append('option down')
        elif part in ['shift']:
            key_modifiers.append('shift down')
        elif part in ['ctrl', 'control']:
            key_modifiers.append('control down')
        else:
            key_char = part

    modifier_string = ', '.join(key_modifiers)

    # Execute VLC command
    vlc_cmd = [
        'osascript',
        '-e', 'tell application "VLC" to activate',
        '-e', f'tell application "System Events" to keystroke "{key_char}" using {{{modifier_string}}}'
    ]

    try:
        #subprocess.run(vlc_cmd, check=True)
        #print(f"Sent {args.keys} to VLC")

        # Wait for the specified delay
        #import time
        #time.sleep(args.delay)

        # Open the most recent file
        subprocess.run(['open', recent_file], check=True)
        print(f"Opened: {recent_file}")

    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")


if __name__ == "__main__":
    main()