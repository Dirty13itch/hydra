# Claude Code Instruction Refactoring - December 14, 2025

## Purpose

Refactored the Hydra repo's Claude instruction files to improve Claude Code performance and correctness by:
1. Eliminating auto-loading of large files
2. Splitting monolithic instructions into focused rule files
3. Adding self-guarding rules to prevent common mistakes
4. Organizing reference documentation properly

---

## Summary of Changes

### Context Size Reduction

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| Project CLAUDE.md | 14KB | 2KB | 86% |
| Global CLAUDE.md | 23KB | 4KB | 83% |
| Auto-loaded files | 152KB+ | 0KB | 100% |
| **Total context** | **189KB** | **6KB** | **97%** |

---

## Detailed Changes

### 1. Project CLAUDE.md Slimmed Down

**Removed auto-loads:**
- `@docs/canonical/00-system-reality/HYDRA_FILE_MANIFEST.csv` (124KB)
- `@docs/canonical/00-system-reality/HYDRA_FULL_FILE_ANALYSIS_AND_RECONCILIATION.md` (9KB)
- `@docs/canonical/00-system-reality/HYDRA_SERVICE_RECONCILIATION_MATRIX.md` (3KB)
- `@docs/canonical/00-system-reality/LATEST_SNAPSHOT.md` (pointer to 16KB file)

**Removed inline content:**
- Phase 11/12 technical documentation (moved to `docs/`)
- Session log (~170 lines, moved to `docs/session-archive/`)

### 2. Created Self-Guarding Rules

New files in `.claude/rules/`:

| File | Size | Purpose |
|------|------|---------|
| `01-discovery-before-action.md` | 1KB | Read knowledge files first |
| `02-canonical-ips.md` | <1KB | Correct IPs, deprecated IP warnings |
| `03-nixos-declarative.md` | <1KB | NixOS configuration rules |
| `04-gpu-power-limits.md` | <1KB | Power/VRAM constraints |
| `05-test-before-commit.md` | <1KB | Validation requirements |
| `06-context-size-guard.md` | <1KB | Prevent large file auto-load |

### 3. Extracted Session Logs

| Location | File | Content |
|----------|------|---------|
| Project | `docs/session-archive/2025-12-session-log.md` | Dec 2025 session notes |
| Global | `~/.claude/session-archive/2025-12-global-session-log.md` | Global session history |

### 4. Created Phase Documentation

| File | Size | Content |
|------|------|---------|
| `docs/phase-11-self-improvement.md` | 2.5KB | Self-improvement tools API |
| `docs/phase-12-character-consistency.md` | 1.7KB | Character consistency system |

### 5. Optimized Global CLAUDE.md

| File | Purpose |
|------|---------|
| `~/.claude/CLAUDE.md` | Now slim version (4KB) |
| `~/.claude/CLAUDE.md.original-backup-20251214` | Original backup (23KB) |
| `~/.claude/CLAUDE.md.slim` | Slim template |
| `~/.claude/secrets-reference.md` | Extracted secrets (NOT auto-loaded) |

### 6. Organized Root Directory

Moved large reference files to `docs/reference/`:

| File | Size | Original Location |
|------|------|-------------------|
| `ARCHITECTURE.md` | 52KB | Root |
| `DEVELOPMENT-PLAN.md` | 27KB | Root |
| `LEARNINGS.md` | 19KB | Root |
| `HYDRA-MASTER-SYNTHESIS.md` | 18KB | Root |
| `HYDRA-SETUP-GUIDE.md` | 6KB | Root |

**Still in root (appropriate for visibility):**
- `README.md` (2KB)
- `ROADMAP.md` (23KB)
- `CLAUDE.md` (2KB)
- `VISION.md` (7KB)
- `STATE.json` (6KB)
- `STRUCTURE.md` (11KB)
- `DEPLOYMENT-CHECKLIST.md` (9KB)

### 7. Created Index Files

| File | Purpose |
|------|---------|
| `.claude/knowledge-index.md` | Quick reference for all knowledge files |
| `.claude/REFACTORING-CHANGELOG.md` | This file |

---

## New File Structure

```
hydra/
├── .claude/
│   ├── commands/
│   │   └── phase1-deploy.md          # Slash command
│   ├── rules/
│   │   ├── 01-discovery-before-action.md
│   │   ├── 02-canonical-ips.md
│   │   ├── 03-nixos-declarative.md
│   │   ├── 04-gpu-power-limits.md
│   │   ├── 05-test-before-commit.md
│   │   └── 06-context-size-guard.md
│   ├── knowledge-index.md
│   ├── REFACTORING-CHANGELOG.md
│   └── settings.local.json
├── docs/
│   ├── reference/                     # Moved large files
│   │   ├── ARCHITECTURE.md
│   │   ├── DEVELOPMENT-PLAN.md
│   │   ├── HYDRA-MASTER-SYNTHESIS.md
│   │   ├── HYDRA-SETUP-GUIDE.md
│   │   └── LEARNINGS.md
│   ├── session-archive/
│   │   └── 2025-12-session-log.md
│   ├── phase-11-self-improvement.md
│   └── phase-12-character-consistency.md
├── knowledge/                         # Unchanged
│   ├── automation.md
│   ├── databases.md
│   ├── infrastructure.md
│   └── ... (9 files, ~97KB total)
├── CLAUDE.md                          # Slim (2KB)
├── README.md
├── ROADMAP.md
└── ...

~/.claude/
├── CLAUDE.md                          # Slim version active (4KB)
├── CLAUDE.md.original-backup-20251214 # Original backup (23KB)
├── CLAUDE.md.slim                     # Template
├── secrets-reference.md               # Extracted secrets
└── session-archive/
    └── 2025-12-global-session-log.md
```

---

## Rollback Instructions

If issues occur, restore originals:

```bash
# Restore global CLAUDE.md
cp ~/.claude/CLAUDE.md.original-backup-20251214 ~/.claude/CLAUDE.md

# Restore root files (from docs/reference/)
cd ~/projects/hydra
mv docs/reference/ARCHITECTURE.md .
mv docs/reference/DEVELOPMENT-PLAN.md .
mv docs/reference/LEARNINGS.md .
mv docs/reference/HYDRA-MASTER-SYNTHESIS.md .
mv docs/reference/HYDRA-SETUP-GUIDE.md .
```

---

## Recommendations

1. **Secrets Migration**: Move secrets from `~/.claude/secrets-reference.md` to SOPS-encrypted files
2. **Session Log Hygiene**: Archive session logs monthly, don't let them grow unbounded
3. **Knowledge File Maintenance**: Keep individual knowledge files under 15KB

---

*Refactoring completed: December 14, 2025*
