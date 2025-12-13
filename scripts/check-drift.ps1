<#
.SYNOPSIS
    Hydra Cluster Drift Detection Script
.DESCRIPTION
    Compares the latest snapshot to the previous one and generates a drift report.
    Detects changes in: IPs, ports, containers, GPU status, mounts.
.NOTES
    Author: Hydra Steward
    Version: 1.0.0
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Configuration
$repoRoot = Split-Path -Parent $PSScriptRoot
$snapshotDir = Join-Path $repoRoot "docs\canonical\00-system-reality"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$driftFile = Join-Path $snapshotDir "DRIFT_REPORT_$timestamp.md"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] [$Level] $Message"
}

# Find the two most recent snapshots
$snapshots = Get-ChildItem -Path $snapshotDir -Filter "Hydra_Snapshot_*.txt" -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    Select-Object -First 2

if ($snapshots.Count -lt 2) {
    Write-Log "Need at least 2 snapshots to detect drift. Found: $($snapshots.Count)" -Level "WARN"

    $content = @"
# Drift Report - $timestamp

**Status:** Insufficient data

Only $($snapshots.Count) snapshot(s) found. Need at least 2 snapshots to compare.

Run ``snapshot-hydra.ps1`` to collect more snapshots.
"@
    $content | Out-File -FilePath $driftFile -Encoding UTF8
    Write-Log "Drift report saved: $driftFile"
    exit 0
}

$latestFile = $snapshots[0].FullName
$previousFile = $snapshots[1].FullName

Write-Log "Comparing snapshots:"
Write-Log "  Latest:   $($snapshots[0].Name)"
Write-Log "  Previous: $($snapshots[1].Name)"

$latest = Get-Content $latestFile -Raw
$previous = Get-Content $previousFile -Raw

# Extract sections for comparison
function Get-Section {
    param([string]$Content, [string]$Section)
    if ($Content -match "-----BEGIN $Section-----([\s\S]*?)-----END $Section-----") {
        return $Matches[1].Trim()
    }
    return ""
}

function Get-NodeSections {
    param([string]$Content, [string]$NodeLabel)
    $result = @{}
    if ($Content -match "=====BEGIN NODE\|label=$NodeLabel[\s\S]*?=====([\s\S]*?)=====END NODE\|label=$NodeLabel=====") {
        $nodeContent = $Matches[1]
        $sections = @("NETWORK", "PORTS", "DOCKER_PS", "GPU", "DF", "NFS_MOUNTS")
        foreach ($section in $sections) {
            $result[$section] = Get-Section -Content $nodeContent -Section $section
        }
    }
    return $result
}

# Compare function
function Compare-Sections {
    param([string]$Name, [string]$Old, [string]$New)

    $changes = @()

    if ($Old -ne $New) {
        $oldLines = ($Old -split "`n") | Where-Object { $_ -match '\S' }
        $newLines = ($New -split "`n") | Where-Object { $_ -match '\S' }

        $added = $newLines | Where-Object { $_ -notin $oldLines }
        $removed = $oldLines | Where-Object { $_ -notin $newLines }

        if ($added.Count -gt 0 -or $removed.Count -gt 0) {
            $changes += "### $Name"
            if ($added.Count -gt 0) {
                $changes += "**Added:**"
                $changes += "``````"
                $changes += ($added | Select-Object -First 10)
                if ($added.Count -gt 10) { $changes += "... and $($added.Count - 10) more" }
                $changes += "``````"
            }
            if ($removed.Count -gt 0) {
                $changes += "**Removed:**"
                $changes += "``````"
                $changes += ($removed | Select-Object -First 10)
                if ($removed.Count -gt 10) { $changes += "... and $($removed.Count - 10) more" }
                $changes += "``````"
            }
            $changes += ""
        }
    }

    return $changes
}

# Build drift report
$driftItems = @()
$nodes = @("hydra-compute-nixos", "hydra-ai-nixos", "hydra-storage-unraid")

foreach ($node in $nodes) {
    $oldSections = Get-NodeSections -Content $previous -NodeLabel $node
    $newSections = Get-NodeSections -Content $latest -NodeLabel $node

    foreach ($section in @("NETWORK", "PORTS", "DOCKER_PS", "GPU", "DF", "NFS_MOUNTS")) {
        $changes = Compare-Sections -Name "$node / $section" `
            -Old ($oldSections[$section] ?? "") `
            -New ($newSections[$section] ?? "")

        if ($changes.Count -gt 0) {
            $driftItems += $changes
        }
    }
}

# Generate report
$reportContent = @"
# Drift Report - $timestamp

**Comparing:**
- Latest: ``$($snapshots[0].Name)``
- Previous: ``$($snapshots[1].Name)``

---

"@

if ($driftItems.Count -eq 0) {
    $reportContent += @"
## Status: No Significant Drift Detected

The cluster configuration appears stable between snapshots.

### Sections Compared
- Network interfaces and routes
- Listening ports
- Docker containers
- GPU status
- Disk usage
- NFS mounts
"@
} else {
    $reportContent += @"
## Status: Drift Detected

The following changes were detected between snapshots:

$($driftItems -join "`n")

---

### Recommended Actions

1. Review the changes above
2. Determine if changes are expected (deployments, updates)
3. Update canonical documentation if changes are intentional
4. Investigate unexpected changes
"@
}

$reportContent += @"

---

*Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")*
"@

$reportContent | Out-File -FilePath $driftFile -Encoding UTF8
Write-Log "Drift report saved: $driftFile"

# Git commit
try {
    Push-Location $repoRoot
    git add "docs/canonical/00-system-reality/DRIFT_REPORT_$timestamp.md"
    $commitMsg = "drift: Hydra drift report $timestamp"
    git commit -m $commitMsg 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Git commit successful: $commitMsg"
    } else {
        Write-Log "Git commit skipped (no changes or error)" -Level "WARN"
    }
}
catch {
    Write-Log "Git commit failed: $($_.Exception.Message)" -Level "ERROR"
}
finally {
    Pop-Location
}

Write-Log "Drift check complete!"
