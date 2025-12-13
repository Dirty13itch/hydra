<#
.SYNOPSIS
    Hydra Cluster Snapshot Automation Script
.DESCRIPTION
    Collects standardized snapshots from all Hydra cluster nodes via SSH,
    saves to canonical docs folder, updates LATEST_SNAPSHOT.md, and commits to git.
.NOTES
    Author: Hydra Steward
    Version: 1.0.0
    Requires: SSH access configured for hydra-compute, hydra-ai, hydra-storage
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"  # Continue on errors to collect all nodes

# Configuration
$repoRoot = Split-Path -Parent $PSScriptRoot
$destDir = Join-Path $repoRoot "docs\canonical\00-system-reality"
$latestFile = Join-Path $destDir "LATEST_SNAPSHOT.md"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$isoTimestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$outputFile = Join-Path $destDir "Hydra_Snapshot_$timestamp.txt"

# SSH options for non-interactive, safe execution
$sshOpts = "-o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new"

# Node definitions
$nodes = @(
    @{
        Name = "hydra-compute"
        Label = "hydra-compute-nixos"
        Host = "hydra-compute"
        User = "typhon"
        OS = "NixOS"
    },
    @{
        Name = "hydra-ai"
        Label = "hydra-ai-nixos"
        Host = "hydra-ai"
        User = "typhon"
        OS = "NixOS"
    },
    @{
        Name = "hydra-storage"
        Label = "hydra-storage-unraid"
        Host = "hydra-storage"
        User = "root"
        OS = "Unraid"
    }
)

# Command definitions for each section
$snapshotCommands = @(
    @{
        Section = "OS_IDENTITY"
        NixOS = "hostname; date -Is; uname -a; nixos-version 2>/dev/null || echo 'nixos-version not available'"
        Unraid = "hostname; date -Is; uname -a; cat /etc/unraid-version 2>/dev/null || echo 'version file not found'"
    },
    @{
        Section = "UPTIME"
        NixOS = "uptime"
        Unraid = "uptime"
    },
    @{
        Section = "CPU"
        NixOS = "lscpu 2>/dev/null | head -30 || echo 'lscpu not available'"
        Unraid = "lscpu 2>/dev/null | head -30 || cat /proc/cpuinfo | head -30"
    },
    @{
        Section = "RAM"
        NixOS = "free -h"
        Unraid = "free -h"
    },
    @{
        Section = "DISKS"
        NixOS = "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL 2>/dev/null | head -30 || echo 'lsblk not available'"
        Unraid = "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null | head -30 || df -h"
    },
    @{
        Section = "DF"
        NixOS = "df -hT | head -20"
        Unraid = "df -hT | head -20"
    },
    @{
        Section = "NETWORK"
        NixOS = "ip -br addr 2>/dev/null | head -15; echo '---'; ip route 2>/dev/null | head -10"
        Unraid = "ip -br addr 2>/dev/null | head -15; echo '---'; ip route 2>/dev/null | head -10"
    },
    @{
        Section = "DNS"
        NixOS = "resolvectl status 2>/dev/null | head -20 || cat /etc/resolv.conf 2>/dev/null | head -10"
        Unraid = "cat /etc/resolv.conf 2>/dev/null | head -10"
    },
    @{
        Section = "PORTS"
        NixOS = "ss -tulpn 2>/dev/null | head -30 || netstat -tulpn 2>/dev/null | head -30"
        Unraid = "ss -tulpn 2>/dev/null | head -50 || netstat -tulpn 2>/dev/null | head -50"
    },
    @{
        Section = "SERVICES"
        NixOS = "systemctl list-units --type=service --state=running 2>/dev/null | head -30"
        Unraid = "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | head -40 || echo 'docker not available'"
    },
    @{
        Section = "DOCKER_VERSION"
        NixOS = "docker version --format 'Client: {{.Client.Version}} | Server: {{.Server.Version}} | API: {{.Server.APIVersion}}' 2>/dev/null || echo 'docker not available'"
        Unraid = "docker version --format 'Client: {{.Client.Version}} | Server: {{.Server.Version}} | API: {{.Server.APIVersion}}' 2>/dev/null || echo 'docker not available'"
    },
    @{
        Section = "DOCKER_PS"
        NixOS = "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>/dev/null | head -30 || echo 'docker not available'"
        Unraid = "docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | head -70 || echo 'docker not available'"
    },
    @{
        Section = "DOCKER_COMPOSE"
        NixOS = "docker compose ls 2>/dev/null | head -20 || echo 'docker compose not available'"
        Unraid = "docker compose ls 2>/dev/null | head -20 || echo 'docker compose not available'"
    },
    @{
        Section = "GPU"
        NixOS = "nvidia-smi --query-gpu=driver_version,name,temperature.gpu,power.draw,power.limit,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null || echo 'nvidia-smi not available or no GPU'"
        Unraid = "nvidia-smi --query-gpu=driver_version,name,temperature.gpu,power.draw,power.limit,memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null || echo 'nvidia-smi not available or no GPU'"
    },
    @{
        Section = "LSPCI_GPU"
        NixOS = "lspci 2>/dev/null | grep -Ei 'vga|3d|display' | head -10 || echo 'lspci not available'"
        Unraid = "lspci 2>/dev/null | grep -Ei 'vga|3d|display' | head -10 || echo 'lspci not available'"
    },
    @{
        Section = "NFS_MOUNTS"
        NixOS = "mount | grep -E 'nfs|cifs' 2>/dev/null | head -10 || echo 'no NFS/CIFS mounts'"
        Unraid = "cat /etc/exports 2>/dev/null | head -20 || echo 'no exports file'"
    },
    @{
        Section = "ZFS_STATUS"
        NixOS = "zpool status 2>/dev/null | head -30 || echo 'zfs not available'"
        Unraid = "zpool status 2>/dev/null | head -30 || echo 'zfs not available'"
    }
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] [$Level] $Message"
}

function Invoke-SSHCommand {
    param(
        [string]$Host,
        [string]$User,
        [string]$Command,
        [int]$TimeoutSec = 30
    )

    $sshTarget = "$User@$Host"
    $fullCommand = "ssh $sshOpts $sshTarget `"$Command`""

    try {
        $output = & cmd /c $fullCommand 2>&1
        $exitCode = $LASTEXITCODE
        return @{
            Output = ($output -join "`n")
            ExitCode = $exitCode
        }
    }
    catch {
        return @{
            Output = "ERROR: $($_.Exception.Message)"
            ExitCode = 1
        }
    }
}

function Get-NodeSnapshot {
    param(
        [hashtable]$Node
    )

    $output = @()
    $output += "=====BEGIN NODE|label=$($Node.Label)|target=$($Node.User)@$($Node.Host)====="

    # Build header summary line
    $headerCmd = if ($Node.OS -eq "NixOS") {
        "hostname; nixos-version 2>/dev/null | head -1; uname -r; lscpu 2>/dev/null | grep 'Model name' | cut -d: -f2 | xargs; nproc; free -h | awk '/Mem:/{print `$2}'; uptime -p 2>/dev/null || uptime | sed 's/.*up /up /'"
    } else {
        "hostname; cat /etc/unraid-version 2>/dev/null | head -1; uname -r; lscpu 2>/dev/null | grep 'Model name' | cut -d: -f2 | xargs; nproc; free -h | awk '/Mem:/{print `$2}'; uptime -p 2>/dev/null || uptime"
    }

    $headerResult = Invoke-SSHCommand -Host $Node.Host -User $Node.User -Command $headerCmd
    if ($headerResult.ExitCode -eq 0) {
        $lines = $headerResult.Output -split "`n" | Where-Object { $_ -match '\S' }
        $hostname = if ($lines.Count -gt 0) { $lines[0] } else { $Node.Name }
        $version = if ($lines.Count -gt 1) { $lines[1] } else { "unknown" }
        $kernel = if ($lines.Count -gt 2) { $lines[2] } else { "unknown" }
        $cpu = if ($lines.Count -gt 3) { $lines[3] -replace '\s+', '_' } else { "unknown" }
        $cores = if ($lines.Count -gt 4) { $lines[4] } else { "?" }
        $ram = if ($lines.Count -gt 5) { $lines[5] } else { "?" }
        $uptime = if ($lines.Count -gt 6) { ($lines[6] -replace 'up ', '') -replace ',.*', '' } else { "?" }

        $output += "HOMEOPS_NODE_SNAPSHOT|hostname=$hostname|os=$($Node.OS)|version=$version|kernel=$kernel|cpu=$cpu|cores=$cores|ram_total=$ram|uptime=$uptime"
    }

    # Run each section command
    foreach ($cmd in $snapshotCommands) {
        $section = $cmd.Section
        $command = if ($Node.OS -eq "NixOS") { $cmd.NixOS } else { $cmd.Unraid }

        $output += "-----BEGIN $section-----"
        $output += "CMD: $($command.Substring(0, [Math]::Min(100, $command.Length)))..."

        $result = Invoke-SSHCommand -Host $Node.Host -User $Node.User -Command $command

        # Cap output at 100 lines
        $lines = ($result.Output -split "`n") | Select-Object -First 100
        $output += $lines
        $output += "EXIT: $($result.ExitCode)"
        $output += "-----END $section-----"
    }

    $output += "=====END NODE|label=$($Node.Label)====="
    return $output
}

# Main execution
Write-Log "Starting Hydra Cluster Snapshot"
Write-Log "Output file: $outputFile"

# Ensure destination directory exists
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

# Build snapshot content
$snapshotContent = @()
$snapshotContent += "HYDRA_SNAPSHOT_BUNDLE|version=2|timestamp=$isoTimestamp|generator=snapshot-hydra.ps1"

foreach ($node in $nodes) {
    Write-Log "Collecting snapshot from $($node.Name)..."
    $nodeOutput = Get-NodeSnapshot -Node $node
    $snapshotContent += $nodeOutput
    Write-Log "Completed $($node.Name)" -Level "SUCCESS"
}

# Write snapshot file
$snapshotContent | Out-File -FilePath $outputFile -Encoding UTF8
Write-Log "Snapshot saved to: $outputFile"

# Update LATEST_SNAPSHOT.md
$snapshotFileName = Split-Path -Leaf $outputFile
$latestContent = @"
# Latest Hydra snapshot
@docs/canonical/00-system-reality/$snapshotFileName

Generated: $isoTimestamp
"@
$latestContent | Out-File -FilePath $latestFile -Encoding UTF8
Write-Log "Updated LATEST_SNAPSHOT.md"

# Git commit
try {
    Push-Location $repoRoot
    git add "docs/canonical/00-system-reality/Hydra_Snapshot_$timestamp.txt"
    git add "docs/canonical/00-system-reality/LATEST_SNAPSHOT.md"
    $commitMsg = "snapshot: Hydra cluster snapshot $timestamp"
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

Write-Log "Snapshot complete!"
Write-Log "View snapshot: $outputFile"
