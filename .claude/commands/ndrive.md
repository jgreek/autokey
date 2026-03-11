# Network Drive Traversal Skill

You are helping the user work with a slow remote network drive (e.g. Windows N: drive or UNC path).
The drive is slow because it is remote, so minimize live traversals and use a local cache whenever possible.

## Arguments

The user's request is: $ARGUMENTS

Parse the intent from their request:
- **index** [path]: Build or refresh the local cache for the given path (default: configured root)
- **search** [pattern]: Search the cached index for files/folders matching a name or glob
- **find** [pattern]: Alias for search
- **ls** [path]: List directory contents from cache (fast) with option to live-refresh
- **refresh** [path]: Re-scan a specific sub-path and update the cache
- **stats**: Show cache statistics (last updated, file count, size breakdown)
- **open** [path]: Open a cached path in the file manager
- Anything else: interpret as a search query against the cache

## How to respond

1. **Use the helper script** `commands/ndrive_cache.py` to perform all cache operations.
   Run it via Bash: `python commands/ndrive_cache.py <subcommand> [args]`

2. **Available subcommands** (pass to the script):
   - `python commands/ndrive_cache.py build <root_path>` — crawls the drive and writes cache
   - `python commands/ndrive_cache.py search <pattern>` — regex/glob search in cached index
   - `python commands/ndrive_cache.py ls <path>` — list a directory from cache
   - `python commands/ndrive_cache.py refresh <path>` — re-crawl one directory subtree
   - `python commands/ndrive_cache.py stats` — show cache info
   - `python commands/ndrive_cache.py export` — dump full path list to stdout

3. **Cache location**: `.ndrive_cache.json` in the project root (or `~/.ndrive_cache.json` as fallback).
   The cache stores: path, type (file/dir), size, mtime, depth.

4. **When the cache is empty or stale** (older than 24 hours):
   - Warn the user the cache may be outdated
   - Offer to run `build` in the background (it can take time on slow drives)
   - Show partial results from what is cached

5. **Handling slow drives**:
   - The build command uses per-directory timeouts (default 10s) — directories that time out
     are marked as `partial` in the cache and skipped
   - Use `--timeout` to adjust: `python commands/ndrive_cache.py build N:\ --timeout 15`
   - Parallel workers (default 4) speed up indexing; use `--workers` to tune

6. **Format output clearly**:
   - For search results: show relative path, type, size, last modified
   - For directory listings: tree-style with file counts and sizes
   - For stats: show last build time, total files, total dirs, partial dirs, cache file size

7. **Common workflows to suggest**:
   - First time: `build` the index (run once, takes a while)
   - Daily use: `search` and `ls` against the cache (instant)
   - After changes on drive: `refresh <changed_subfolder>` (fast, targeted)
   - Weekly: rebuild full index

## Example interactions

User: "find all PDFs in the reports folder"
→ Run: `python commands/ndrive_cache.py search "reports.*\.pdf$"`

User: "what's in N:\Finance\2024"
→ Run: `python commands/ndrive_cache.py ls "N:\\Finance\\2024"`

User: "index the N drive"
→ Run: `python commands/ndrive_cache.py build "N:\\"`

User: "how stale is the cache"
→ Run: `python commands/ndrive_cache.py stats`
