# AutoKey

AutoKey is a Python-based tool that enhances your productivity by allowing you to create custom keyboard shortcuts for various actions on your Mac.

## Features

- Custom triplet key commands (e.g., 'aaa', 'nnn')
- Function key shortcuts (F1-F12)
- Integration with Dock apps
- iTerm2 command execution
- Chrome tab management
- Cheat sheet display for easy reference

## Requirements

- Python 3.x
- macOS
- iTerm2 (for iTerm-specific commands)
- Google Chrome (for Chrome-specific commands)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/jgreek/autokey.git
   cd autokey
   ```

2. Install the required Python packages:
   ```
   pip install pynput
   ```

3. Ensure you have the necessary permissions to control your Mac using Python (you may need to grant accessibility permissions to your terminal or Python interpreter).

## Configuration

AutoKey uses a JSON configuration file to define custom shortcuts. By default, it looks for `config.json` in the same directory as the script. You can specify a different configuration file using the `--config` option.

### Understanding Triplets

A key feature of AutoKey is the use of "triplets" for triggering actions. A triplet is a sequence of three identical keys pressed in quick succession. For example:

- 'aaa' might activate a specific application
- 'nnn' could execute a command in iTerm
- 'ttt' might switch to a particular window in an IDE

Triplets are designed to be easy to remember and quick to type, while being unlikely to conflict with normal typing patterns.

Example `config.json`:

```json
{
  "aaa": [
    {"activate_command": "ApplicationName"}
  ],
  "bbb": [
    {"iterm_command": "echo 'Example command'", "window": "Example Window"}
  ],
  "ccc": [
    {"activate_command": "IDE", "window": "ProjectName"}
  ],
  "ddd": [
    {"activate_command": "ApplicationName", "window": "WindowName", "delay": 5}
  ],
  "eee": [
    {"url": "example.com"}
  ],
  "fff": [
    {"activate_command": "ApplicationName1", "delay": 2},
    {"activate_command": "ApplicationName2", "window": ""}
  ],
  "ggg": [
    {"activate_command": "MusicApp", "delay": 1}
  ]
}
```

This configuration demonstrates various types of commands and their structures, including activating applications, executing iTerm commands, opening URLs, and chaining multiple actions.

## Usage

Run the script:

```
python autokey.py
```

Or with a custom configuration file:

```
python autokey.py --config my_config.json
```

When you run the script, it will display a cheat sheet of your configured shortcuts.

## Customization

You can customize AutoKey by modifying the `config.json` file. The configuration supports the following types of commands:

- `activate_command`: Activates a specified application
- `iterm_command`: Executes a command in iTerm2
- `url`: Opens or switches to a Chrome tab with the specified URL

You can combine these commands and add delays between actions to create complex sequences triggered by a single triplet.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Disclaimer

Use this tool responsibly. Be aware that it can control your computer based on keyboard input, so make sure you understand the configured shortcuts before running the script. While triplets are designed to avoid accidental triggering, be cautious when setting up shortcuts for critical or potentially destructive actions.