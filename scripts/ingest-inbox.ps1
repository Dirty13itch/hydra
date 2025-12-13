# ingest-inbox.ps1
# Moves files from _inbox into canonical system-reality folder,
# updates LATEST_SNAPSHOT.md, and commits to git.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Get-Location
$inbox = Join-Path $repoRoot "_inbox"
$dest  = Join-Path $repoRoot "docs\canonical\00-system-reality"
$latestFile = Join-Path $dest "LATEST_SNAPSHOT.md"

Write-Host "Repo root: $repoRoot"
Write-Host "Inbox:     $inbox"
Write-Host "Dest:      $dest"

New-Item -ItemType Directory -Force -Path $inbox | Out-Null
New-Item -ItemType Directory -Force -Path $dest  | Out-Null

$items = Get-ChildItem -Path $inbox -File -ErrorAction SilentlyContinue

if (-not $items) {
  Write-Host "Inbox is empty. Nothing to ingest."
  Write-Host "Press Enter to exit."
  Read-Host | Out-Null
  exit 0
}

foreach ($i in $items) {
  $target = Join-Path $dest $i.Name
  Move-Item -LiteralPath $i.FullName -Destination $target -Force
  Write-Host "MOVED: $($i.Name)"
}

# Update LATEST_SNAPSHOT.md
$latestSnap = Get-ChildItem -Path $dest -Filter "Hydra_Snapshot_*.txt" -ErrorAction SilentlyContinue |
  Sort-Object Name -Descending |
  Select-Object -First 1

if ($latestSnap) {
  $rel = "@docs/canonical/00-system-reality/$($latestSnap.Name)"
  "# Latest Hydra snapshot`n$rel" | Set-Content -LiteralPath $latestFile -Encoding UTF8
  Write-Host "UPDATED: LATEST_SNAPSHOT.md -> $($latestSnap.Name)"
} else {
  Write-Host "No Hydra_Snapshot_*.txt found; LATEST_SNAPSHOT.md unchanged."
}

# Commit to git
git add -A | Out-Null
git commit -m "Ingest canonical artifacts from _inbox" | Out-Null

Write-Host "DONE."
Write-Host "Press Enter to close."
Read-Host | Out-Null
