"""Triplet usage history tracking."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class HistoryTracker:
    """Tracks triplet command usage in a CSV file."""

    def __init__(self, history_path: Path):
        self.history_path = history_path

    def update(self, key: str, description: str) -> None:
        """Update the history for a triplet key."""
        self.history_path.parent.mkdir(parents=True, exist_ok=True)

        history = self._read_history()

        now = datetime.now().isoformat(timespec='seconds')
        if key in history:
            row = history[key]
            row['count'] = str(int(row['count']) + 1)
            row['last used'] = now
            row['description'] = description
        else:
            row = {
                'key': key,
                'count': '1',
                'last used': now,
                'description': description
            }
            history[key] = row

        self._write_history(history)

    def get_stats(self) -> Dict[str, Any]:
        """Return the current history statistics."""
        return self._read_history()

    def _read_history(self) -> Dict[str, Dict[str, str]]:
        """Read history from CSV file."""
        history = {}
        if self.history_path.exists():
            with open(self.history_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    history[row['key']] = row
        return history

    def _write_history(self, history: Dict[str, Dict[str, str]]) -> None:
        """Write history to CSV file, sorted by count descending."""
        sorted_rows = sorted(
            history.values(),
            key=lambda r: (-int(r['count']), r['last used']),
            reverse=False
        )

        with open(self.history_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'count', 'last used', 'description'])
            writer.writeheader()
            for row in sorted_rows:
                writer.writerow(row)
