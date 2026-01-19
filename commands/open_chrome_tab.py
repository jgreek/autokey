#!/usr/bin/env python3
"""
open_chrome_tab.py --url cnn.com --tag news   # closes existing "news" tabs, opens cnn
open_chrome_tab.py --url wsj.com --tag news   # closes existing "news" tabs, opens wsj
"""

import argparse
import json
import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
TAG_FILE = DATA_DIR / "chrome_tab_tags.json"
BROWSER = "Brave Browser"


def load_tags():
    try:
        return json.load(open(TAG_FILE))
    except:
        return {}


def save_tags(tags):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json.dump(tags, open(TAG_FILE, "w"))


def applescript(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()


def close_tabs_matching(domains):
    for domain in domains:
        applescript(f'''
        tell application "{BROWSER}"
            repeat with w in windows
                set i to (count of tabs of w)
                repeat while i > 0
                    if URL of tab i of w contains "{domain}" then
                        close tab i of w
                    end if
                    set i to i - 1
                end repeat
            end repeat
        end tell
        ''')


def open_tab(url):
    result = applescript(f'''
    tell application "{BROWSER}"
        activate
        if (count of windows) = 0 then
            make new window
        end if
        set newTab to make new tab at front window with properties {{URL:"{url}"}}
        delay 2
        return URL of newTab
    end tell
    ''')
    return result


def get_domain(url):
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return url.split("/")[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", "-u", required=True)
    p.add_argument("--tag", "-t")
    args = p.parse_args()

    url = args.url if args.url.startswith("http") else "https://" + args.url

    tags = load_tags()

    # Close existing tabs with this tag
    if args.tag and args.tag in tags:
        close_tabs_matching(tags[args.tag])

    actual_url = open_tab(url)
    actual_domain = get_domain(actual_url) if actual_url else get_domain(args.url)
    print(f"Opened: {actual_url or url}")

    # Track under tag
    if args.tag:
        tags[args.tag] = [actual_domain]
        save_tags(tags)


if __name__ == "__main__":
    main()
