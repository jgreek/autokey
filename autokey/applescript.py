"""AppleScript helper functions for macOS automation."""

import subprocess


def run_applescript(script: str) -> str:
    """Execute an AppleScript and return the output."""
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def activate_app(app_name: str, window: str = '') -> None:
    """Activate a macOS application, optionally bringing a specific window to front."""
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
