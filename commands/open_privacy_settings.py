#!/usr/bin/env python3
"""Open Privacy & Security pane in System Settings."""

import subprocess

subprocess.run(["open", "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension"])
