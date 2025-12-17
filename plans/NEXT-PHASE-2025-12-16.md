# HYDRA NEXT PHASE - December 16, 2025
## Post-13-Task Analysis and Priority Actions

---

## EXECUTIVE SUMMARY

**Previous Session Completed:** 13 tasks across 3 tiers
**API Version:** 1.7.0 (8 new routers added)
**Container Health:** 36/36 (100%)
**System Status:** HEALTHY

---

## CURRENT OPERATIONAL STATUS

### New Endpoints Deployed (Last Session)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/calendar` | Working | Afternoon/weekday mode active |
| `/presence` | Built | Needs HA_TOKEN env var |
| `/benchmark` | Working | 6 categories ready |
| `/memory` | Working | 14 memories in 6 tiers |
| `/discord` | Built | Needs DISCORD_WEBHOOK_URL env var |
| `/constitution` | Working | Integrity valid |
| `/self-improvement` | Working | Ready for proposals |
| `/sandbox` | Working | Docker connected, 9 executions |
| `/predictive` | Working | All systems healthy |
| `/container-health` | Working | 36/36 containers |
| `/preference-collector` | Working | Ready to collect data |

### GPU Status
```
hydra-ai:
  RTX 5090: 50GB/56GB VRAM, 37°C, 24W
  RTX 4090: 20GB/24GB VRAM, 30°C, 4W

hydra-compute:
  RTX 5070 Ti #1: 9GB/16GB VRAM, 40°C, 18W
  RTX 5070 Ti #2: 0.7GB/16GB VRAM, 37°C, 11W
```

### Scheduler Status
- Monitoring: Daily 6:00 AM CST (next: Dec 17)
- Research: Weekly Monday 2:00 AM (next: Dec 22)
- Maintenance: Weekly Sunday 3:00 AM (next: Dec 21)

---

## TIER 1: IMMEDIATE (Environment Configuration)

### 1.1 Configure Discord Webhook
**Effort:** 15 minutes | **Impact:** HIGH

Discord webhook URL exists in n8n but not in hydra-tools-api.

```bash
# Recreate hydra-tools-api with Discord env var
docker stop hydra-tools-api
docker run -d --name hydra-tools-api-new \
  --network hydra-network \
  -p 8700:8700 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v hydra-tools_hydra-tools-data:/data \
  -v /mnt/user/appdata/hydra-stack/data:/mnt/data \
  -v /mnt/user/appdata/hydra-dev/src/hydra_tools:/app/src/hydra_tools:ro \
  -v /mnt/user/appdata/hydra-dev/CONSTITUTION.yaml:/app/CONSTITUTION.yaml:ro \
  -v /mnt/user/appdata/hydra-dev/logs:/app/logs \
  -e DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1450248508513714239/6xUKn-nrHvhs50uiFXfFkkrONu-bxtCMs5PRYbNwEQ4K0vbGIVIiZWAcpOEuMC72BK7N" \
  -e TZ="America/Chicago" \
  hydra-tools-api:latest

# Or simpler: use Unraid Docker UI to add env var
```

---

### 1.2 Configure Home Assistant Token
**Effort:** 15 minutes | **Impact:** HIGH

Create long-lived access token in Home Assistant.

```bash
# 1. Go to Home Assistant UI
#    http://192.168.1.244:8123/profile/security
#
# 2. Scroll to "Long-lived access tokens"
#
# 3. Click "Create Token", name it "hydra-api"
#
# 4. Add to hydra-tools-api container:
#    -e HA_TOKEN="<your-token>"
#    -e HA_URL="http://192.168.1.244:8123"
```

---

### 1.3 Wire LiteLLM Preference Callback
**Effort:** 30 minutes | **Impact:** MEDIUM

Configure LiteLLM to send usage data to preference collector.

```yaml
# Add to LiteLLM config:
litellm_settings:
  success_callback: ["webhook"]
  failure_callback: ["webhook"]
  callbacks:
    webhook_url: "http://192.168.1.244:8700/preference-collector/litellm/callback"
```

```bash
# Or via environment variable in hydra-litellm:
# LITELLM_CALLBACKS=webhook
# LITELLM_WEBHOOK_URL=http://192.168.1.244:8700/preference-collector/litellm/callback
```

---

## TIER 2: VOICE INTERFACE COMPLETION

### 2.1 Fix Voice LLM Connection
**Effort:** 30 minutes | **Impact:** HIGH

Voice pipeline shows LLM status "error".

```bash
# Check voice status
curl -s http://192.168.1.244:8700/voice/status | jq .

# Voice API uses LiteLLM at http://192.168.1.244:4000
# Verify LiteLLM is accessible:
curl -s http://192.168.1.244:4000/health
```

**Files to check:**
- `src/hydra_tools/voice_api.py` - LLM endpoint configuration

---

### 2.2 Deploy Wake Word Detection
**Effort:** 1-2 hours | **Impact:** HIGH

Enable hands-free voice activation.

**Options:**
1. **OpenWakeWord** (recommended) - Open source, runs locally
2. **Porcupine** - Proprietary but free tier available

```bash
# OpenWakeWord container
docker run -d --name hydra-wakeword \
  --network hydra-network \
  -v /mnt/user/appdata/hydra-stack/data/wakeword:/data \
  -p 8765:8765 \
  rhasspy/openWakeWord:latest
```

---

### 2.3 Wire Whisper STT
**Effort:** 1 hour | **Impact:** HIGH

Connect Faster-Whisper for speech-to-text.

```bash
# Check if Whisper is available
curl -s http://192.168.1.244:8700/voice/transcribe --help

# Faster-Whisper can run on hydra-compute GPU #2 (mostly idle)
```

---

## TIER 3: OPTIMIZATION

### 3.1 Deploy Speculative Decoding
**Effort:** 2 hours | **Impact:** HIGH (potential 2x speedup)

From last session's research: ExLlamaV2 supports speculative decoding.

```yaml
# TabbyAPI config update:
model:
  draft:
    model_name: Mistral-7B-Instruct-v0.3-exl2-4.0bpw
    draft_rope_alpha: 1.0
```

**Expected:** 25 tok/s → 45-60 tok/s

---

### 3.2 Run Baseline Benchmarks
**Effort:** 30 minutes | **Impact:** MEDIUM

Establish baseline for self-improvement tracking.

```bash
# Run full benchmark suite
curl -X POST http://192.168.1.244:8700/benchmark/run | jq .

# Individual benchmarks
curl -X POST http://192.168.1.244:8700/benchmark/single/api_availability | jq .
curl -X POST http://192.168.1.244:8700/benchmark/single/container_health | jq .
curl -X POST http://192.168.1.244:8700/benchmark/single/inference_latency | jq .
```

---

### 3.3 Create Self-Improvement Workflow
**Effort:** 2 hours | **Impact:** HIGH

Implement DGM-inspired proposal → test → deploy loop.

**Flow:**
1. Monitor benchmark scores
2. Generate improvement proposals via LLM
3. Test in sandbox
4. If passes, create PR for review
5. Deploy after approval

---

## TIER 4: FUTURE WORK

### 4.1 Multi-Agent Orchestration
- Implement AIOS-style agent scheduling
- Create agent memory isolation
- Build tool access control

### 4.2 Empire Pipeline Automation
- Character consistency via InstantID
- Automated scene generation
- Voice synthesis for dialogue

### 4.3 External Integrations
- Google Calendar sync
- Email digest automation
- GitHub PR workflows

---

## QUICK COMMANDS

```bash
# Check all new endpoints
curl -s http://192.168.1.244:8700/calendar/status | jq .
curl -s http://192.168.1.244:8700/presence/status | jq .
curl -s http://192.168.1.244:8700/benchmark/status | jq .
curl -s http://192.168.1.244:8700/memory/status | jq .
curl -s http://192.168.1.244:8700/discord/status | jq .
curl -s http://192.168.1.244:8700/constitution/status | jq .
curl -s http://192.168.1.244:8700/self-improvement/status | jq .
curl -s http://192.168.1.244:8700/sandbox/status | jq .
curl -s http://192.168.1.244:8700/predictive/health | jq .
curl -s http://192.168.1.244:8700/container-health/status | jq .
curl -s http://192.168.1.244:8700/preference-collector/stats | jq .

# Trigger benchmark run
curl -X POST http://192.168.1.244:8700/benchmark/run

# Test presence change
curl -X POST http://192.168.1.244:8700/presence/set/away

# Execute sandbox code
curl -X POST http://192.168.1.244:8700/sandbox/execute \
  -H "Content-Type: application/json" \
  -d '{"language": "python", "code": "print(2+2)"}'
```

---

## SUCCESS METRICS

| Metric | Current | Target |
|--------|---------|--------|
| Container Health | 100% | Maintain |
| Voice Interface | Partial | Full |
| Preference Data | 0 | 100+ interactions |
| Benchmark Baseline | None | Established |
| Discord Notifications | n8n only | API + n8n |
| Presence Automation | Manual | HA-synced |

---

*Generated: 2025-12-16T12:10:00Z*
*Author: Claude Code (Opus 4.5) as Hydra Autonomous Steward*
