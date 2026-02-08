# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoKey is a macOS automation tool that provides custom keyboard shortcuts using triplets (three identical keystrokes like 'aaa', 'xxx') and function key combinations. It integrates with macOS applications, iTerm2, web browsers, and executes Python scripts to enhance productivity.

## Architecture

### Core Components

- **autokey/**: Main package with modular components (config, listener, executor, etc.)
- **autokey.py**: Entry point wrapper that imports from the autokey package
- **config.json**: Command definitions using new format with descriptions and command arrays
- **commands/**: Directory containing utility scripts called by shortcuts
- **data/triplet_history.csv**: Usage tracking for triplet commands
- **keyboard_rec.py**: Keyboard recording functionality

### Key Architecture Patterns

- **Config Migration**: Automatically migrates old format configs to new format with descriptions
- **Command Types**: Supports activate_command (app activation), iterm_command (terminal), url (browser), python_command (script execution)
- **Cooldown System**: 5-second cooldown prevents accidental rapid executions
- **Threading**: Python commands execute in separate threads with real-time output
- **AppleScript Integration**: Uses osascript for macOS app control

## Development Commands

Since this is a Python project without package.json, use standard Python commands:

```bash
# Run the main application
python autokey.py

# Run with custom config
python autokey.py --config my_config.json

# Install dependencies
pip install pynput

# Set up virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # or .venv/bin/activate.fish
pip install pynput
```

## Configuration System

### New Config Format (Current)
```json
{
  "key": {
    "description": "Human readable description",
    "commands": [
      {"activate_command": "AppName", "window": "WindowName", "delay": 2},
      {"python_command": "/path/to/python /path/to/script.py args"},
      {"url": "https://example.com"}
    ]
  }
}
```

### Command Types
- **activate_command**: Activates macOS applications via AppleScript
- **iterm_command**: Executes commands in new iTerm windows
- **python_command**: Runs Python scripts with full interpreter path
- **url**: Opens URLs in default browser

### Key Patterns
- **Triplets**: Three identical characters (aaa, xxx, qqw)
- **Function Keys**: f1-f12 (also maps to Dock apps)
- **Command Shortcuts**: cmd+1, cmd+2, etc.

## Integration Points

### External Dependencies
- **image_utils**: External Python project for image processing
- **VLC Media Player**: Controlled via commands/vlc_controller.py
- **iTerm2**: Terminal integration for command execution
- **macOS Dock**: Function keys map to Dock applications

### File Dependencies
- Configuration auto-creates if missing
- History tracking requires data/ directory
- Commands directory contains utility scripts

## Key Development Notes

- Uses pynput for cross-platform keyboard listening
- AppleScript integration requires macOS accessibility permissions
- Python commands execute with custom PYTHONPATH and environment
- Undo functionality uses Cmd+Z to remove typed triplets
- Thread-safe command execution with output streaming