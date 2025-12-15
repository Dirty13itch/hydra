# Drift Fixes Applied

This document tracks fixes applied to address drift identified in the Service Reconciliation Matrix.

## Issues Identified

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | UI hardcodes wrong Ollama IP (251 vs 203) | High | Fix Available |
| 2 | Architecture.md lists LiteLLM under hydra-ai | Medium | Fix Available |
| 3 | Alert rules assume DCGM metrics | Medium | Fix Available |
| 4 | GPU exporters inconsistent | Low | Documented |

## Fix 1: UI Ollama IP

**Location:** `ui/src/lib/api.ts`
**Issue:** Hardcoded IP 192.168.1.251 should be 192.168.1.203

**Fix Script:**
```bash
# Find and replace in UI code
sed -i 's/192\.168\.1\.251/192.168.1.203/g' ui/src/lib/api.ts
```

**Better Solution:** Use environment variable or config:
```typescript
// In api.ts or config.ts
export const OLLAMA_URL = process.env.OLLAMA_URL || 'http://192.168.1.203:11434';
```

## Fix 2: Architecture Documentation

**Location:** `docs/canonical/01-architecture-decisions/architecture.md` (if exists)
**Issue:** LiteLLM incorrectly listed under hydra-ai

**Correct assignment:**
- LiteLLM runs on **hydra-storage:4000** (Docker container)
- TabbyAPI runs on **hydra-ai:5000** (systemd service)

## Fix 3: Alert Rules for GPU Metrics

**Location:** `config/prometheus/rules/hydra-alerts.yml`
**Issue:** Rules assume DCGM metrics but hydra-compute uses nvidia-smi-exporter

**Solution:** Create unified alert rules that work with both exporters:

```yaml
# Generic GPU metrics that work with nvidia-smi-exporter
- alert: GPUHighTemperature
  expr: |
    nvidia_smi_temperature_gpu > 85
    OR
    DCGM_FI_DEV_GPU_TEMP > 85
  for: 5m
  labels:
    severity: warning
```

## Fix 4: GPU Exporter Standardization

**Current State:**
- hydra-ai: nvidia-dcgm-exporter (official NVIDIA)
- hydra-compute: nvidia-smi-exporter (custom, works with Blackwell)

**Recommendation:**
Keep current setup until DCGM properly supports Blackwell GPUs (RTX 50 series).
The custom nvidia-smi-exporter was created specifically because DCGM doesn't support 5070 Ti.

**Prometheus Configuration:**
Ensure both metric naming conventions are scraped:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'nvidia-gpu'
    static_configs:
      - targets:
        - '192.168.1.250:9835'  # hydra-ai (dcgm)
        - '192.168.1.203:9835'  # hydra-compute (nvidia-smi)
```

## Applied Changes Log

| Date | Change | By |
|------|--------|-----|
| 2025-12-13 | Created unified Prometheus alert rules | Steward |
| 2025-12-13 | Documented IP/port drift | Steward |
| 2025-12-13 | Added configuration fix scripts | Steward |

## Verification Commands

```bash
# Verify Ollama is reachable at correct IP
curl -s http://192.168.1.203:11434/api/tags | jq '.models | length'

# Verify LiteLLM on hydra-storage
curl -s http://192.168.1.244:4000/health

# Verify both GPU exporters
curl -s http://192.168.1.250:9835/metrics | head -5
curl -s http://192.168.1.203:9835/metrics | head -5

# Check Prometheus targets
curl -s http://192.168.1.244:9090/api/v1/targets | jq '.data.activeTargets | length'
```
