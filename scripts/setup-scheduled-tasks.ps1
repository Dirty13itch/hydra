<#
.SYNOPSIS
    Creates Windows Scheduled Tasks for Hydra automation
.DESCRIPTION
    Registers (or updates) scheduled tasks for:
    - snapshot-hydra.ps1 (daily at 3:00 AM)
    - check-drift.ps1 (daily at 3:10 AM)
    Idempotent: safe to run multiple times.
.NOTES
    Author: Hydra Steward
    Version: 1.0.0
    Requires: Run as Administrator
#>

#Requires -RunAsAdministrator

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptsDir = $PSScriptRoot
$logsDir = Join-Path $repoRoot "logs"

# Ensure logs directory exists
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

Write-Host "Hydra Scheduled Tasks Setup" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

# Task definitions
$tasks = @(
    @{
        Name = "Hydra Cluster Snapshot"
        Description = "Collects daily system snapshots from all Hydra cluster nodes"
        Script = "snapshot-hydra.ps1"
        Time = "03:00"
        LogFile = "snapshot"
    },
    @{
        Name = "Hydra Drift Detection"
        Description = "Compares snapshots and generates drift reports"
        Script = "check-drift.ps1"
        Time = "03:10"
        LogFile = "drift"
    }
)

foreach ($task in $tasks) {
    $taskName = $task.Name
    $scriptPath = Join-Path $scriptsDir $task.Script
    $logPath = Join-Path $logsDir "$($task.LogFile)_`$(Get-Date -Format 'yyyyMMdd').log"

    Write-Host "Processing: $taskName" -ForegroundColor Yellow

    # Check if task exists
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

    # Build the action
    $argument = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" *> `"$logPath`""
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $repoRoot

    # Build the trigger (daily at specified time)
    $timeParts = $task.Time -split ":"
    $trigger = New-ScheduledTaskTrigger -Daily -At "$($task.Time):00"

    # Build settings
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -RestartCount 1 `
        -RestartInterval (New-TimeSpan -Minutes 5)

    # Build principal (run as current user, highest privileges)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest

    if ($existingTask) {
        Write-Host "  Task exists, updating..." -ForegroundColor Gray

        # Update existing task
        Set-ScheduledTask -TaskName $taskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings | Out-Null

        Write-Host "  Updated: $taskName" -ForegroundColor Green
    }
    else {
        Write-Host "  Creating new task..." -ForegroundColor Gray

        # Register new task
        Register-ScheduledTask -TaskName $taskName `
            -Description $task.Description `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Principal $principal | Out-Null

        Write-Host "  Created: $taskName" -ForegroundColor Green
    }

    Write-Host "  Schedule: Daily at $($task.Time)" -ForegroundColor Gray
    Write-Host "  Script: $scriptPath" -ForegroundColor Gray
    Write-Host ""
}

# Verification
Write-Host "Verification" -ForegroundColor Cyan
Write-Host "------------" -ForegroundColor Cyan

foreach ($task in $tasks) {
    $info = Get-ScheduledTask -TaskName $task.Name -ErrorAction SilentlyContinue
    if ($info) {
        $status = if ($info.State -eq "Ready") { "Ready" } else { $info.State }
        Write-Host "  [OK] $($task.Name) - $status" -ForegroundColor Green
    }
    else {
        Write-Host "  [FAIL] $($task.Name) - Not found" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Commands to manage tasks:" -ForegroundColor Cyan
Write-Host "  View:    Get-ScheduledTask -TaskName 'Hydra*'" -ForegroundColor Gray
Write-Host "  Run now: Start-ScheduledTask -TaskName 'Hydra Cluster Snapshot'" -ForegroundColor Gray
Write-Host "  Disable: Disable-ScheduledTask -TaskName 'Hydra Cluster Snapshot'" -ForegroundColor Gray
Write-Host "  Enable:  Enable-ScheduledTask -TaskName 'Hydra Cluster Snapshot'" -ForegroundColor Gray
Write-Host "  Remove:  Unregister-ScheduledTask -TaskName 'Hydra Cluster Snapshot'" -ForegroundColor Gray
Write-Host ""
Write-Host "Logs will be saved to: $logsDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
