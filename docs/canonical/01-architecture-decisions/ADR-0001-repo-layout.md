# ADR-0001: Canonical Repository Structure

## Status

Accepted

## Date

2025-12-13

## Context

The Hydra repository had accumulated multiple documentation locations, prototype scripts, and extraction artifacts. This caused confusion for both humans and AI assistants about which files were authoritative and which were experimental.

Problems observed:
- Prototype `.py` and `.ts` files mixed with production scripts
- Multiple overlapping documentation efforts
- Unclear which docs were "truth" vs drafts
- Extraction artifacts from tarballs polluting root

## Decision

Establish a canonical folder structure with clear separation of concerns:

```
hydra/
├── docs/
│   └── canonical/                    # SINGLE SOURCE OF TRUTH
│       ├── 00-system-reality/        # Snapshots, manifests, current state
│       ├── 01-architecture-decisions/ # ADRs (this folder)
│       ├── 02-runbooks/              # Operational procedures
│       ├── 03-network/               # DNS, ingress, network topology
│       ├── 04-storage/               # Backup, restore, data management
│       └── 05-observability/         # Alerts, SLOs, monitoring
├── scripts/                          # Production automation scripts
│   ├── snapshot-hydra.ps1            # Daily cluster snapshot
│   ├── check-drift.ps1               # Drift detection
│   └── ingest-inbox.ps1              # Inbox processing
├── config/                           # Configuration templates
│   └── *.example                     # Example configs (no secrets)
├── knowledge/                        # Reference docs for AI context
├── legacy/                           # Archived/deprecated content
│   ├── patches/                      # Old patch scripts
│   ├── prototypes/                   # Experimental code
│   ├── notes/                        # Old notes
│   └── zips/                         # Archive files
├── _inbox/                           # Drop folder for ingestion
├── CLAUDE.md                         # AI context/instructions
├── README.md                         # Project overview
└── .gitignore                        # Excludes secrets, local configs
```

## Consequences

### Positive

1. **Single source of truth**: All authoritative docs live in `docs/canonical/`
2. **Clear ownership**: Each folder has a defined purpose
3. **AI-friendly**: CLAUDE.md points to canonical docs, reducing hallucination
4. **Safe archival**: Legacy content preserved but clearly separated
5. **Script organization**: Production scripts in `scripts/`, prototypes in `legacy/`

### Negative

1. **Migration effort**: Required moving files and updating references
2. **Learning curve**: Contributors must learn the new structure
3. **Potential breakage**: Any hardcoded paths to moved files will break

### Mitigations

- Files moved, not deleted (recoverable from `legacy/`)
- ADR documents the structure for future reference
- Commit history preserves original locations

## Alternatives Considered

### 1. Flat structure with naming conventions

Rejected: Doesn't scale, still causes confusion.

### 2. Single `docs/` folder with prefixed files

Rejected: Becomes unwieldy as documentation grows.

### 3. Separate repo for docs

Rejected: Adds friction, docs should live with code.

## Related Documents

- `docs/canonical/00-system-reality/LATEST_SNAPSHOT.md` - Current cluster state
- `docs/canonical/02-runbooks/task-scheduler.md` - Automation setup
- `CLAUDE.md` - AI assistant context

---

*ADR template based on Michael Nygard's format*
