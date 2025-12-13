# Hydra Repo Organizer v1
# Safe organizer: creates canonical folders and moves likely-legacy items to /legacy.
# Run from repo root.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Dir($path) {
  if (-not (Test-Path -LiteralPath $path)) {
    New-Item -ItemType Directory -Path $path | Out-Null
  }
}

function Safe-Move($source, $destDir) {
  if (-not (Test-Path -LiteralPath $source)) { return $false }

  Ensure-Dir $destDir

  $name = Split-Path -Leaf $source
  $dest = Join-Path $destDir $name

  if (Test-Path -LiteralPath $dest) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $dest = Join-Path $destDir ("{0}_moved_{1}" -f $name, $stamp)
  }

  Move-Item -LiteralPath $source -Destination $dest
  return $true
}

function Safe-Copy($source, $destDir) {
  if (-not (Test-Path -LiteralPath $source)) { return $false }

  Ensure-Dir $destDir

  $name = Split-Path -Leaf $source
  $dest = Join-Path $destDir $name

  if (Test-Path -LiteralPath $dest) {
    # Don't overwrite; keep existing.
    return $false
  }

  Copy-Item -LiteralPath $source -Destination $dest
  return $true
}

# ----- Confirm we're in a repo-ish folder (soft check) -----
$here = (Get-Location).Path
Write-Host "Hydra Organizer running in: $here"

# ----- Canonical folder structure -----
$canonicalRoot = "docs\canonical"
$dirs = @(
  "docs",
  "docs\canonical",
  "docs\canonical\00-system-reality",
  "docs\canonical\01-architecture-decisions",
  "docs\canonical\02-runbooks",
  "docs\canonical\03-network",
  "docs\canonical\04-storage",
  "docs\canonical\05-observability",
  "docs\canonical\06-ai-platform",
  "legacy",
  "legacy\zips",
  "legacy\prototypes",
  "legacy\notes",
  "scripts"
)

foreach ($d in $dirs) { Ensure-Dir $d }

# ----- Put “canonical artifacts” where Claude can always see them -----
# If these files exist in the repo root (or wherever you dropped them), we copy them into docs/canonical/00-system-reality.
$systemRealityDir = "docs\canonical\00-system-reality"

$canonicalFiles = @(
  "Hydra_Snapshot_20251212_222505.txt",
  "HYDRA_FULL_FILE_ANALYSIS_AND_RECONCILIATION.md",
  "HYDRA_SERVICE_RECONCILIATION_MATRIX.md",
  "HYDRA_FILE_MANIFEST.csv"
)

$copied = @()
foreach ($f in $canonicalFiles) {
  if (Safe-Copy ".\$f" $systemRealityDir) { $copied += $f }
}

# Create/refresh a pointer file for “latest snapshot”
$latestSnap = Get-ChildItem -LiteralPath $systemRealityDir -Filter "Hydra_Snapshot_*.txt" -ErrorAction SilentlyContinue |
  Sort-Object Name -Descending |
  Select-Object -First 1

$latestFile = "docs\canonical\00-system-reality\LATEST_SNAPSHOT.md"
if ($latestSnap) {
  $rel = "@" + ($latestSnap.FullName.Replace($here + "\", "") -replace "\\","/")
  @(
    "# Latest Hydra snapshot",
    $rel
  ) | Set-Content -LiteralPath $latestFile -Encoding UTF8
} else {
  @(
    "# Latest Hydra snapshot",
    "_No snapshot file found yet. Drop Hydra_Snapshot_*.txt into docs/canonical/00-system-reality/_"
  ) | Set-Content -LiteralPath $latestFile -Encoding UTF8
}

# ----- Ensure CLAUDE.md exists at repo root and points to canonical docs -----
$claudeMd = "CLAUDE.md"
if (-not (Test-Path -LiteralPath $claudeMd)) {
  @"
# Hydra Canonical Context (auto-loaded)

This repository is the canonical source of truth for the Hydra home cluster.

## Latest ground-truth snapshot
@docs/canonical/00-system-reality/LATEST_SNAPSHOT.md

## Full file-level reconciliation report
@docs/canonical/00-system-reality/HYDRA_FULL_FILE_ANALYSIS_AND_RECONCILIATION.md

## Service reconciliation matrix
@docs/canonical/00-system-reality/HYDRA_SERVICE_RECONCILIATION_MATRIX.md

## Full per-file manifest (CSV)
@docs/canonical/00-system-reality/HYDRA_FILE_MANIFEST.csv

## Stable SSH targets
- hydra-storage (Unraid) 192.168.1.244
- hydra-compute (NixOS) 192.168.1.203
- hydra-ai (NixOS) 192.168.1.250

Rules:
- Prefer hostnames (hydra-*) over raw IPs in configs/scripts.
- Keep legacy/prototypes in /legacy. Do not deploy from /legacy.
"@ | Set-Content -LiteralPath $claudeMd -Encoding UTF8
}

# ----- Move “likely legacy” stuff out of the mainline -----
# This is intentionally conservative: it moves obvious prototype/duplicate folders if they exist.
$legacyMoves = @(
  @{ Path="hydra-control-plane-frontend"; Dest="legacy\prototypes" },
  @{ Path="other"; Dest="legacy\prototypes" },
  @{ Path=".claude"; Dest="legacy\notes" } # WARNING: this can be sensitive; moving keeps it out of the repo root
)

$moved = @()
foreach ($item in $legacyMoves) {
  if (Safe-Move $item.Path $item.Dest) { $moved += $item.Path }
}

# Move zip files into legacy/zips if they exist in repo root
Get-ChildItem -LiteralPath . -File -Filter "*.zip" -ErrorAction SilentlyContinue | ForEach-Object {
  if (Safe-Move $_.FullName "legacy\zips") { $moved += $_.Name }
}

# ----- Final summary -----
Write-Host ""
Write-Host "=== DONE ==="
Write-Host "Created canonical structure under: docs\canonical\"
Write-Host "Copied canonical files into: $systemRealityDir"
if ($copied.Count -gt 0) {
  Write-Host "Copied:"; $copied | ForEach-Object { Write-Host "  - $_" }
} else {
  Write-Host "Copied: (none found in repo root; drop the files in repo root and rerun, or copy manually)"
}

if ($moved.Count -gt 0) {
  Write-Host "Moved to legacy:"; $moved | ForEach-Object { Write-Host "  - $_" }
} else {
  Write-Host "Moved to legacy: (none found)"
}

Write-Host "Wrote/updated: docs\canonical\00-system-reality\LATEST_SNAPSHOT.md"
Write-Host "Ensured: CLAUDE.md at repo root"
Write-Host ""
Write-Host "Next: open Claude Code in THIS repo folder so it reads CLAUDE.md automatically."
