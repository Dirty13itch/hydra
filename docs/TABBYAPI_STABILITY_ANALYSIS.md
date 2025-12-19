# TabbyAPI Stability Analysis - Deep Dive

**Date:** 2025-12-18
**Analysis Period:** 30 days (Nov 18 - Dec 18, 2025)

## Executive Summary

TabbyAPI experienced **13,979 restarts in 30 days**, with 99.7% occurring during a single 5-day incident (Dec 7-11). The root cause was a cascading configuration failure after a NixOS rebuild, compounded by missing operational safeguards.

**Key Finding:** The system had monitoring infrastructure deployed (Prometheus, AlertManager, Uptime Kuma, Grafana) but **zero alert rules configured**. The incident went undetected for 4+ days.

---

## Incident Timeline

### Dec 7, 21:30 - Initial Failure
**Trigger:** NixOS rebuild (likely for RTX 5090/Blackwell support)

**Error:**
```
ImportError: libstdc++.so.6: cannot open shared object file: No such file or directory
```

**Root Cause:** systemd service missing `LD_LIBRARY_PATH` for gcc libraries after NixOS update.

**Restarts:** ~700 (10-second intervals)

### Dec 8 - First Fix Attempt
**Fix Applied:** Added `LD_LIBRARY_PATH` to systemd Environment

**New Error:**
```
ImportError: undefined symbol: _ZN3c106detail23torchInternalAssertFailEPKcS2_jS2_RKSs
```

**Root Cause:** ExLlamaV2 compiled against different PyTorch version than system provides.

**Restarts:** ~7,413 (continuing every 10 seconds)

### Dec 9-10 - Continued Failure
**Status:** Same PyTorch mismatch error

**Restarts:** ~4,082

### Dec 11 - Resolution
**Fix:** Rebuilt TabbyAPI venv with matching PyTorch version

**First Success:** 23:52

**Additional Issue:** VRAM configuration needed tuning (1,741 more restarts)

### Total Impact
| Metric | Value |
|--------|-------|
| Total Restarts | 13,979 |
| Duration | ~100 hours |
| Inference Downtime | 100 hours |
| Human Detection Time | ~4 days |

---

## Failure Breakdown

| Failure Type | Count | Percentage |
|--------------|-------|------------|
| VRAM Exhaustion | 3,539 | 25.3% |
| Port Conflict (5000→5001) | 1,757 | 12.6% |
| PyTorch Mismatch | ~7,000 | 50.0% |
| libstdc++ Missing | ~700 | 5.0% |
| CUDA Kernel Errors | 4 | <0.1% |
| Other/Unknown | ~980 | 7.0% |

---

## Root Cause Analysis

### Why Did This Happen?

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROOT CAUSE CHAIN                              │
└─────────────────────────────────────────────────────────────────┘

[NixOS Rebuild]
     │
     ▼
[Library paths changed] ──── No smoke test after rebuild
     │
     ▼
[TabbyAPI can't import torch]
     │
     ▼
[Service crashes on startup]
     │
     ▼
[systemd restarts (10s interval)] ──── No restart limits
     │
     ▼
[Same error, crash again]
     │
     ▼
[13,000+ restart loop] ──── No alerting configured
     │
     ▼
[4 days until human notices]
```

### Contributing Factors

1. **No Post-Deploy Verification**
   - NixOS rebuild completed "successfully"
   - No automated test verified TabbyAPI still worked
   - A simple `curl http://localhost:5000/health` would have caught it

2. **No Restart Limits**
   - systemd config: `Restart=on-failure`, `RestartSec=10`
   - No `StartLimitBurst` or `StartLimitIntervalSec`
   - System happily restarted 13,000+ times

3. **No Alerting**
   - AlertManager deployed with receivers (Discord, n8n, webhooks)
   - **ZERO alert rules defined**
   - Nobody was notified

4. **Silent Port Fallback**
   - TabbyAPI switches to 5001 when 5000 is busy
   - This "helpful" behavior hides failures
   - LiteLLM routes to 5000, gets nothing

5. **Unrecoverable Failure Mode**
   - The error required human intervention (rebuild venv)
   - No amount of automatic restarts would fix it
   - System couldn't distinguish "fixable" vs "unfixable" failures

---

## What Should Exist (But Doesn't)

### Layer 1: Preventive

| Control | Status | Impact |
|---------|--------|--------|
| Post-deploy smoke test | Missing | Would catch 100% of these failures |
| Pre-start dependency check | Missing | Verify libs exist before starting |
| Config validation | Missing | Catch invalid configs before deploy |

### Layer 2: Detective

| Control | Status | Impact |
|---------|--------|--------|
| Prometheus alert rules | **Missing** | Would alert on service down |
| Restart count monitoring | Missing | Would alert on restart loops |
| Error pattern detection | Missing | Would identify recurring errors |
| Health check endpoint | Exists | But not tied to alerting |

### Layer 3: Reactive

| Control | Status | Impact |
|---------|--------|--------|
| Restart limits | Now Added | Prevents infinite loops |
| Circuit breaker | Missing | Would stop retrying unfixable errors |
| Fallback routing | Missing | Would route to Ollama when TabbyAPI down |
| Auto-remediation | Missing | Could restart with different config |

### Layer 4: Recovery

| Control | Status | Impact |
|---------|--------|--------|
| Model fallback chain | Missing | Try smaller model if VRAM fails |
| Graceful degradation | Missing | Use Ollama when TabbyAPI unavailable |
| Self-healing venv rebuild | Missing | Could detect and fix version mismatches |

---

## Production LLM Serving Patterns (Industry Best Practices)

Based on research from [Portkey](https://portkey.ai/blog/retries-fallbacks-and-circuit-breakers-in-llm-apps/), [Azure](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/improve-llm-backend-resiliency-with-load-balancer-and-circuit-breaker-rules-in-a/4394502), and [Galileo](https://galileo.ai/blog/production-llm-monitoring-strategies):

### Circuit Breaker Pattern
```
[Request] → [Circuit Breaker] → [TabbyAPI]
                   │
                   ├── Closed: Normal operation
                   ├── Open: Stop sending requests (cooldown)
                   └── Half-Open: Test with single request

Thresholds:
- Trip after 5 consecutive failures
- Cooldown: 60 seconds
- Half-open test: Single request
```

### Fallback Chain Pattern
```
[Request] → [LiteLLM Router]
                   │
                   ├── Primary: TabbyAPI (70B models)
                   │      │
                   │      └── Fallback: Reduce context, retry
                   │
                   ├── Secondary: Ollama GPU (14B models)
                   │
                   └── Tertiary: Ollama CPU (7B models)
```

### Health-Aware Routing
```
Every 30s:
  Check TabbyAPI /health → Update routing table
  Check Ollama /api/ps → Update routing table

If TabbyAPI unhealthy for > 2 checks:
  Route all traffic to Ollama
  Send alert
  Begin circuit breaker cooldown
```

---

## Recommended Solution Architecture

### Phase 1: Immediate Fixes (Hours)

1. **Add Prometheus Alert Rules**
   ```yaml
   groups:
     - name: inference
       rules:
         - alert: TabbyAPIDown
           expr: up{job="tabbyapi"} == 0
           for: 1m
           labels:
             severity: critical
           annotations:
             summary: "TabbyAPI is down"

         - alert: TabbyAPIRestartLoop
           expr: increase(systemd_unit_start_total{name="tabbyapi.service"}[10m]) > 5
           labels:
             severity: critical
           annotations:
             summary: "TabbyAPI restarting repeatedly"
   ```

2. **Configure LiteLLM Fallback**
   - Add fallback chain to route to Ollama when TabbyAPI fails
   - Set appropriate timeouts

3. **Fix prestart.sh Pattern**
   - Current pattern misses some processes
   - Use PID file for reliable tracking

### Phase 2: Operational Processes (Days)

1. **Post-Deploy Verification Runbook**
   ```bash
   # After any NixOS rebuild on hydra-ai:
   ssh hydra-ai "curl -sf http://localhost:5000/health && echo 'TabbyAPI OK' || echo 'TABBYAPI FAILED'"
   ```

2. **Change Management Process**
   - No `nixos-rebuild switch` without verification
   - Document expected behavior
   - Rollback procedure

3. **Incident Response Runbook**
   - What to check when TabbyAPI is down
   - How to identify error patterns
   - When to escalate vs auto-recover

### Phase 3: Intelligent Recovery (Weeks)

1. **TabbyAPI Manager Service**
   - Wrapper that manages TabbyAPI lifecycle
   - VRAM-aware model selection
   - Automatic fallback to smaller models
   - Health monitoring with circuit breaker
   - Metrics export

2. **Self-Healing Capabilities**
   - Detect version mismatch errors
   - Trigger venv rebuild workflow
   - Notify human but don't block

3. **Chaos Engineering**
   - Periodic failure injection
   - Verify alerting works
   - Test fallback chains

---

## Cost of Inaction

If this happens again:
- **4+ days of inference downtime**
- **Dependent services degraded** (n8n agents, SillyTavern, API consumers)
- **13,000+ log entries** polluting storage
- **CPU/power waste** from restart loops

---

## Immediate Action Items

| Priority | Action | Owner | Status |
|----------|--------|-------|--------|
| P0 | Create Prometheus alert rules | - | TODO |
| P0 | Add TabbyAPI to AlertManager routing | - | TODO |
| P1 | Configure LiteLLM fallback chain | - | TODO |
| P1 | Create post-deploy verification script | - | TODO |
| P2 | Design TabbyAPI Manager service | - | TODO |
| P2 | Document runbooks | - | TODO |

---

## Conclusion

The Dec 7-11 incident wasn't a TabbyAPI bug - it was an **operational maturity gap**. The monitoring infrastructure exists but wasn't configured. The restart limits weren't set. The fallback chains weren't built.

**The system failed not because something broke, but because nothing was watching.**

The fix isn't more band-aids on TabbyAPI's systemd service. The fix is:
1. **Alert rules that fire when services are unhealthy**
2. **Fallback chains that route around failures**
3. **Processes that verify changes work before leaving**
4. **Circuit breakers that stop retrying unfixable problems**

This is the difference between "running a service" and "operating a production system."
