#!/usr/bin/env python3
"""
ndrive_cache.py — Local cache for slow remote/network drives.

Traverses a network drive once and stores a JSON index locally so that
subsequent searches and directory listings are instant, without hitting
the slow remote filesystem.

Usage:
    python commands/ndrive_cache.py build   <root_path> [--timeout N] [--workers N]
    python commands/ndrive_cache.py search  <pattern>   [--type file|dir] [--limit N]
    python commands/ndrive_cache.py ls      <path>      [--depth N]
    python commands/ndrive_cache.py refresh <path>      [--timeout N] [--workers N]
    python commands/ndrive_cache.py stats
    python commands/ndrive_cache.py export
"""

import argparse
import fnmatch
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Cache location: project root first, then home dir as fallback
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent.parent
_CACHE_CANDIDATES = [
    _SCRIPT_DIR / ".ndrive_cache.json",
    Path.home() / ".ndrive_cache.json",
]


def _cache_path() -> Path:
    for p in _CACHE_CANDIDATES:
        if p.exists():
            return p
    # Default: project root
    return _CACHE_CANDIDATES[0]


# ---------------------------------------------------------------------------
# Cache schema
# {
#   "meta": {
#     "root": "N:\\",
#     "built_at": "<iso timestamp>",
#     "partial_dirs": ["N:\\slow_subdir", ...]
#   },
#   "entries": {
#     "N:\\Finance\\report.pdf": {
#       "type": "file",
#       "size": 12345,
#       "mtime": 1710000000.0,
#       "depth": 2
#     },
#     "N:\\Finance": {
#       "type": "dir",
#       "size": 0,
#       "mtime": 1710000000.0,
#       "depth": 1
#     }
#   }
# }
# ---------------------------------------------------------------------------


def load_cache() -> dict:
    p = _cache_path()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"meta": {}, "entries": {}}


def save_cache(cache: dict) -> None:
    p = _cache_path()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)
    print(f"[ndrive] Cache saved to {p}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Build / crawl
# ---------------------------------------------------------------------------

def _stat_entry(full_path: str, root_path: str, timeout: float) -> dict | None:
    """Return a cache entry dict or None on failure."""
    try:
        st = os.stat(full_path, follow_symlinks=False)
        depth = len(Path(full_path).relative_to(root_path).parts)
        return {
            "type": "dir" if os.path.isdir(full_path) else "file",
            "size": st.st_size,
            "mtime": st.st_mtime,
            "depth": depth,
        }
    except OSError:
        return None


def _scan_directory(dir_path: str, root_path: str, timeout: float) -> tuple[list[str], bool]:
    """
    List immediate children of dir_path.
    Returns (children_paths, timed_out).
    """
    children = []
    timed_out = False
    deadline = time.monotonic() + timeout
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if time.monotonic() > deadline:
                    timed_out = True
                    break
                children.append(entry.path)
    except (PermissionError, OSError):
        pass
    return children, timed_out


def build_cache(root_path: str, timeout: float = 10.0, workers: int = 4) -> dict:
    """
    Walk root_path and build a fresh cache.  Each directory scan is bounded
    by `timeout` seconds; slow/hanging dirs are skipped and flagged.
    """
    root_path = str(Path(root_path).resolve()) if not root_path.startswith("\\\\") else root_path

    print(f"[ndrive] Building index for {root_path} (timeout={timeout}s, workers={workers})", file=sys.stderr)
    t0 = time.monotonic()

    entries: dict[str, dict] = {}
    partial_dirs: list[str] = []

    # BFS queue
    queue: list[str] = [root_path]
    visited: set[str] = set()

    def process_dir(dir_path: str):
        children, timed_out = _scan_directory(dir_path, root_path, timeout)
        results = []
        for child in children:
            entry = _stat_entry(child, root_path, timeout)
            if entry:
                results.append((child, entry))
                if entry["type"] == "dir":
                    results.append(("__queue__", child))
        return dir_path, results, timed_out

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        # Seed with root
        futures[pool.submit(process_dir, root_path)] = root_path
        visited.add(root_path)

        while futures:
            done_futures = list(as_completed(futures, timeout=timeout + 5))
            for fut in done_futures:
                dir_path = futures.pop(fut)
                try:
                    _, results, timed_out = fut.result(timeout=0)
                except Exception:
                    timed_out = True
                    results = []

                if timed_out:
                    partial_dirs.append(dir_path)
                    print(f"[ndrive]   TIMEOUT: {dir_path}", file=sys.stderr)

                for key, val in results:
                    if key == "__queue__":
                        subdir = val
                        if subdir not in visited:
                            visited.add(subdir)
                            futures[pool.submit(process_dir, subdir)] = subdir
                    else:
                        entries[key] = val

    elapsed = time.monotonic() - t0
    print(
        f"[ndrive] Done in {elapsed:.1f}s: {len(entries)} entries, {len(partial_dirs)} partial dirs",
        file=sys.stderr,
    )

    cache = {
        "meta": {
            "root": root_path,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "partial_dirs": partial_dirs,
        },
        "entries": entries,
    }
    return cache


# ---------------------------------------------------------------------------
# Refresh a subtree
# ---------------------------------------------------------------------------

def refresh_cache(cache: dict, path: str, timeout: float = 10.0, workers: int = 4) -> dict:
    """Re-crawl `path` and merge results back into existing cache."""
    root = cache.get("meta", {}).get("root", path)
    print(f"[ndrive] Refreshing {path} ...", file=sys.stderr)

    # Remove stale entries under path
    prefix = path if path.endswith(os.sep) else path + os.sep
    stale_keys = [k for k in cache["entries"] if k == path or k.startswith(prefix)]
    for k in stale_keys:
        del cache["entries"][k]

    # Also remove from partial_dirs
    cache["meta"].setdefault("partial_dirs", [])
    cache["meta"]["partial_dirs"] = [
        p for p in cache["meta"]["partial_dirs"]
        if not (p == path or p.startswith(prefix))
    ]

    # Re-crawl the subtree
    sub_cache = build_cache(path, timeout=timeout, workers=workers)
    cache["entries"].update(sub_cache["entries"])
    cache["meta"]["partial_dirs"].extend(sub_cache["meta"].get("partial_dirs", []))
    cache["meta"]["refreshed_at"] = datetime.now(timezone.utc).isoformat()
    return cache


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_cache(cache: dict, pattern: str, entry_type: str | None = None, limit: int = 200) -> list[dict]:
    """
    Search cached entries by name or path using regex (or glob converted to regex).
    `pattern` may be a glob (contains * or ?) or a plain regex.
    """
    # Convert glob-style to regex if no regex special chars beyond * and ?
    if re.search(r"[^*?\w\s\-./\\]", pattern) is None and ("*" in pattern or "?" in pattern):
        pattern = fnmatch.translate(pattern)

    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        rx = re.compile(re.escape(pattern), re.IGNORECASE)

    results = []
    for path, entry in cache.get("entries", {}).items():
        if entry_type and entry["type"] != entry_type:
            continue
        if rx.search(path):
            results.append({"path": path, **entry})
        if len(results) >= limit:
            break

    results.sort(key=lambda e: e["path"])
    return results


# ---------------------------------------------------------------------------
# List directory
# ---------------------------------------------------------------------------

def ls_cache(cache: dict, path: str, depth: int = 1) -> list[dict]:
    """Return direct children (up to `depth` levels) of `path` from cache."""
    path = path.rstrip(os.sep)
    prefix = path + os.sep
    target_depth_base = cache["entries"].get(path, {}).get("depth", 0)

    results = []
    for entry_path, entry in cache.get("entries", {}).items():
        if entry_path.startswith(prefix):
            relative_depth = entry["depth"] - target_depth_base
            if 1 <= relative_depth <= depth:
                results.append({"path": entry_path, **entry})

    results.sort(key=lambda e: (e["type"] != "dir", e["path"]))
    return results


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def cache_stats(cache: dict) -> dict:
    meta = cache.get("meta", {})
    entries = cache.get("entries", {})

    file_entries = [e for e in entries.values() if e["type"] == "file"]
    dir_entries = [e for e in entries.values() if e["type"] == "dir"]

    total_size = sum(e["size"] for e in file_entries)

    built_at = meta.get("built_at", "never")
    if built_at != "never":
        dt = datetime.fromisoformat(built_at)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        age_str = f"{age_hours:.1f}h ago"
        stale = age_hours > 24
    else:
        age_str = "never built"
        stale = True

    cache_file = _cache_path()
    cache_file_size = cache_file.stat().st_size if cache_file.exists() else 0

    return {
        "root": meta.get("root", "unknown"),
        "built_at": built_at,
        "age": age_str,
        "stale": stale,
        "total_files": len(file_entries),
        "total_dirs": len(dir_entries),
        "partial_dirs": len(meta.get("partial_dirs", [])),
        "total_size_bytes": total_size,
        "cache_file": str(cache_file),
        "cache_file_bytes": cache_file_size,
    }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def print_results(results: list[dict], show_size: bool = True) -> None:
    if not results:
        print("No results found.")
        return
    for r in results:
        kind = "DIR " if r["type"] == "dir" else "FILE"
        size = _human_size(r["size"]) if show_size and r["type"] == "file" else "     "
        mtime = _fmt_mtime(r["mtime"]) if r.get("mtime") else "          "
        print(f"  [{kind}] {r['path']:<80} {size:>10}  {mtime}")


def print_stats(stats: dict) -> None:
    stale_flag = " *** STALE (>24h) ***" if stats["stale"] else ""
    print(f"  Root:          {stats['root']}")
    print(f"  Built at:      {stats['built_at']}  ({stats['age']}){stale_flag}")
    print(f"  Files:         {stats['total_files']:,}")
    print(f"  Directories:   {stats['total_dirs']:,}")
    print(f"  Partial dirs:  {stats['partial_dirs']}  (timed out during scan)")
    print(f"  Total size:    {_human_size(stats['total_size_bytes'])}")
    print(f"  Cache file:    {stats['cache_file']}  ({_human_size(stats['cache_file_bytes'])})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Local cache for slow remote/network drives.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # build
    p_build = sub.add_parser("build", help="Crawl root_path and build cache")
    p_build.add_argument("root_path", help="Root path of the network drive, e.g. N:\\ or \\\\server\\share")
    p_build.add_argument("--timeout", type=float, default=10.0, help="Per-directory timeout in seconds")
    p_build.add_argument("--workers", type=int, default=4, help="Parallel worker threads")

    # search / find
    for cmd_name in ("search", "find"):
        p_s = sub.add_parser(cmd_name, help="Search cached index by name/pattern")
        p_s.add_argument("pattern", help="Regex or glob pattern to match against full paths")
        p_s.add_argument("--type", choices=["file", "dir"], dest="entry_type", default=None)
        p_s.add_argument("--limit", type=int, default=200)

    # ls
    p_ls = sub.add_parser("ls", help="List directory from cache")
    p_ls.add_argument("path", help="Directory path to list")
    p_ls.add_argument("--depth", type=int, default=1, help="How many levels deep to show")

    # refresh
    p_ref = sub.add_parser("refresh", help="Re-crawl a subtree and update cache")
    p_ref.add_argument("path", help="Subtree to refresh")
    p_ref.add_argument("--timeout", type=float, default=10.0)
    p_ref.add_argument("--workers", type=int, default=4)

    # stats
    sub.add_parser("stats", help="Show cache statistics")

    # export
    p_exp = sub.add_parser("export", help="Dump all cached paths to stdout")
    p_exp.add_argument("--type", choices=["file", "dir"], dest="entry_type", default=None)

    args = parser.parse_args()

    if args.cmd == "build":
        cache = build_cache(args.root_path, timeout=args.timeout, workers=args.workers)
        save_cache(cache)
        print("\nIndex complete:")
        print_stats(cache_stats(cache))

    elif args.cmd in ("search", "find"):
        cache = load_cache()
        if not cache["entries"]:
            print("Cache is empty. Run: python commands/ndrive_cache.py build <root_path>")
            sys.exit(1)
        results = search_cache(cache, args.pattern, entry_type=args.entry_type, limit=args.limit)
        print(f"Found {len(results)} result(s) for pattern '{args.pattern}':")
        print_results(results)

    elif args.cmd == "ls":
        cache = load_cache()
        if not cache["entries"]:
            print("Cache is empty. Run: python commands/ndrive_cache.py build <root_path>")
            sys.exit(1)
        results = ls_cache(cache, args.path, depth=args.depth)
        print(f"Listing: {args.path}  ({len(results)} items)")
        print_results(results)

    elif args.cmd == "refresh":
        cache = load_cache()
        cache = refresh_cache(cache, args.path, timeout=args.timeout, workers=args.workers)
        save_cache(cache)
        print_stats(cache_stats(cache))

    elif args.cmd == "stats":
        cache = load_cache()
        if not cache["meta"]:
            print("No cache found. Run: python commands/ndrive_cache.py build <root_path>")
        else:
            print_stats(cache_stats(cache))

    elif args.cmd == "export":
        cache = load_cache()
        for path, entry in sorted(cache.get("entries", {}).items()):
            if args.entry_type is None or entry["type"] == args.entry_type:
                print(path)


if __name__ == "__main__":
    main()
