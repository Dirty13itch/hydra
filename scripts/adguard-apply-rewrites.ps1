<#
.SYNOPSIS
    Apply DNS rewrites to AdGuard Home for Hydra cluster
.DESCRIPTION
    Configures DNS rewrites in AdGuard Home to enable hydra.lan domain resolution.
    Supports DRY RUN mode (default) and APPLY mode.
.PARAMETER Apply
    Actually apply changes. Without this flag, only shows what would be done.
.EXAMPLE
    .\adguard-apply-rewrites.ps1           # Dry run - shows planned changes
    .\adguard-apply-rewrites.ps1 -Apply    # Actually applies changes
.NOTES
    Author: Hydra Steward
    Version: 1.0.0

    Required environment variables for APPLY mode:
    - ADGUARD_URL: AdGuard Home URL (e.g., http://192.168.1.244:3053)
    - ADGUARD_USER: Admin username
    - ADGUARD_PASS: Admin password
#>

param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# DNS Rewrites to configure
$rewrites = @(
    # Node hostnames
    @{ Domain = "storage.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "compute.hydra.lan"; Answer = "192.168.1.203" }
    @{ Domain = "ai.hydra.lan"; Answer = "192.168.1.250" }

    # Legacy aliases
    @{ Domain = "hydra-storage.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "hydra-compute.hydra.lan"; Answer = "192.168.1.203" }
    @{ Domain = "hydra-ai.hydra.lan"; Answer = "192.168.1.250" }

    # Services on hydra-storage
    @{ Domain = "plex.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "grafana.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "prometheus.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "portainer.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "home.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "n8n.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "litellm.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "qdrant.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "redis.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "postgres.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "searx.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "firecrawl.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "docling.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "miniflux.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "sillytavern.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "kokoro.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "perplexica.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "homeassistant.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "stash.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "qbit.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "sabnzbd.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "prowlarr.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "sonarr.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "radarr.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "lidarr.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "bazarr.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "adguard.hydra.lan"; Answer = "192.168.1.244" }
    @{ Domain = "vault.hydra.lan"; Answer = "192.168.1.244" }

    # Services on hydra-ai
    @{ Domain = "tabby.hydra.lan"; Answer = "192.168.1.250" }
    @{ Domain = "openwebui.hydra.lan"; Answer = "192.168.1.250" }

    # Services on hydra-compute
    @{ Domain = "ollama.hydra.lan"; Answer = "192.168.1.203" }
    @{ Domain = "comfyui.hydra.lan"; Answer = "192.168.1.203" }
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $color = switch ($Level) {
        "INFO" { "White" }
        "DRY" { "Yellow" }
        "OK" { "Green" }
        "ERROR" { "Red" }
        "WARN" { "DarkYellow" }
        default { "White" }
    }
    $prefix = if ($Level -eq "DRY") { "[DRY RUN]" } else { "[$Level]" }
    Write-Host "$prefix $Message" -ForegroundColor $color
}

# Header
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AdGuard DNS Rewrite Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not $Apply) {
    Write-Log "Running in DRY RUN mode. Use -Apply to make changes." -Level "DRY"
    Write-Host ""
}

# Check environment variables for Apply mode
if ($Apply) {
    $url = $env:ADGUARD_URL
    $user = $env:ADGUARD_USER
    $pass = $env:ADGUARD_PASS

    if (-not $url -or -not $user -or -not $pass) {
        Write-Log "Missing required environment variables for APPLY mode:" -Level "ERROR"
        Write-Host "  ADGUARD_URL  = AdGuard Home URL (e.g., http://192.168.1.244:3053)"
        Write-Host "  ADGUARD_USER = Admin username"
        Write-Host "  ADGUARD_PASS = Admin password"
        Write-Host ""
        Write-Host "Example:"
        Write-Host '  $env:ADGUARD_URL = "http://192.168.1.244:3053"'
        Write-Host '  $env:ADGUARD_USER = "admin"'
        Write-Host '  $env:ADGUARD_PASS = "your-password"'
        Write-Host '  .\adguard-apply-rewrites.ps1 -Apply'
        exit 1
    }

    Write-Log "AdGuard URL: $url" -Level "INFO"

    # Build auth header
    $authBytes = [System.Text.Encoding]::UTF8.GetBytes("${user}:${pass}")
    $authBase64 = [Convert]::ToBase64String($authBytes)
    $headers = @{
        "Authorization" = "Basic $authBase64"
        "Content-Type" = "application/json"
    }

    # Test connection
    try {
        $status = Invoke-RestMethod -Uri "$url/control/status" -Headers $headers -Method Get
        Write-Log "Connected to AdGuard Home v$($status.version)" -Level "OK"
    }
    catch {
        Write-Log "Failed to connect to AdGuard: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }

    # Get existing rewrites
    try {
        $existing = Invoke-RestMethod -Uri "$url/control/rewrite/list" -Headers $headers -Method Get
        $existingDomains = @{}
        foreach ($r in $existing) {
            $existingDomains[$r.domain] = $r.answer
        }
        Write-Log "Found $($existing.Count) existing rewrites" -Level "INFO"
    }
    catch {
        Write-Log "Failed to get existing rewrites: $($_.Exception.Message)" -Level "ERROR"
        exit 1
    }
}

# Process rewrites
Write-Host ""
Write-Host "DNS Rewrites to configure:" -ForegroundColor Cyan
Write-Host "--------------------------" -ForegroundColor Cyan

$added = 0
$skipped = 0
$failed = 0

foreach ($rewrite in $rewrites) {
    $domain = $rewrite.Domain
    $answer = $rewrite.Answer

    if ($Apply) {
        # Check if already exists
        if ($existingDomains.ContainsKey($domain)) {
            if ($existingDomains[$domain] -eq $answer) {
                Write-Log "$domain -> $answer (already exists)" -Level "INFO"
                $skipped++
                continue
            }
            else {
                # Different answer - need to delete and re-add
                Write-Log "$domain: updating $($existingDomains[$domain]) -> $answer" -Level "WARN"
                try {
                    $deleteBody = @{ domain = $domain; answer = $existingDomains[$domain] } | ConvertTo-Json
                    Invoke-RestMethod -Uri "$url/control/rewrite/delete" -Headers $headers -Method Post -Body $deleteBody | Out-Null
                }
                catch {
                    Write-Log "Failed to delete old rewrite for $domain" -Level "ERROR"
                }
            }
        }

        # Add the rewrite
        try {
            $body = @{ domain = $domain; answer = $answer } | ConvertTo-Json
            Invoke-RestMethod -Uri "$url/control/rewrite/add" -Headers $headers -Method Post -Body $body | Out-Null
            Write-Log "$domain -> $answer" -Level "OK"
            $added++
        }
        catch {
            Write-Log "Failed to add $domain: $($_.Exception.Message)" -Level "ERROR"
            $failed++
        }
    }
    else {
        Write-Log "$domain -> $answer" -Level "DRY"
    }
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($Apply) {
    Write-Host "  Added:   $added" -ForegroundColor Green
    Write-Host "  Skipped: $skipped (already existed)" -ForegroundColor Yellow
    Write-Host "  Failed:  $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

    if ($failed -eq 0) {
        Write-Host ""
        Write-Log "All rewrites applied successfully!" -Level "OK"
        Write-Host ""
        Write-Host "Test with: nslookup tabby.hydra.lan 192.168.1.244" -ForegroundColor Gray
    }
}
else {
    Write-Host "  Total rewrites: $($rewrites.Count)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To apply these changes, run:" -ForegroundColor Cyan
    Write-Host '  $env:ADGUARD_URL = "http://192.168.1.244:3053"'
    Write-Host '  $env:ADGUARD_USER = "admin"'
    Write-Host '  $env:ADGUARD_PASS = "your-password"'
    Write-Host '  .\adguard-apply-rewrites.ps1 -Apply'
}

Write-Host ""
