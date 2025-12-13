<#
.SYNOPSIS
    Comprehensive Hydra Cluster Health Check
.DESCRIPTION
    Performs a complete health assessment of all Hydra cluster components:
    - Node connectivity and uptime
    - GPU status and temperatures
    - Disk space
    - Critical services
    - Docker containers
    - Inference backends
.PARAMETER Quick
    Perform quick checks only (no SSH, just HTTP endpoints)
.PARAMETER Verbose
    Show detailed output for all checks
.EXAMPLE
    .\hydra-health.ps1           # Full health check
    .\hydra-health.ps1 -Quick    # Quick endpoint checks only
.NOTES
    Author: Hydra Steward
    Version: 1.0.0
#>

param(
    [switch]$Quick,
    [switch]$Detailed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Configuration
$nodes = @{
    "hydra-compute" = @{ IP = "192.168.1.203"; User = "typhon"; HasGPU = $true }
    "hydra-ai" = @{ IP = "192.168.1.250"; User = "typhon"; HasGPU = $true }
    "hydra-storage" = @{ IP = "192.168.1.244"; User = "root"; HasGPU = $false }
}

$services = @(
    @{ Name = "TabbyAPI"; URL = "http://192.168.1.250:5000/v1/model"; Node = "hydra-ai" }
    @{ Name = "Ollama"; URL = "http://192.168.1.203:11434/api/tags"; Node = "hydra-compute" }
    @{ Name = "LiteLLM"; URL = "http://192.168.1.244:4000/health"; Node = "hydra-storage" }
    @{ Name = "Prometheus"; URL = "http://192.168.1.244:9090/-/healthy"; Node = "hydra-storage" }
    @{ Name = "Grafana"; URL = "http://192.168.1.244:3003/api/health"; Node = "hydra-storage" }
    @{ Name = "Open WebUI"; URL = "http://192.168.1.250:3000"; Node = "hydra-ai" }
    @{ Name = "Qdrant"; URL = "http://192.168.1.244:6333/health"; Node = "hydra-storage" }
    @{ Name = "PostgreSQL"; URL = "http://192.168.1.244:5432"; Port = 5432; Node = "hydra-storage" }
    @{ Name = "Redis"; URL = "http://192.168.1.244:6379"; Port = 6379; Node = "hydra-storage" }
)

# Results tracking
$results = @{
    Passed = 0
    Failed = 0
    Warnings = 0
    Details = @()
}

function Write-Check {
    param(
        [string]$Category,
        [string]$Check,
        [string]$Status,  # OK, WARN, FAIL, INFO
        [string]$Details = ""
    )

    $symbol = switch ($Status) {
        "OK" { "[+]"; $color = "Green" }
        "WARN" { "[!]"; $color = "Yellow" }
        "FAIL" { "[-]"; $color = "Red" }
        "INFO" { "[*]"; $color = "Cyan" }
        default { "[ ]"; $color = "White" }
    }

    $line = "$symbol $Category`: $Check"
    if ($Details -and ($Detailed -or $Status -eq "FAIL")) {
        $line += " ($Details)"
    }

    Write-Host $line -ForegroundColor $color

    # Track results
    switch ($Status) {
        "OK" { $script:results.Passed++ }
        "WARN" { $script:results.Warnings++ }
        "FAIL" { $script:results.Failed++ }
    }

    $script:results.Details += @{
        Category = $Category
        Check = $Check
        Status = $Status
        Details = $Details
    }
}

function Test-TCPPort {
    param([string]$Host, [int]$Port, [int]$Timeout = 3)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $result = $client.BeginConnect($Host, $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne($Timeout * 1000, $false)
        if ($success) {
            $client.EndConnect($result)
            $client.Close()
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
}

function Test-HTTPEndpoint {
    param([string]$URL, [int]$Timeout = 5)
    try {
        $response = Invoke-WebRequest -Uri $URL -TimeoutSec $Timeout -UseBasicParsing -ErrorAction Stop
        return @{ Success = $true; StatusCode = $response.StatusCode; Content = $response.Content }
    }
    catch {
        return @{ Success = $false; Error = $_.Exception.Message }
    }
}

function Get-SSHOutput {
    param([string]$Host, [string]$User, [string]$Command, [int]$Timeout = 10)
    try {
        $sshCommand = "ssh -o ConnectTimeout=$Timeout -o BatchMode=yes -o StrictHostKeyChecking=accept-new $User@$Host `"$Command`""
        $output = & cmd /c $sshCommand 2>&1
        return @{ Success = ($LASTEXITCODE -eq 0); Output = ($output -join "`n") }
    }
    catch {
        return @{ Success = $false; Error = $_.Exception.Message }
    }
}

# Header
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                   HYDRA CLUSTER HEALTH CHECK                     ║" -ForegroundColor Cyan
Write-Host "║                      $timestamp                        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ===== NETWORK CONNECTIVITY =====
Write-Host "── Network Connectivity ──────────────────────────────────────────" -ForegroundColor Yellow

foreach ($nodeName in $nodes.Keys) {
    $node = $nodes[$nodeName]
    $pingable = Test-Connection -ComputerName $node.IP -Count 1 -Quiet -TimeoutSeconds 2

    if ($pingable) {
        Write-Check -Category $nodeName -Check "Ping" -Status "OK" -Details $node.IP
    }
    else {
        Write-Check -Category $nodeName -Check "Ping" -Status "FAIL" -Details "No response from $($node.IP)"
    }
}
Write-Host ""

# ===== SERVICE ENDPOINTS =====
Write-Host "── Service Endpoints ─────────────────────────────────────────────" -ForegroundColor Yellow

foreach ($svc in $services) {
    if ($svc.Port) {
        # TCP port check
        $reachable = Test-TCPPort -Host ($svc.URL -replace 'http://|:\d+.*', '') -Port $svc.Port
        if ($reachable) {
            Write-Check -Category $svc.Name -Check "Port $($svc.Port)" -Status "OK"
        }
        else {
            Write-Check -Category $svc.Name -Check "Port $($svc.Port)" -Status "FAIL" -Details "Connection refused"
        }
    }
    else {
        # HTTP endpoint check
        $result = Test-HTTPEndpoint -URL $svc.URL -Timeout 5
        if ($result.Success) {
            # Extract useful info
            $detail = ""
            if ($svc.Name -eq "TabbyAPI") {
                try {
                    $json = $result.Content | ConvertFrom-Json
                    $detail = $json.model_name
                }
                catch { }
            }
            elseif ($svc.Name -eq "Ollama") {
                try {
                    $json = $result.Content | ConvertFrom-Json
                    $detail = "$($json.models.Count) models"
                }
                catch { }
            }
            Write-Check -Category $svc.Name -Check "HTTP" -Status "OK" -Details $detail
        }
        else {
            Write-Check -Category $svc.Name -Check "HTTP" -Status "FAIL" -Details $result.Error
        }
    }
}
Write-Host ""

if (-not $Quick) {
    # ===== GPU STATUS =====
    Write-Host "── GPU Status ────────────────────────────────────────────────────" -ForegroundColor Yellow

    foreach ($nodeName in $nodes.Keys | Where-Object { $nodes[$_].HasGPU }) {
        $node = $nodes[$nodeName]
        $gpuResult = Get-SSHOutput -Host $node.IP -User $node.User -Command "nvidia-smi --query-gpu=name,temperature.gpu,memory.used,memory.total,power.draw --format=csv,noheader,nounits"

        if ($gpuResult.Success) {
            $lines = $gpuResult.Output -split "`n" | Where-Object { $_ -match '\S' }
            foreach ($line in $lines) {
                $parts = $line -split ", "
                if ($parts.Count -ge 5) {
                    $gpuName = $parts[0].Trim()
                    $temp = [int]$parts[1].Trim()
                    $memUsed = [math]::Round([double]$parts[2].Trim() / 1024, 1)
                    $memTotal = [math]::Round([double]$parts[3].Trim() / 1024, 1)
                    $power = [math]::Round([double]$parts[4].Trim(), 0)

                    # Temperature check
                    $tempStatus = if ($temp -lt 70) { "OK" } elseif ($temp -lt 80) { "WARN" } else { "FAIL" }
                    Write-Check -Category "$nodeName GPU" -Check "Temperature" -Status $tempStatus -Details "${temp}°C"

                    # Memory check
                    $memPct = [math]::Round(($memUsed / $memTotal) * 100, 0)
                    $memStatus = if ($memPct -lt 80) { "OK" } elseif ($memPct -lt 95) { "WARN" } else { "FAIL" }
                    Write-Check -Category "$nodeName GPU" -Check "Memory" -Status $memStatus -Details "${memUsed}/${memTotal}GB (${memPct}%)"

                    # Power check
                    Write-Check -Category "$nodeName GPU" -Check "Power" -Status "INFO" -Details "${power}W"
                }
            }
        }
        else {
            Write-Check -Category "$nodeName GPU" -Check "nvidia-smi" -Status "FAIL" -Details "Cannot query GPU"
        }
    }
    Write-Host ""

    # ===== DISK SPACE =====
    Write-Host "── Disk Space ────────────────────────────────────────────────────" -ForegroundColor Yellow

    foreach ($nodeName in $nodes.Keys) {
        $node = $nodes[$nodeName]
        $path = if ($nodeName -eq "hydra-storage") { "/mnt/user" } else { "/" }
        $diskResult = Get-SSHOutput -Host $node.IP -User $node.User -Command "df -h $path | tail -1 | awk '{print `$5, `$4}'"

        if ($diskResult.Success) {
            $parts = $diskResult.Output.Trim() -split '\s+'
            if ($parts.Count -ge 2) {
                $usedPct = [int]($parts[0] -replace '%', '')
                $avail = $parts[1]

                $diskStatus = if ($usedPct -lt 80) { "OK" } elseif ($usedPct -lt 90) { "WARN" } else { "FAIL" }
                Write-Check -Category $nodeName -Check "Disk $path" -Status $diskStatus -Details "${usedPct}% used, ${avail} free"
            }
        }
        else {
            Write-Check -Category $nodeName -Check "Disk" -Status "FAIL" -Details "Cannot check disk"
        }
    }
    Write-Host ""

    # ===== DOCKER CONTAINERS =====
    Write-Host "── Docker Containers (hydra-storage) ─────────────────────────────" -ForegroundColor Yellow

    $dockerResult = Get-SSHOutput -Host $nodes["hydra-storage"].IP -User $nodes["hydra-storage"].User -Command "docker ps -a --format '{{.Names}}|{{.Status}}' | head -30"

    if ($dockerResult.Success) {
        $containers = $dockerResult.Output -split "`n" | Where-Object { $_ -match '\S' }
        $upCount = 0
        $downCount = 0
        $unhealthy = @()

        foreach ($container in $containers) {
            $parts = $container -split '\|'
            if ($parts.Count -ge 2) {
                $name = $parts[0]
                $status = $parts[1]

                if ($status -match "^Up") {
                    $upCount++
                }
                else {
                    $downCount++
                    $unhealthy += $name
                }
            }
        }

        if ($downCount -eq 0) {
            Write-Check -Category "Docker" -Check "Containers" -Status "OK" -Details "$upCount running"
        }
        else {
            Write-Check -Category "Docker" -Check "Containers" -Status "WARN" -Details "$upCount up, $downCount down"
            foreach ($c in $unhealthy | Select-Object -First 5) {
                Write-Check -Category "Docker" -Check $c -Status "FAIL" -Details "Not running"
            }
        }
    }
    else {
        Write-Check -Category "Docker" -Check "Status" -Status "FAIL" -Details "Cannot query Docker"
    }
    Write-Host ""

    # ===== UPTIME =====
    Write-Host "── Node Uptime ───────────────────────────────────────────────────" -ForegroundColor Yellow

    foreach ($nodeName in $nodes.Keys) {
        $node = $nodes[$nodeName]
        $uptimeResult = Get-SSHOutput -Host $node.IP -User $node.User -Command "uptime -p 2>/dev/null || uptime | sed 's/.*up /up /'"

        if ($uptimeResult.Success) {
            $uptime = $uptimeResult.Output.Trim() -replace '^up ', ''
            Write-Check -Category $nodeName -Check "Uptime" -Status "INFO" -Details $uptime
        }
        else {
            Write-Check -Category $nodeName -Check "Uptime" -Status "FAIL" -Details "Cannot query"
        }
    }
    Write-Host ""
}

# ===== SUMMARY =====
Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$totalChecks = $results.Passed + $results.Failed + $results.Warnings

if ($results.Failed -eq 0 -and $results.Warnings -eq 0) {
    Write-Host "  CLUSTER STATUS: HEALTHY" -ForegroundColor Green
    Write-Host "  All $totalChecks checks passed" -ForegroundColor Green
}
elseif ($results.Failed -eq 0) {
    Write-Host "  CLUSTER STATUS: OPERATIONAL (with warnings)" -ForegroundColor Yellow
    Write-Host "  Passed: $($results.Passed)  Warnings: $($results.Warnings)" -ForegroundColor Yellow
}
else {
    Write-Host "  CLUSTER STATUS: DEGRADED" -ForegroundColor Red
    Write-Host "  Passed: $($results.Passed)  Failed: $($results.Failed)  Warnings: $($results.Warnings)" -ForegroundColor Red
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Return exit code based on status
if ($results.Failed -gt 0) {
    exit 1
}
elseif ($results.Warnings -gt 0) {
    exit 2
}
else {
    exit 0
}
