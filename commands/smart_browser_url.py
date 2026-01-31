#!/usr/bin/env python3
"""
Smart Browser URL Manager - Delete domain tabs, open new URL
"""

import argparse
import subprocess
import json
from pathlib import Path
from urllib.parse import urlparse


class SmartBrowserURL:
    def __init__(self, browser="Brave Browser"):
        self.browser = browser
        self.script_dir = Path(__file__).resolve().parent
        self.config_path = self.script_dir / "browser_tags.json"
        self.tag_mappings = self.load_tag_mappings()

    def load_tag_mappings(self):
        """Load tag-to-domains mapping from config file"""
        if not self.config_path.exists():
            default_config = {
                "news": ["cnn.com", "bbc.com", "nytimes.com", "theguardian.com"],
                "sports": ["espn.com", "nfl.com", "nba.com"],
                "work": ["github.com", "slack.com", "gmail.com"]
            }
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def extract_domain(self, url):
        """Extract domain from URL"""
        parsed = urlparse(url if url.startswith('http') else f'https://{url}')
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def run_applescript(self, script):
        """Execute AppleScript"""
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        return result.returncode == 0

    def delete_domain_and_open(self, url, domain):
        """Delete tabs with domain, then open URL"""
        script = f'''
tell application "{self.browser}"
	set w to front window

	-- Collect tabs to delete
	set tabsToDelete to {{}}
	repeat with i from 1 to count of tabs of w
		set tabURL to URL of (tab i of w)
		if tabURL contains "{domain}" then
			set end of tabsToDelete to i
		end if
	end repeat

	-- Delete in reverse order
	repeat with idx in (reverse of tabsToDelete)
		delete (tab idx of w)
	end repeat

	-- Open the new URL
	make new tab at end of tabs of w with properties {{URL:"{url}"}}
end tell
'''
        return self.run_applescript(script)

    def delete_tags_and_open(self, url, tag):
        """Delete tabs with all domains in tag, then open URL"""
        if tag not in self.tag_mappings:
            print(f"Error: Tag '{tag}' not found")
            return False

        domains = self.tag_mappings[tag]
        domain_checks = " or ".join([f'tabURL contains "{d}"' for d in domains])

        script = f'''
tell application "{self.browser}"
	set w to front window

	-- Collect tabs to delete
	set tabsToDelete to {{}}
	repeat with i from 1 to count of tabs of w
		set tabURL to URL of (tab i of w)
		if {domain_checks} then
			set end of tabsToDelete to i
		end if
	end repeat

	-- Delete in reverse order
	repeat with idx in (reverse of tabsToDelete)
		delete (tab idx of w)
	end repeat

	-- Open the new URL
	make new tab at end of tabs of w with properties {{URL:"{url}"}}
end tell
'''
        return self.run_applescript(script)

    def show_tabs(self):
        """Show currently open tabs"""
        script = f'''
tell application "{self.browser}"
	set w to front window
	set output to ""
	repeat with i from 1 to count of tabs of w
		set tabURL to URL of (tab i of w)
		set output to output & tabURL & "
"
	end repeat
	return output
end tell
'''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            print("\nOpen tabs:")
            print("-" * 60)
            for i, url in enumerate(result.stdout.strip().split('\n'), 1):
                if url:
                    print(f"{i}. {url}")
            print()

    def list_tags(self):
        """List all tags and domains"""
        if not self.tag_mappings:
            print("No tags configured")
            return

        print("\nAvailable tags:")
        print("-" * 60)
        for tag, domains in self.tag_mappings.items():
            print(f"\n{tag}:")
            for domain in domains:
                print(f"  - {domain}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Smart Browser URL Manager")
    parser.add_argument('--url', help='URL to open')
    parser.add_argument('--tag', help='Tag group (deletes all domains in tag)')
    parser.add_argument('--list-tags', action='store_true', help='List all tags')
    parser.add_argument('--show-tabs', action='store_true', help='Show open tabs')

    args = parser.parse_args()

    if not args.url and not args.list_tags and not args.show_tabs:
        parser.error("--url required (or use --list-tags or --show-tabs)")

    manager = SmartBrowserURL()

    if args.list_tags:
        manager.list_tags()
        return

    if args.show_tabs:
        manager.show_tabs()
        return

    if args.tag:
        success = manager.delete_tags_and_open(args.url, args.tag)
        if success:
            print(f"✓ Deleted {args.tag} tabs, opened URL")
    else:
        domain = manager.extract_domain(args.url)
        success = manager.delete_domain_and_open(args.url, domain)
        if success:
            print(f"✓ Deleted {domain} tabs, opened URL")

    exit(0 if success else 1)


if __name__ == "__main__":
    main()
