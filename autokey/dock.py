"""macOS Dock app reader."""

import os
import plistlib
import subprocess
from typing import List


class DockReader:
    """Reads the list of apps from the macOS Dock."""

    def get_apps(self) -> List[str]:
        """Return list of app names from the Dock's persistent apps."""
        dock_plist_path = os.path.expanduser("~/Library/Preferences/com.apple.dock.plist")
        try:
            xml_plist = subprocess.run(
                ['plutil', '-convert', 'xml1', '-o', '-', dock_plist_path],
                capture_output=True,
                text=True,
                check=True
            ).stdout

            plist_data = plistlib.loads(xml_plist.encode('utf-8'))

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
