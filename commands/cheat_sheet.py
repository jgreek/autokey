#!/usr/bin/env python3
"""
Autokey Cheat Sheet - generates a minimalist HTML cheat sheet from config.json
and opens it in the default browser.
"""

import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "triplet_history.csv"
CHEAT_SHEET_PATH = Path(__file__).resolve().parent.parent / "data" / "cheat_sheet.html"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_stats():
    stats = {}
    if not HISTORY_PATH.exists():
        return stats
    with open(HISTORY_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stats[row["key"]] = {
                "count": int(row["count"]),
                "last_used": row["last used"],
            }
    return stats


def relative_time(iso_str):
    try:
        then = datetime.fromisoformat(iso_str)
        diff = (datetime.now() - then).days
        if diff == 0:
            return "today"
        if diff == 1:
            return "yesterday"
        if diff < 7:
            return f"{diff}d ago"
        if diff < 30:
            return f"{diff // 7}w ago"
        return f"{diff // 30}mo ago"
    except Exception:
        return ""


def get_command_detail(commands):
    for cmd in commands:
        if "activate_command" in cmd:
            return cmd["activate_command"]
        if "url" in cmd:
            return cmd["url"]
        if "python_command" in cmd:
            val = cmd["python_command"]
            if "--url" in val:
                return val.split("--url")[-1].strip().split()[0]
            return "python"
        if "iterm_command" in cmd:
            return cmd["iterm_command"][:40]
    return ""


def heat_class(count, max_count):
    if count == 0:
        return "heat-0"
    ratio = count / max_count
    if ratio >= 0.6:
        return "heat-3"
    if ratio >= 0.25:
        return "heat-2"
    return "heat-1"


def build_row(key, value, stat, max_count):
    desc = value.get("description", "—")
    commands = value.get("commands", [])
    detail = get_command_detail(commands)

    count = stat.get("count", 0) if stat else 0
    last_used = stat.get("last_used", "") if stat else ""
    rel = relative_time(last_used) if last_used else "never"
    hc = heat_class(count, max_count)

    count_html = f'<span class="usage-count {hc}">×{count}</span>' if count else '<span class="usage-count heat-0">—</span>'

    return f'  <tr class="row {hc}"><td><kbd>{key}</kbd></td><td class="desc">{desc}</td><td class="detail">{detail}</td><td class="count">{count_html}</td><td class="last-used">{rel}</td></tr>\n'


def build_html(config, stats):
    max_count = max((s["count"] for s in stats.values()), default=1)
    total = len(config)
    total_uses = sum(s["count"] for s in stats.values())

    # Top 5 most used
    top_keys = {k for k, _ in sorted(
        [(k, stats[k]) for k in config if k in stats],
        key=lambda x: -x[1]["count"]
    )[:5]}

    # Build single table: top-5 section header + rows, then groups
    rows = ""
    if top_keys:
        rows += '  <tr class="group-header top-header"><td colspan="5">Most Used</td></tr>\n'
        for key, stat in sorted(
            [(k, stats[k]) for k in config if k in top_keys],
            key=lambda x: -x[1]["count"]
        ):
            rows += build_row(key, config[key], stat, max_count)
        rows += '  <tr class="divider-row"><td colspan="5"></td></tr>\n'

    # Groups sorted by prefix, entries sorted by count desc
    groups = {}
    for key, value in config.items():
        groups.setdefault(key[0].upper(), []).append((key, value))

    for prefix in groups:
        groups[prefix].sort(key=lambda x: -(stats.get(x[0], {}).get("count", 0)))

    for prefix in sorted(groups):
        rows += f'  <tr class="group-header"><td colspan="5">{prefix}</td></tr>\n'
        for key, value in groups[prefix]:
            rows += build_row(key, value, stats.get(key), max_count)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Autokey Cheat Sheet</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg: #f9f9f7;
      --border: #e8e8e4;
      --border-faint: #f0f0ec;
      --text: #1a1a1a;
      --muted: #999990;
      --accent: #2d2d2d;
      --kbd-bg: #1a1a1a;
      --kbd-text: #f0f0ee;
      --kbd-shadow: #00000033;
      --group-label: #c0c0b8;
      --row-hover: #f3f3f0;
      --heat1: #b09870;
      --heat2: #a07840;
      --heat3: #7c5010;
    }}

    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #111110;
        --border: #252523;
        --border-faint: #1e1e1c;
        --text: #e8e8e4;
        --muted: #555550;
        --accent: #e8e8e4;
        --kbd-bg: #2a2a28;
        --kbd-text: #f0f0ee;
        --kbd-shadow: #00000066;
        --group-label: #3a3a38;
        --row-hover: #191918;
        --heat1: #6b5a3e;
        --heat2: #b07830;
        --heat3: #e09840;
      }}
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
      font-size: 13px;
      line-height: 1.4;
      padding: 40px 36px;
      max-width: 780px;
      margin: 0 auto;
    }}

    header {{
      display: flex;
      align-items: baseline;
      gap: 14px;
      margin-bottom: 28px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
    }}

    header h1 {{
      font-size: 18px;
      font-weight: 600;
      letter-spacing: -0.3px;
      color: var(--accent);
    }}

    header .stats {{
      font-size: 11px;
      color: var(--muted);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
    }}

    tr.group-header td {{
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--group-label);
      padding: 20px 0 6px;
      border-bottom: 1px solid var(--border-faint);
    }}

    tr.top-header td {{
      padding-top: 0;
    }}

    tr.divider-row td {{
      padding: 0;
      height: 24px;
      border-bottom: 1px solid var(--border);
    }}

    tr.row {{
      border-bottom: 1px solid var(--border-faint);
      transition: background 0.1s;
    }}

    tr.row:hover {{ background: var(--row-hover); }}

    tr.row.heat-0 {{ opacity: 0.45; }}

    td {{
      padding: 7px 10px 7px 0;
      vertical-align: middle;
      white-space: nowrap;
    }}

    td:last-child {{ padding-right: 0; }}

    kbd {{
      display: inline-block;
      background: var(--kbd-bg);
      color: var(--kbd-text);
      font-family: "SF Mono", "JetBrains Mono", "Fira Code", monospace;
      font-size: 11px;
      font-weight: 500;
      padding: 2px 7px;
      border-radius: 4px;
      box-shadow: 0 1px 0 var(--kbd-shadow);
      min-width: 32px;
      text-align: center;
    }}

    td.desc {{
      font-size: 13px;
      color: var(--text);
      width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    td.detail {{
      font-size: 11px;
      color: var(--muted);
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      padding-right: 20px;
    }}

    td.count {{ text-align: right; padding-right: 16px; }}

    .usage-count {{
      font-family: "SF Mono", "JetBrains Mono", monospace;
      font-size: 11px;
      font-weight: 600;
    }}

    .usage-count.heat-0 {{ color: var(--muted); font-weight: 400; }}
    .usage-count.heat-1 {{ color: var(--heat1); }}
    .usage-count.heat-2 {{ color: var(--heat2); }}
    .usage-count.heat-3 {{ color: var(--heat3); }}

    td.last-used {{
      font-size: 11px;
      color: var(--muted);
      text-align: right;
      min-width: 64px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Autokey</h1>
    <span class="stats">{total} shortcuts &middot; {total_uses} total uses</span>
  </header>
  <table>
    <tbody>
{rows}    </tbody>
  </table>
</body>
</html>"""


def main():
    config = load_config()
    stats = load_stats()
    html = build_html(config, stats)

    CHEAT_SHEET_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHEAT_SHEET_PATH.write_text(html, encoding="utf-8")

    subprocess.run(["open", CHEAT_SHEET_PATH.as_uri()])


if __name__ == "__main__":
    main()
