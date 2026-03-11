#!/usr/bin/env python3
"""
drive_navigator.py — Cloud/Network Drive navigator for AutoKey.

Best-practice patterns for navigating a deeply-nested investment document
drive (Google Drive, Dropbox, SMB share, etc.) from a keyboard shortcut.

Usage:
    python drive_navigator.py --root /Volumes/GoogleDrive/Investments --search "Series B"
    python drive_navigator.py --root /Volumes/GoogleDrive/Investments --rebuild-index
    python drive_navigator.py --root /Volumes/GoogleDrive/Investments --open-recent

Design choices:
  1. Local JSON index  — scans once, caches results; never blocks on a slow mount.
  2. Fuzzy path search — matches across folder segments, not just filenames.
  3. Metadata tagging  — extracts year / doc-type / fund from path conventions.
  4. macOS-native open — uses `open` so Finder / default app handles the file.
  5. Recent-file log   — tracks opens so `--open-recent` surfaces hot docs fast.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "drive_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Index is stale after this many minutes (network drives are slow — 60 min default)
INDEX_TTL_MINUTES = 60

# Document extensions considered "investment documents"
DOC_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".pptx", ".ppt", ".csv", ".txt", ".md",
}

# Folder-name tokens that hint at document category
CATEGORY_TOKENS: Dict[str, str] = {
    "lp update":    "LP Update",
    "fund":         "Fund",
    "portfolio":    "Portfolio",
    "diligence":    "Due Diligence",
    "cap table":    "Cap Table",
    "term sheet":   "Term Sheet",
    "financials":   "Financials",
    "legal":        "Legal",
    "board":        "Board",
    "deck":         "Deck",
    "memo":         "Memo",
    "model":        "Model",
}

MAX_RESULTS = 15  # How many search hits to show
MAX_RECENT  = 10  # How many recently opened files to track


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------

def _index_path(root: Path) -> Path:
    """Return the cache file path for a given root directory."""
    safe_name = root.as_posix().replace("/", "_").strip("_")
    return CACHE_DIR / f"index_{safe_name}.json"


def _recent_path() -> Path:
    return CACHE_DIR / "recent.json"


def index_is_fresh(root: Path) -> bool:
    idx = _index_path(root)
    if not idx.exists():
        return False
    age_minutes = (time.time() - idx.stat().st_mtime) / 60
    return age_minutes < INDEX_TTL_MINUTES


def build_index(root: Path, verbose: bool = True) -> List[Dict]:
    """
    Walk *root* and return a list of document records.

    Each record:
        path      — absolute path string
        rel       — path relative to root (for display / search)
        name      — filename stem
        ext       — lowercase extension
        size      — bytes
        modified  — ISO timestamp
        category  — inferred from path tokens
        year      — 4-digit year inferred from path/filename, or None
    """
    if verbose:
        print(f"Indexing {root} …", flush=True)

    records: List[Dict] = []
    root_str = str(root)

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Skip hidden dirs (e.g. .Trash, .DS_Store parent dirs)
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for fname in filenames:
            if fname.startswith("."):
                continue
            ext = Path(fname).suffix.lower()
            if ext not in DOC_EXTENSIONS:
                continue

            abs_path = os.path.join(dirpath, fname)
            rel = abs_path[len(root_str):].lstrip("/")

            try:
                stat = os.stat(abs_path)
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
            except OSError:
                size, modified = 0, ""

            records.append({
                "path":     abs_path,
                "rel":      rel,
                "name":     Path(fname).stem,
                "ext":      ext,
                "size":     size,
                "modified": modified,
                "category": _infer_category(rel),
                "year":     _infer_year(rel),
            })

    records.sort(key=lambda r: r["modified"], reverse=True)

    idx_path = _index_path(root)
    idx_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    if verbose:
        print(f"Indexed {len(records)} documents → {idx_path}")

    return records


def load_index(root: Path) -> List[Dict]:
    idx_path = _index_path(root)
    if not idx_path.exists():
        return []
    return json.loads(idx_path.read_text(encoding="utf-8"))


def _infer_category(rel_path: str) -> str:
    lower = rel_path.lower()
    for token, label in CATEGORY_TOKENS.items():
        if token in lower:
            return label
    return "General"


def _infer_year(rel_path: str) -> Optional[str]:
    import re
    # Match a 4-digit year between 2000–2035 anywhere in the path
    m = re.search(r"\b(20[0-2]\d)\b", rel_path)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Fuzzy search
# ---------------------------------------------------------------------------

def _score(record: Dict, query: str) -> int:
    """
    Return a relevance score for *record* vs *query* (higher = better).
    0 means no match.

    Strategy (ordered by quality of signal):
      4 — query matches the bare filename exactly (case-insensitive)
      3 — all query words appear in the filename
      2 — all query words appear in the relative path
      1 — at least one word appears in the relative path
    """
    q = query.lower()
    words = q.split()
    name_lower = record["name"].lower()
    rel_lower  = record["rel"].lower()

    if name_lower == q:
        return 4
    if all(w in name_lower for w in words):
        return 3
    if all(w in rel_lower for w in words):
        return 2
    if any(w in rel_lower for w in words):
        return 1
    return 0


def search(records: List[Dict], query: str) -> List[Dict]:
    scored = [(r, _score(r, query)) for r in records]
    hits   = [(r, s) for r, s in scored if s > 0]
    hits.sort(key=lambda x: (-x[1], x[0]["modified"]), reverse=False)
    return [r for r, _ in hits[:MAX_RESULTS]]


# ---------------------------------------------------------------------------
# Recent-file tracking
# ---------------------------------------------------------------------------

def log_recent(path: str) -> None:
    rp = _recent_path()
    recent: List[Dict] = json.loads(rp.read_text()) if rp.exists() else []
    # Remove old entry for same file if present
    recent = [r for r in recent if r["path"] != path]
    recent.insert(0, {"path": path, "opened": datetime.now().isoformat(timespec="seconds")})
    rp.write_text(json.dumps(recent[:MAX_RECENT], indent=2))


def load_recent() -> List[Dict]:
    rp = _recent_path()
    if not rp.exists():
        return []
    return json.loads(rp.read_text())


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _print_results(results: List[Dict], root: Path) -> None:
    if not results:
        print("No documents found.")
        return

    print(f"\n{'#':<3}  {'Category':<16}  {'Year':<6}  {'Size':<9}  {'Path'}")
    print("─" * 80)
    for i, r in enumerate(results, 1):
        year = r.get("year") or "    "
        size = _fmt_size(r["size"])
        # Truncate long paths from the left
        rel = r["rel"]
        if len(rel) > 55:
            rel = "…" + rel[-54:]
        print(f"{i:<3}  {r['category']:<16}  {year:<6}  {size:<9}  {rel}")
    print()


# ---------------------------------------------------------------------------
# macOS open
# ---------------------------------------------------------------------------

def open_path(path: str) -> None:
    """Open a file or folder with the macOS default handler."""
    if not Path(path).exists():
        print(f"Path no longer exists: {path}")
        return
    log_recent(path)
    subprocess.run(["open", path])


def open_in_finder(path: str) -> None:
    """Reveal a file in Finder (selects it)."""
    if not Path(path).exists():
        print(f"Path no longer exists: {path}")
        return
    log_recent(path)
    subprocess.run(["open", "-R", path])


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _prompt_pick(results: List[Dict]) -> Optional[str]:
    """Ask the user to pick a result number, or press Enter to abort."""
    if not results:
        return None
    raw = input("Open #  (Enter to skip, 'f' to reveal in Finder): ").strip()
    if not raw:
        return None
    if raw.lower() == "f":
        raw = input("Reveal # in Finder: ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(results):
                open_in_finder(results[idx]["path"])
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(results):
            return results[idx]["path"]
    print("Invalid selection.")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Navigate investment documents on a cloud / network drive."
    )
    parser.add_argument("--root", required=True,
                        help="Root folder of the drive to navigate")
    parser.add_argument("--search", "-s",
                        help="Search query (supports multiple words)")
    parser.add_argument("--rebuild-index", action="store_true",
                        help="Force a full re-index even if the cache is fresh")
    parser.add_argument("--open-recent", action="store_true",
                        help="Show and open a recently accessed document")
    parser.add_argument("--open", metavar="N", type=int,
                        help="Directly open result #N without prompting (for non-interactive use)")
    parser.add_argument("--reveal", metavar="N", type=int,
                        help="Reveal result #N in Finder without prompting")
    parser.add_argument("--category", "-c",
                        help="Filter results to a specific category (e.g. 'Financials')")
    parser.add_argument("--year", "-y",
                        help="Filter results to a specific year (e.g. '2023')")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()

    # ── Recent files shortcut ───────────────────────────────────────────────
    if args.open_recent:
        recent = load_recent()
        if not recent:
            print("No recently opened documents.")
            sys.exit(0)
        print("\nRecently opened:")
        for i, r in enumerate(recent, 1):
            p = r["path"]
            rel = p[len(str(root)):].lstrip("/") if p.startswith(str(root)) else p
            print(f"  {i}. {rel}  ({r['opened']})")
        print()
        path = _prompt_pick([{"path": r["path"]} for r in recent])
        if path:
            open_path(path)
        sys.exit(0)

    # ── Mount check ─────────────────────────────────────────────────────────
    if not root.exists():
        print(f"Drive not mounted or path not found: {root}")
        print("Tip: mount the drive first, then retry.")
        sys.exit(1)

    # ── Index management ────────────────────────────────────────────────────
    if args.rebuild_index or not index_is_fresh(root):
        records = build_index(root)
    else:
        records = load_index(root)
        if not records:
            records = build_index(root)

    # ── Category / year filters ─────────────────────────────────────────────
    if args.category:
        records = [r for r in records
                   if r["category"].lower() == args.category.lower()]
    if args.year:
        records = [r for r in records if r.get("year") == args.year]

    # ── Search ──────────────────────────────────────────────────────────────
    if args.search:
        results = search(records, args.search)
        _print_results(results, root)

        if args.open is not None:
            idx = args.open - 1
            if 0 <= idx < len(results):
                open_path(results[idx]["path"])
            else:
                print(f"Invalid result number: {args.open}")
        elif args.reveal is not None:
            idx = args.reveal - 1
            if 0 <= idx < len(results):
                open_in_finder(results[idx]["path"])
        elif sys.stdin.isatty():
            path = _prompt_pick(results)
            if path:
                open_path(path)
    else:
        # No query — print a summary of what's indexed
        categories: Dict[str, int] = {}
        years: Dict[str, int] = {}
        for r in records:
            categories[r["category"]] = categories.get(r["category"], 0) + 1
            if r.get("year"):
                years[r["year"]] = years.get(r["year"], 0) + 1

        print(f"\nDrive: {root}")
        print(f"Index: {len(records)} documents  (use --search to query)\n")

        print("By category:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"  {cat:<20}  {count:>4} docs")

        if years:
            print("\nBy year:")
            for yr in sorted(years, reverse=True)[:8]:
                print(f"  {yr}  {years[yr]:>4} docs")
        print()


if __name__ == "__main__":
    main()
