<#
.SYNOPSIS
    Hydra Cluster Model Management Utility
.DESCRIPTION
    Manage AI models across the Hydra cluster - list, load, pull, and check status.
.PARAMETER Action
    Action to perform: status, list, load, pull, info
.PARAMETER Model
    Model name for load/pull/info actions
.PARAMETER Backend
    Backend to use: tabby, ollama, all (default: all)
.EXAMPLE
    .\hydra-models.ps1 status              # Show all model status
    .\hydra-models.ps1 list                # List available models
    .\hydra-models.ps1 list -Backend tabby # List TabbyAPI models only
    .\hydra-models.ps1 info qwen2.5:7b     # Get info about specific model
    .\hydra-models.ps1 pull llama3.2:3b    # Pull model to Ollama
.NOTES
    Author: Hydra Steward
    Version: 1.0.0
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("status", "list", "load", "pull", "info")]
    [string]$Action = "status",

    [Parameter(Position=1)]
    [string]$Model,

    [ValidateSet("tabby", "ollama", "all")]
    [string]$Backend = "all"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Configuration
$tabbyHost = "192.168.1.250"
$tabbyPort = 5000
$ollamaHost = "192.168.1.203"
$ollamaPort = 11434
$modelsPath = "/mnt/models"

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $color = switch ($Status) {
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    $symbol = switch ($Status) {
        "OK" { "[+]" }
        "WARN" { "[!]" }
        "ERROR" { "[-]" }
        "INFO" { "[*]" }
        default { "   " }
    }
    Write-Host "$symbol $Message" -ForegroundColor $color
}

function Get-TabbyStatus {
    try {
        $response = Invoke-RestMethod -Uri "http://${tabbyHost}:${tabbyPort}/v1/model" -TimeoutSec 10
        return @{
            Online = $true
            Model = $response.model_name
            MaxSeqLen = $response.max_seq_len
            Data = $response
        }
    }
    catch {
        return @{
            Online = $false
            Error = $_.Exception.Message
        }
    }
}

function Get-OllamaStatus {
    try {
        $response = Invoke-RestMethod -Uri "http://${ollamaHost}:${ollamaPort}/api/tags" -TimeoutSec 10
        return @{
            Online = $true
            Models = $response.models
            Count = $response.models.Count
        }
    }
    catch {
        return @{
            Online = $false
            Error = $_.Exception.Message
        }
    }
}

function Get-OllamaModelInfo {
    param([string]$ModelName)
    try {
        $body = @{ name = $ModelName } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "http://${ollamaHost}:${ollamaPort}/api/show" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
        return $response
    }
    catch {
        return $null
    }
}

function Invoke-OllamaPull {
    param([string]$ModelName)
    Write-Status "Pulling model: $ModelName" -Status "INFO"
    Write-Status "This may take a while..." -Status "WARN"

    try {
        $body = @{ name = $ModelName; stream = $false } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "http://${ollamaHost}:${ollamaPort}/api/pull" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 3600
        return @{ Success = $true; Response = $response }
    }
    catch {
        return @{ Success = $false; Error = $_.Exception.Message }
    }
}

function Get-TabbyModels {
    # List EXL2 models on disk via SSH
    try {
        $result = ssh typhon@$tabbyHost "ls -la /mnt/models/exl2/ 2>/dev/null | grep '^d' | awk '{print `$NF}' | grep -v '^\.$'" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $models = $result -split "`n" | Where-Object { $_ -match '\S' -and $_ -ne '.' -and $_ -ne '..' }
            return $models
        }
        return @()
    }
    catch {
        return @()
    }
}

function Show-Status {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║              HYDRA CLUSTER MODEL STATUS                      ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    # TabbyAPI Status
    Write-Host "┌─ TabbyAPI (hydra-ai:$tabbyPort) ─────────────────────────────" -ForegroundColor Yellow
    $tabby = Get-TabbyStatus
    if ($tabby.Online) {
        Write-Status "Status: ONLINE" -Status "OK"
        Write-Status "Model: $($tabby.Model)" -Status "INFO"
        Write-Status "Max Sequence Length: $($tabby.MaxSeqLen)" -Status "INFO"
    }
    else {
        Write-Status "Status: OFFLINE" -Status "ERROR"
        Write-Status "Error: $($tabby.Error)" -Status "WARN"
    }
    Write-Host ""

    # Ollama Status
    Write-Host "┌─ Ollama (hydra-compute:$ollamaPort) ─────────────────────────" -ForegroundColor Yellow
    $ollama = Get-OllamaStatus
    if ($ollama.Online) {
        Write-Status "Status: ONLINE" -Status "OK"
        Write-Status "Models loaded: $($ollama.Count)" -Status "INFO"
        if ($ollama.Models.Count -gt 0) {
            Write-Host ""
            Write-Host "   Available models:" -ForegroundColor Gray
            foreach ($model in $ollama.Models | Select-Object -First 10) {
                $size = [math]::Round($model.size / 1GB, 2)
                Write-Host "   - $($model.name) (${size}GB)" -ForegroundColor White
            }
            if ($ollama.Models.Count -gt 10) {
                Write-Host "   ... and $($ollama.Models.Count - 10) more" -ForegroundColor Gray
            }
        }
    }
    else {
        Write-Status "Status: OFFLINE" -Status "ERROR"
        Write-Status "Error: $($ollama.Error)" -Status "WARN"
    }
    Write-Host ""

    # Summary
    Write-Host "┌─ Summary ────────────────────────────────────────────────────" -ForegroundColor Yellow
    $healthy = ($tabby.Online -and $ollama.Online)
    if ($healthy) {
        Write-Status "All inference backends operational" -Status "OK"
    }
    else {
        Write-Status "Some backends are offline - check above" -Status "WARN"
    }
    Write-Host ""
}

function Show-List {
    param([string]$BackendFilter)

    Write-Host ""
    Write-Host "HYDRA CLUSTER MODEL INVENTORY" -ForegroundColor Cyan
    Write-Host "==============================" -ForegroundColor Cyan
    Write-Host ""

    if ($BackendFilter -eq "all" -or $BackendFilter -eq "tabby") {
        Write-Host "TabbyAPI (EXL2 models on hydra-ai):" -ForegroundColor Yellow
        Write-Host "-----------------------------------" -ForegroundColor Yellow

        $tabbyModels = Get-TabbyModels
        if ($tabbyModels.Count -gt 0) {
            foreach ($model in $tabbyModels) {
                Write-Host "  $model" -ForegroundColor White
            }
        }
        else {
            Write-Host "  (Unable to list - SSH or directory issue)" -ForegroundColor Gray
        }

        # Show currently loaded
        $tabby = Get-TabbyStatus
        if ($tabby.Online) {
            Write-Host ""
            Write-Host "  Currently loaded: $($tabby.Model)" -ForegroundColor Green
        }
        Write-Host ""
    }

    if ($BackendFilter -eq "all" -or $BackendFilter -eq "ollama") {
        Write-Host "Ollama (GGUF models on hydra-compute):" -ForegroundColor Yellow
        Write-Host "---------------------------------------" -ForegroundColor Yellow

        $ollama = Get-OllamaStatus
        if ($ollama.Online -and $ollama.Models.Count -gt 0) {
            foreach ($model in $ollama.Models) {
                $size = [math]::Round($model.size / 1GB, 2)
                $modified = [DateTime]::Parse($model.modified_at).ToString("yyyy-MM-dd")
                Write-Host "  $($model.name.PadRight(30)) ${size}GB  $modified" -ForegroundColor White
            }
        }
        else {
            Write-Host "  (No models available or Ollama offline)" -ForegroundColor Gray
        }
        Write-Host ""
    }
}

function Show-ModelInfo {
    param([string]$ModelName)

    if (-not $ModelName) {
        Write-Status "Please specify a model name" -Status "ERROR"
        return
    }

    Write-Host ""
    Write-Host "MODEL INFO: $ModelName" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    Write-Host ""

    # Try Ollama first
    $info = Get-OllamaModelInfo -ModelName $ModelName
    if ($info) {
        Write-Host "Backend: Ollama" -ForegroundColor Yellow
        Write-Host ""

        if ($info.modelfile) {
            Write-Host "Modelfile:" -ForegroundColor Gray
            $info.modelfile -split "`n" | Select-Object -First 10 | ForEach-Object {
                Write-Host "  $_" -ForegroundColor White
            }
        }

        if ($info.parameters) {
            Write-Host ""
            Write-Host "Parameters:" -ForegroundColor Gray
            Write-Host "  $($info.parameters)" -ForegroundColor White
        }

        if ($info.details) {
            Write-Host ""
            Write-Host "Details:" -ForegroundColor Gray
            Write-Host "  Family: $($info.details.family)" -ForegroundColor White
            Write-Host "  Parameter Size: $($info.details.parameter_size)" -ForegroundColor White
            Write-Host "  Quantization: $($info.details.quantization_level)" -ForegroundColor White
        }
    }
    else {
        Write-Status "Model not found in Ollama. Check TabbyAPI models manually." -Status "WARN"
    }
    Write-Host ""
}

function Invoke-Pull {
    param([string]$ModelName)

    if (-not $ModelName) {
        Write-Status "Please specify a model name (e.g., llama3.2:3b)" -Status "ERROR"
        return
    }

    Write-Host ""
    Write-Host "PULLING MODEL: $ModelName" -ForegroundColor Cyan
    Write-Host "==========================" -ForegroundColor Cyan
    Write-Host ""

    $result = Invoke-OllamaPull -ModelName $ModelName

    if ($result.Success) {
        Write-Status "Model pulled successfully!" -Status "OK"
    }
    else {
        Write-Status "Failed to pull model: $($result.Error)" -Status "ERROR"
    }
    Write-Host ""
}

# Main
switch ($Action) {
    "status" { Show-Status }
    "list" { Show-List -BackendFilter $Backend }
    "info" { Show-ModelInfo -ModelName $Model }
    "pull" { Invoke-Pull -ModelName $Model }
    "load" {
        Write-Status "Load action requires manual config change for TabbyAPI" -Status "WARN"
        Write-Host ""
        Write-Host "To load a different model on TabbyAPI:" -ForegroundColor Yellow
        Write-Host "1. SSH to hydra-ai: ssh typhon@hydra-ai"
        Write-Host "2. Edit config: sudo nano /opt/tabbyapi/config.yml"
        Write-Host "3. Change model_name to desired model"
        Write-Host "4. Restart: sudo systemctl restart tabbyapi"
        Write-Host ""
        Write-Host "For Ollama, models are loaded on-demand automatically."
        Write-Host ""
    }
    default {
        Write-Host "Usage: .\hydra-models.ps1 <action> [model] [-Backend tabby|ollama|all]"
        Write-Host ""
        Write-Host "Actions:"
        Write-Host "  status  - Show cluster model status"
        Write-Host "  list    - List available models"
        Write-Host "  info    - Get info about a specific model"
        Write-Host "  pull    - Pull a model to Ollama"
        Write-Host "  load    - Instructions for loading models"
    }
}
