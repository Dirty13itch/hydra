# Windows Task Scheduler Setup for Hydra Automation

This runbook documents how to schedule `snapshot-hydra.ps1` to run automatically.

## Overview

| Setting | Value |
|---------|-------|
| Script | `C:\Users\shaun\projects\hydra\scripts\snapshot-hydra.ps1` |
| Schedule | Daily at 3:00 AM |
| Working Directory | `C:\Users\shaun\projects\hydra` |
| Run As | Current user account |
| Log Output | `C:\Users\shaun\projects\hydra\logs\snapshot.log` |

## Prerequisites

1. SSH keys configured for passwordless access to:
   - `hydra-compute` (typhon@)
   - `hydra-ai` (typhon@)
   - `hydra-storage` (root@)

2. Git configured in the repository

3. PowerShell execution policy allows scripts:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

## Step-by-Step Setup

### Step 1: Create Log Directory

```powershell
New-Item -ItemType Directory -Force -Path "C:\Users\shaun\projects\hydra\logs"
```

### Step 2: Open Task Scheduler

1. Press `Win + R`
2. Type `taskschd.msc` and press Enter
3. Or search for "Task Scheduler" in Start menu

### Step 3: Create New Task

1. In the right panel, click **Create Task** (not "Create Basic Task")

### Step 4: General Tab

| Setting | Value |
|---------|-------|
| Name | `Hydra Cluster Snapshot` |
| Description | `Collects daily system snapshots from all Hydra cluster nodes` |
| Security options | Select **Run whether user is logged on or not** |
| Security options | Check **Run with highest privileges** |
| Configure for | Windows 10/11 |

### Step 5: Triggers Tab

1. Click **New...**
2. Configure:

| Setting | Value |
|---------|-------|
| Begin the task | On a schedule |
| Settings | Daily |
| Start | 3:00:00 AM |
| Recur every | 1 days |
| Enabled | Checked |

3. Click **OK**

### Step 6: Actions Tab

1. Click **New...**
2. Configure:

| Setting | Value |
|---------|-------|
| Action | Start a program |
| Program/script | `powershell.exe` |
| Add arguments | `-NoProfile -ExecutionPolicy Bypass -File "C:\Users\shaun\projects\hydra\scripts\snapshot-hydra.ps1" *> "C:\Users\shaun\projects\hydra\logs\snapshot_$(Get-Date -Format 'yyyyMMdd').log"` |
| Start in | `C:\Users\shaun\projects\hydra` |

**Note:** The argument redirects all output (stdout + stderr) to a dated log file.

**Alternative argument for appending to single log:**
```
-NoProfile -ExecutionPolicy Bypass -File "C:\Users\shaun\projects\hydra\scripts\snapshot-hydra.ps1" >> "C:\Users\shaun\projects\hydra\logs\snapshot.log" 2>&1
```

### Step 7: Conditions Tab

| Setting | Value |
|---------|-------|
| Start only if on AC power | Unchecked (for desktop) |
| Wake computer to run | Optional (check if computer sleeps) |
| Start only if network available | Checked |

### Step 8: Settings Tab

| Setting | Value |
|---------|-------|
| Allow task to run on demand | Checked |
| Run task as soon as possible after scheduled start missed | Checked |
| Stop task if runs longer than | 1 hour |
| If running task does not end, force stop | Checked |

### Step 9: Save and Authenticate

1. Click **OK**
2. Enter your Windows password when prompted
3. Task is now created

## Testing the Task

### Option 1: Run Manually from Task Scheduler

1. Find `Hydra Cluster Snapshot` in Task Scheduler Library
2. Right-click → **Run**
3. Check:
   - Exit code in "Last Run Result" column (0x0 = success)
   - Log file: `C:\Users\shaun\projects\hydra\logs\snapshot.log`
   - Snapshot file: `docs\canonical\00-system-reality\Hydra_Snapshot_*.txt`

### Option 2: Run from PowerShell

```powershell
cd C:\Users\shaun\projects\hydra
.\scripts\snapshot-hydra.ps1
```

### Option 3: Verify Git Commit

```powershell
cd C:\Users\shaun\projects\hydra
git log --oneline -5
# Should show: "snapshot: Hydra cluster snapshot YYYYMMDD_HHMMSS"
```

## Troubleshooting

### Task fails with exit code 0x1

- Check SSH connectivity: `ssh hydra-compute hostname`
- Verify SSH keys are loaded
- Check log file for specific errors

### Task never runs

- Verify "Run whether user is logged on or not" is set
- Check Windows Event Viewer → Applications and Services Logs → Microsoft → Windows → TaskScheduler

### Log file not created

- Ensure logs directory exists
- Check "Start in" is set correctly
- Try running manually first

### SSH hangs

- The script uses BatchMode and ConnectTimeout
- If a node is down, it will timeout after 15 seconds and continue

## Maintenance

### View Recent Logs

```powershell
Get-Content "C:\Users\shaun\projects\hydra\logs\snapshot.log" -Tail 50
```

### Clean Old Snapshots (manual)

Keep last 30 days of snapshots:
```powershell
$dir = "C:\Users\shaun\projects\hydra\docs\canonical\00-system-reality"
Get-ChildItem $dir -Filter "Hydra_Snapshot_*.txt" |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  ForEach-Object {
    Write-Host "Archiving: $($_.Name)"
    # Move-Item $_.FullName -Destination "C:\Users\shaun\projects\hydra\legacy\snapshots\"
  }
```

### Disable Task Temporarily

```powershell
Disable-ScheduledTask -TaskName "Hydra Cluster Snapshot"
Enable-ScheduledTask -TaskName "Hydra Cluster Snapshot"
```

## Export/Import Task (Backup)

### Export

```powershell
Export-ScheduledTask -TaskName "Hydra Cluster Snapshot" | Out-File "C:\Users\shaun\projects\hydra\config\hydra-snapshot-task.xml"
```

### Import

```powershell
Register-ScheduledTask -TaskName "Hydra Cluster Snapshot" -Xml (Get-Content "C:\Users\shaun\projects\hydra\config\hydra-snapshot-task.xml" -Raw)
```

---

*Last updated: 2025-12-13*
