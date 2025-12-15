# Rule: Context Size Guard

**Priority:** HIGH

## Do NOT Auto-Load Large Files

Files over 40KB should NOT be referenced with `@` in CLAUDE.md.

### Excluded from Auto-Load

- `HYDRA_FILE_MANIFEST.csv` (124KB) - Query on demand
- `Hydra_Snapshot_*.txt` (16KB+) - Query on demand
- Session logs - Archive, don't auto-load

### Safe to Auto-Load

- `LATEST_SNAPSHOT.md` (pointer file, <1KB)
- Individual knowledge files (<15KB each)
- Rules files (<2KB each)

## If You Need Large File Data

```bash
# Query manifest for specific info
grep "pattern" docs/canonical/00-system-reality/HYDRA_FILE_MANIFEST.csv

# Read snapshot on demand
cat docs/canonical/00-system-reality/Hydra_Snapshot_*.txt
```

## Session Log Management

Session logs grow unbounded. Archive them periodically:

1. Move completed session notes to `docs/session-archive/`
2. Keep only current session in CLAUDE.md
3. Never auto-load archived sessions
