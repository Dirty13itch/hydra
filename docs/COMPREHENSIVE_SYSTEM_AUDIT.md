# Hydra System Comprehensive Audit
**Generated:** 2025-12-18
**Purpose:** Deep analysis of all components for User Data Management System design

## Executive Summary

The Hydra ecosystem consists of:
- **73+ Docker containers** on hydra-storage
- **5 services** on hydra-compute (NixOS)
- **1 systemd service** on hydra-ai (NixOS)
- **665 API endpoints** in Hydra Tools API
- **13 Command Center views**
- **3 compute nodes** with 88GB+ total VRAM

---

## Part 1: Container Inventory by Category

### 1.1 AI Core Services (12 containers)

| Container | Port | Purpose | Credentials Required |
|-----------|------|---------|---------------------|
| hydra-tools-api | 8700 | Main Hydra API (665 endpoints) | Internal only |
| hydra-command-center | 3210 | React dashboard UI | User auth (internal) |
| hydra-litellm | 4000 | LLM router to backends | `LITELLM_MASTER_KEY` |
| hydra-letta | 8283 | Memory/agent framework | `LETTA_PASSWORD` |
| hydra-crewai | 8500 | Multi-agent orchestration | Internal only |
| hydra-mcp | 8600 | Model Context Protocol hub | Internal only |
| kokoro-tts | 8880 | Voice synthesis | None |
| gpt-researcher | 8090 | Research agent | `OPENAI_API_KEY` via LiteLLM |
| local-deep-research | 5050 | Deep research agent | LiteLLM connection |
| openhands | 3015 | Code agent (E2B-like) | `LLM_API_KEY` |
| letta-proxy | 8400 | Letta API proxy | None |
| hydra-brain | - | Background worker | Internal only |

### 1.2 Databases (7 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| hydra-postgres | 5432 | Primary database | `POSTGRES_PASSWORD` |
| hydra-neo4j | 7474/7687 | Graph database (Graphiti) | `NEO4J_AUTH` |
| hydra-qdrant | 6333/6334 | Vector database | None (no auth) |
| hydra-redis | 6379 | Cache + pub/sub | `REDIS_PASSWORD` |
| hydra-meilisearch | 7700 | Full-text search | `MEILI_MASTER_KEY` |
| letta-db | 5432 (internal) | pgvector for Letta | `POSTGRES_PASSWORD` |
| hydra-firecrawl-redis | 6379 (internal) | Firecrawl queue | None |

### 1.3 Web/Research Stack (5 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| hydra-firecrawl-api | 3005 | Web scraping API | None |
| hydra-firecrawl-worker | - | Async scraper workers | - |
| hydra-firecrawl-playwright | - | Browser automation | - |
| hydra-docling | 5001 | Document parsing | None |
| hydra-searxng | 8888 | Meta search engine | None |
| perplexica | 3030 | AI-powered search | LiteLLM connection |

### 1.4 Monitoring & Observability (11 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| hydra-prometheus | 9090 | Metrics collection | None |
| hydra-grafana | 3003 | Metrics visualization | `GF_SECURITY_ADMIN_PASSWORD` |
| hydra-alertmanager | 9093 | Alert routing | Webhook configs |
| hydra-loki | 3100 | Log aggregation | None |
| hydra-promtail | - | Log shipper | None |
| hydra-uptime-kuma | 3004 | Status page | User-set password |
| hydra-watchtower | - | Container updates | Docker socket |
| prometheus-pushgateway | 9091 | Push metrics | None |
| node-exporter | - | Node metrics | None |
| gpu-metrics-api | 8701 | GPU metrics aggregator | None |
| auditforecaster-monitor | 3002 | AF health monitor | None |

### 1.5 Media & Download Stack (14 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| Plex-Media-Server | 32400 | Media server | Plex account |
| stash | 9999 | Adult media organizer | User-set |
| pigallery2 | 8280 | Photo gallery | None |
| sonarr | 8989 | TV show management | API key |
| radarr | 7878 | Movie management | API key |
| prowlarr | 9696 | Indexer management | API key |
| lidarr | 8686 | Music management | API key |
| readarr | 8787 | Book management | API key |
| whisparr | 6969 | Adult content management | API key |
| bazarr | 6767 | Subtitle management | API key |
| sabnzbd | 8085 | Usenet downloader | API key + Usenet account |
| qbittorrent | 8082 | Torrent client | User-set |

### 1.6 Smart Home (2 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| homeassistant | 8123 | Home automation hub | `HA_TOKEN` (Long-lived) |
| wyoming-openwakeword | 10400 | Voice wake word | None |

### 1.7 Infrastructure (5 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| tailscale | - | VPN mesh | Tailscale account |
| adguard | 53/3380 | DNS + ad blocking | User-set |
| portainer | 9000 | Docker management | User-set |
| vaultwarden | (via caddy) | Password manager | Master password |
| caddy-vaultwarden | 8444 | HTTPS proxy | None |

### 1.8 Alternative AI UIs (4 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| open-webui | 3001 | ChatGPT-like UI | User accounts |
| sillytavern | 8000 | Character chat UI | None |
| homepage | 3333 | Service dashboard | Service API keys |
| hydra-control-plane-ui | 3200 | Legacy control plane | None |

### 1.9 Automation (2 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| hydra-n8n | 5678 | Workflow automation | User accounts |
| hydra-miniflux | 8180 | RSS reader | `MINIFLUX_API_KEY` |

### 1.10 Project-Specific (8 containers)

| Container | Port | Purpose | Credentials |
|-----------|------|---------|-------------|
| empire-control-plane | 8081 | VN game backend | None |
| hydra-control-plane-backend | 3101 | Legacy backend | None |
| hydra-task-hub | 8800 | Task management | None |
| agent-writer | - | Writing agent | None |
| auditforecaster-ui | 3000 | AF frontend | None |
| auditforecaster-db | 5433 | AF database | `POSTGRES_PASSWORD` |
| auditforecaster-backup | - | AF backup | None |
| auditforecaster-proxy | 8080 | AF reverse proxy | None |
| auditforecaster-redis | - | AF cache | None |

---

## Part 2: Remote Node Services

### 2.1 hydra-ai (192.168.1.250)

| Service | Port | Type | Credentials |
|---------|------|------|-------------|
| TabbyAPI | 5000 | systemd | Admin key optional |
| Node Exporter | 9100 | systemd | None |
| SSH | 22 | system | SSH key |

**Hardware:** RTX 5090 (32GB) + RTX 4090 (24GB) = 56GB VRAM

### 2.2 hydra-compute (192.168.1.203)

| Service | Port | Type | Credentials |
|---------|------|------|-------------|
| ComfyUI | 8188 | Docker | None |
| TabbyAPI | 5000 | Docker | None |
| Kohya Training | - | Docker | None |
| Whisper ASR | - | Docker | None |
| Ollama | 11434 | NixOS service | None |
| Node Exporter | 9100 | Docker | None |

**Hardware:** 2x RTX 5070 Ti (16GB each) = 32GB VRAM

---

## Part 3: API Endpoint Analysis (665 total)

### 3.1 Endpoint Categories by Count

| Category | Count | Description |
|----------|-------|-------------|
| characters | 52 | VN character management |
| autonomous | 28 | Autonomous agent operations |
| memory | 27 | Memory systems (multiple types) |
| unraid | 26 | Unraid server management |
| self-improvement | 21 | Self-modification capabilities |
| crews | 20 | CrewAI integration |
| agent-scheduler | 17 | Agent task scheduling |
| dashboard | 15 | Dashboard data |
| alerts | 13 | Alert management |
| container-health | 13 | Docker health monitoring |
| news | 13 | RSS/news integration |
| skill-learning | 13 | Skill acquisition |
| graphiti-memory | 12 | Neo4j graph memory |
| home-automation | 12 | Home Assistant integration |
| conversation-cache | 11 | Conversation caching |
| routing | 11 | LLM routing |
| speculative-decoding | 11 | Inference optimization |
| briefing | 10 | Morning briefings |
| cognitive | 10 | Cognitive processing |
| gmail | 10 | Gmail integration |
| multi-agent-memory | 10 | Shared agent memory |
| presence | 10 | HA presence detection |
| asset-quality | 9 | Image quality scoring |
| autonomous-research | 9 | Research automation |
| cluster-health | 9 | Cluster monitoring |

### 3.2 External Integration APIs

| Integration | Endpoints | Credentials Needed |
|-------------|-----------|-------------------|
| Google Calendar | 6 | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| Gmail | 8 | Same OAuth as Calendar |
| Home Assistant | 12 | `HA_TOKEN` |
| Miniflux (News) | 13 | `MINIFLUX_API_KEY` |
| Discord | 3 | `DISCORD_WEBHOOK_URL` |
| Kokoro TTS | 5 | None (local) |

---

## Part 4: Command Center Views Analysis

### 4.1 Current Views (13)

| View | File | Purpose | Data Dependencies |
|------|------|---------|-------------------|
| **Mission** | Mission.tsx | Dashboard overview | Dashboard stats, cluster health |
| **Agents** | Agents.tsx | Agent management | Agent status, logs, configs |
| **Chat** | Chat.tsx | LLM conversation | LiteLLM, conversation cache |
| **Projects** | Projects.tsx | Project tracking | Project DB |
| **Studio** | Studio.tsx | Creative generation | ComfyUI, character system |
| **Knowledge** | Knowledge.tsx | RAG management | Qdrant, ingest pipeline |
| **Research** | Research.tsx | Research tasks | Autonomous research queue |
| **Feedback** | Feedback.tsx | Human feedback UI | Feedback DB, quality scores |
| **Briefing** | Briefing.tsx | Morning briefings | Calendar, Gmail, News, Health |
| **Lab** | Lab.tsx | Experiments | Various experimental APIs |
| **Infra** | Infra.tsx | Infrastructure | Node metrics, GPU stats |
| **Home** | Home.tsx | Home automation | HA WebSocket, presence |
| **Login** | Login.tsx | Authentication | Auth context |

### 4.2 Missing Views (Identified Gaps)

| Missing View | Purpose | Why Needed |
|--------------|---------|------------|
| **Settings** | User preferences, credentials | No centralized config UI |
| **Notifications** | Alert history, preferences | Notifications exist but no view |
| **Models** | Model management, hot-swap | Critical for inference control |
| **Workflows** | n8n integration view | Automation visibility |
| **Logs** | Centralized log viewer | Currently only in Grafana |
| **Security** | Credential status, audit | No security dashboard |

---

## Part 5: Credential Requirements Matrix

### 5.1 External Services (User Must Provide)

| Credential | Used By | Features Unlocked | Priority |
|------------|---------|------------------|----------|
| `GOOGLE_CLIENT_ID` | Calendar, Gmail | External intelligence | HIGH |
| `GOOGLE_CLIENT_SECRET` | Calendar, Gmail | External intelligence | HIGH |
| `HA_TOKEN` | Home automation | Smart home control | HIGH |
| `MINIFLUX_API_KEY` | News | RSS monitoring | MEDIUM |
| `DISCORD_WEBHOOK_URL` | Alerts, Briefings | Discord notifications | LOW |
| Plex Account | Plex | Media streaming | MEDIUM |
| Usenet Provider | SABnzbd | Download automation | LOW |
| Tailscale Account | VPN | Remote access | LOW |

### 5.2 Internal Credentials (Pre-configured)

| Credential | Service | Current Value | Notes |
|------------|---------|---------------|-------|
| `POSTGRES_PASSWORD` | hydra-postgres | `g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6` | Core DB |
| `REDIS_PASSWORD` | hydra-redis | `ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC` | Cache |
| `LITELLM_MASTER_KEY` | hydra-litellm | `sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7` | LLM routing |
| `LETTA_PASSWORD` | hydra-letta | `HydraLetta2024!` | Memory |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana | `HydraGrafana2024!` | Monitoring |
| `NEO4J_AUTH` | hydra-neo4j | neo4j/HydraNeo4j2024! | Graph DB |

### 5.3 Arr Stack API Keys (Auto-generated)

| Service | Config Location | How to Get |
|---------|-----------------|------------|
| Sonarr | Settings > General | UI generated |
| Radarr | Settings > General | UI generated |
| Prowlarr | Settings > General | UI generated |
| Lidarr | Settings > General | UI generated |
| Readarr | Settings > General | UI generated |
| Whisparr | Settings > General | UI generated |
| Bazarr | Settings > General | UI generated |

---

## Part 6: User Data Categories

### 6.1 Category Breakdown

| Category | Examples | Storage Type |
|----------|----------|--------------|
| **Credentials** | API keys, OAuth tokens | Encrypted (Vaultwarden) |
| **Preferences** | Theme, notification settings | Profile (JSON) |
| **Contacts** | Priority email contacts | Database |
| **Locations** | Home, work, gym addresses | Profile |
| **Schedules** | Work hours, quiet times | Profile |
| **Media Prefs** | Favorite genres, ratings | Database |
| **News Topics** | Monitored keywords | Database |
| **Financial** | (Future) Plaid, crypto | Encrypted |
| **Home Zones** | HA zones, automations | Profile |
| **AI Prefs** | Model preferences, temp | Profile |
| **Goals** | Current projects, priorities | Database |

### 6.2 Storage Layer Recommendations

```
┌─────────────────────────────────────────────────┐
│                  VAULT LAYER                     │
│   (Vaultwarden - encrypted at rest)             │
│   • API keys, OAuth tokens, passwords           │
│   • Never exposed to frontend directly          │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│                 PROFILE LAYER                    │
│   (PostgreSQL - user_profiles table)            │
│   • Preferences, settings, schedules            │
│   • Exposed via /user-data/* endpoints          │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│                 MEMORY LAYER                     │
│   (Qdrant + Neo4j + Redis)                      │
│   • Conversation history, learned patterns      │
│   • Goals, relationships, context               │
└─────────────────────────────────────────────────┘
```

---

## Part 7: Recommended Implementation Plan

### 7.1 Phase 1: Core Infrastructure (Week 1)

1. **Create user_data schema in PostgreSQL**
   - profiles, preferences, contacts tables
   - credentials_status table (tracks what's configured, not values)

2. **Add `/user-data/*` API endpoints**
   - GET/PUT /user-data/profile
   - GET/PUT /user-data/preferences
   - GET /user-data/credentials-status
   - POST /user-data/test-credential/{type}

3. **Create Settings View in Command Center**
   - Profile section
   - Credentials status section
   - Preferences section

### 7.2 Phase 2: Credential Management (Week 2)

1. **OAuth flow integration**
   - Google OAuth popup flow
   - Token storage in server-side encrypted store

2. **API key validation endpoints**
   - Test connectivity for each service
   - Clear status indicators

3. **Feature dependency mapping**
   - Show which features unlock with each credential

### 7.3 Phase 3: Deep Integration (Week 3)

1. **Per-view integration**
   - Each view checks required credentials
   - Graceful degradation with setup prompts

2. **Onboarding flow**
   - First-run wizard
   - Progressive disclosure

3. **UserDataProvider context**
   - Global state for user data
   - Caching and refresh logic

---

## Part 8: Security Considerations

### 8.1 Constitutional Constraints

From `data/CONSTITUTION.yaml`:
- Never store credentials in plaintext in code
- Never expose secrets to logs
- Require human approval for credential changes
- Maintain audit trail of credential access

### 8.2 Implementation Requirements

1. **Credentials must be encrypted at rest**
   - Use Vaultwarden or similar
   - Never store raw values in PostgreSQL

2. **Frontend never sees raw credentials**
   - Only status (configured/not configured)
   - Only test results (valid/invalid)

3. **OAuth tokens refreshed server-side**
   - No refresh tokens in browser
   - Server handles token lifecycle

4. **Audit logging**
   - Log all credential access attempts
   - Log all configuration changes

---

## Part 9: User Experience Flows

### 9.1 New User Onboarding

```
[First Login]
    │
    ▼
[Welcome Screen]
    │
    ▼
[Core Setup]
  • Display name
  • Time zone
  • Theme preference
    │
    ▼
[Optional Integrations]
  • Google (Calendar + Gmail)
  • Home Assistant
  • News (Miniflux)
  • Discord
    │
    ▼
[Feature Preview]
  • Show what's enabled/disabled
  • Quick access to Settings
```

### 9.2 Credential Setup Flow (Google Example)

```
[Settings > Credentials > Google]
    │
    ▼
[Status: Not Configured]
    │
    ├── [Setup Button] ──► [OAuth Popup]
    │                          │
    │                          ▼
    │                     [Google Consent]
    │                          │
    │                          ▼
    │                     [Callback Handler]
    │                          │
    │                          ▼
[Status: Configured ✓] ◄──────┘
    │
    ▼
[Test Connection] ──► [Calendar: ✓] [Gmail: ✓]
```

### 9.3 Feature Dependency Display

```
┌─────────────────────────────────────────────────┐
│ Briefing View                                   │
├─────────────────────────────────────────────────┤
│ ✓ System Health      [Always Available]         │
│ ✓ Voice Synthesis    [Kokoro - Local]           │
│ ⚠ Calendar           [Requires: Google OAuth]   │
│ ⚠ Email Summary      [Requires: Google OAuth]   │
│ ⚠ News Headlines     [Requires: Miniflux API]   │
│ ✗ Weather            [Not Yet Implemented]      │
└─────────────────────────────────────────────────┘
         │
         ▼
    [Configure Google] [Configure Miniflux]
```

---

## Part 10: Container Management Recommendations

### 10.1 Containers Needing User Visibility

| Container | Why User Needs Visibility |
|-----------|---------------------------|
| Plex | Transcode status, library stats |
| Home Assistant | Device status, automations |
| SABnzbd | Download queue, speed |
| qBittorrent | Torrent status |
| Sonarr/Radarr | Upcoming releases, wanted |
| Grafana | Metrics dashboards |
| n8n | Workflow status |

### 10.2 Containers for Admin Only

| Container | Why Admin Only |
|-----------|---------------|
| hydra-postgres | Database management |
| hydra-redis | Cache management |
| hydra-prometheus | Metrics backend |
| hydra-loki | Log backend |
| All firecrawl-* | Infrastructure |
| portainer | Docker management |

### 10.3 Recommended Dashboard Integrations

| Integration | Data to Show | API Source |
|-------------|--------------|------------|
| Plex | Now Playing, Library Size | Tautulli API |
| *Arr Stack | Upcoming, Downloads | Individual APIs |
| Home Assistant | Active entities, scenes | WebSocket |
| n8n | Active workflows, recent runs | n8n API |

---

## Part 11: Complete Environment Variable Audit

### 11.1 External User-Provided Credentials (REQUIRED for features)

| Variable | Used By | Feature Unlocked | Default |
|----------|---------|------------------|---------|
| `GOOGLE_CLIENT_ID` | google_calendar, gmail | Calendar, Email | Empty (required) |
| `GOOGLE_CLIENT_SECRET` | google_calendar, gmail | Calendar, Email | Empty (required) |
| `HA_TOKEN` | home_automation, presence | Smart home control | Empty (required) |
| `MINIFLUX_API_KEY` | news_integration | News/RSS monitoring | Empty |
| `MINIFLUX_USERNAME` | news_integration | Alt: Miniflux login | Empty |
| `MINIFLUX_PASSWORD` | news_integration | Alt: Miniflux login | Empty |
| `DISCORD_WEBHOOK_URL` | discord_bot, alerts, daily_digest | Discord notifications | Empty |
| `DISCORD_BOT_TOKEN` | discord_bot | Discord bot commands | Empty |
| `WEATHER_API_KEY` | morning_briefing | Weather in briefings | Empty |
| `WEATHER_LOCATION` | morning_briefing | Location for weather | "Austin,TX" |
| `UNRAID_API_KEY` | unraid_client | Unraid management | Empty |
| `VPN_SERVICE_PROVIDER` | Gluetun | VPN for downloads | Empty |
| `VPN_USERNAME` | Gluetun | VPN credentials | Empty |
| `VPN_PASSWORD` | Gluetun | VPN credentials | Empty |

### 11.2 Internal Pre-Configured Credentials (System managed)

| Variable | Service | Current Default |
|----------|---------|-----------------|
| `LITELLM_API_KEY` | LiteLLM router | `sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7` |
| `LITELLM_MASTER_KEY` | LiteLLM admin | Same as above |
| `LITELLM_SALT_KEY` | LiteLLM hashing | Custom |
| `POSTGRES_PASSWORD` | PostgreSQL | `g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6` |
| `REDIS_PASSWORD` | Redis | `ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC` |
| `NEO4J_PASSWORD` | Neo4j | `HydraNeo4jPass2024` |
| `NEO4J_USER` | Neo4j | `neo4j` |
| `MEILISEARCH_KEY` | Meilisearch | Empty (no auth) |
| `GRAFANA_PASSWORD` | Grafana | `HydraGrafana2024!` |
| `VAULTWARDEN_ADMIN_TOKEN` | Vaultwarden | Custom |
| `HYDRA_API_KEY` | Hydra API | `hydra-dev-key` |

### 11.3 Service URLs (Pre-configured with defaults)

| Variable | Default Value | Service |
|----------|---------------|---------|
| `LITELLM_URL` | `http://192.168.1.244:4000` | LiteLLM |
| `QDRANT_URL` | `http://192.168.1.244:6333` | Qdrant |
| `OLLAMA_URL` | `http://192.168.1.203:11434` | Ollama |
| `TABBYAPI_URL` | `http://192.168.1.250:5000` | TabbyAPI |
| `MEILISEARCH_URL` | `http://192.168.1.244:7700` | Meilisearch |
| `SEARXNG_URL` | `http://192.168.1.244:8888` | SearXNG |
| `FIRECRAWL_URL` | `http://192.168.1.244:3005` | Firecrawl |
| `COMFYUI_URL` | `http://192.168.1.203:8188` | ComfyUI |
| `PROMETHEUS_URL` | `http://192.168.1.244:9090` | Prometheus |
| `LOKI_URL` | `http://192.168.1.244:3100` | Loki |
| `TTS_URL` | `http://192.168.1.244:8880` | Kokoro TTS |
| `STT_URL` | `http://192.168.1.203:9002` | Whisper ASR |
| `HA_URL` | `http://192.168.1.244:8123` | Home Assistant |
| `N8N_URL` | `http://192.168.1.244:5678` | n8n |
| `LETTA_URL` | `http://192.168.1.244:8283` | Letta |

### 11.4 Data Paths (Pre-configured)

| Variable | Default | Purpose |
|----------|---------|---------|
| `HYDRA_DATA_DIR` | `/data` | Persistent data |
| `HYDRA_SHARED_PATH` | `/mnt/user/hydra_shared` | Shared storage |
| `EXL2_MODEL_DIR` | `/mnt/models` | ExL2 models |
| `OLLAMA_MODEL_DIR` | `/mnt/user/appdata/ollama` | Ollama models |
| `COMFYUI_TEMPLATES_DIR` | Various | ComfyUI workflows |

### 11.5 Feature Dependency Matrix

| Feature | Required Credentials | Optional |
|---------|---------------------|----------|
| **Morning Briefing** | None (basic) | Google (full), Miniflux, Weather |
| **Calendar View** | `GOOGLE_CLIENT_ID/SECRET` | - |
| **Email Summary** | `GOOGLE_CLIENT_ID/SECRET` | - |
| **Home Automation** | `HA_TOKEN` | - |
| **Presence Detection** | `HA_TOKEN` | - |
| **News Monitoring** | `MINIFLUX_API_KEY` or username/password | - |
| **Discord Alerts** | `DISCORD_WEBHOOK_URL` | `DISCORD_BOT_TOKEN` (commands) |
| **Weather** | `WEATHER_API_KEY` | - |
| **VPN Downloads** | `VPN_*` credentials | - |
| **LLM Inference** | None (internal) | - |
| **Image Generation** | None (internal) | - |
| **Voice Synthesis** | None (internal) | - |
| **Research Agents** | None (internal) | - |
| **Knowledge Base** | None (internal) | - |

---

## Appendix A: Full Container List (73 containers)

```
AI Core (12):
  hydra-tools-api, hydra-command-center, hydra-litellm, hydra-letta,
  hydra-crewai, hydra-mcp, kokoro-tts, gpt-researcher, local-deep-research,
  openhands, letta-proxy, hydra-brain

Databases (7):
  hydra-postgres, hydra-neo4j, hydra-qdrant, hydra-redis, hydra-meilisearch,
  letta-db, hydra-firecrawl-redis

Web/Research (6):
  hydra-firecrawl-api, hydra-firecrawl-worker, hydra-firecrawl-playwright,
  hydra-docling, hydra-searxng, perplexica

Monitoring (11):
  hydra-prometheus, hydra-grafana, hydra-alertmanager, hydra-loki,
  hydra-promtail, hydra-uptime-kuma, hydra-watchtower, prometheus-pushgateway,
  node-exporter, gpu-metrics-api, auditforecaster-monitor

Media (14):
  Plex-Media-Server, stash, pigallery2, sonarr, radarr, prowlarr, lidarr,
  readarr, whisparr, bazarr, sabnzbd, qbittorrent

Smart Home (2):
  homeassistant, wyoming-openwakeword

Infrastructure (5):
  tailscale, adguard, portainer, vaultwarden, caddy-vaultwarden

UIs (4):
  open-webui, sillytavern, homepage, hydra-control-plane-ui

Automation (2):
  hydra-n8n, hydra-miniflux

Project-Specific (10):
  empire-control-plane, hydra-control-plane-backend, hydra-task-hub,
  agent-writer, auditforecaster-ui, auditforecaster-db, auditforecaster-backup,
  auditforecaster-proxy, auditforecaster-redis, happy_hopper
```

---

## Appendix B: API Endpoint Summary

**Total Endpoints:** 665

**Top 25 Categories:**
1. characters (52), autonomous (28), memory (27), unraid (26)
2. self-improvement (21), crews (20), agent-scheduler (17), dashboard (15)
3. alerts (13), container-health (13), news (13), skill-learning (13)
4. graphiti-memory (12), home-automation (12), conversation-cache (11)
5. routing (11), speculative-decoding (11), briefing (10), cognitive (10)
6. gmail (10), multi-agent-memory (10), presence (10), asset-quality (9)
7. autonomous-research (9), cluster-health (9)

---

## Conclusion

The Hydra system is a comprehensive AI infrastructure with:
- Strong foundation (databases, monitoring, automation)
- Rich API surface (665 endpoints)
- Multiple integration points (home, media, external services)

**Key Gap:** No centralized user data management or Settings view.

**Recommendation:** Implement the User Data Management System as described in Part 7, prioritizing:
1. Settings View in Command Center
2. Credential status tracking
3. Feature dependency mapping
4. OAuth integration flows

This will transform Hydra from a developer-configured system to a user-friendly autonomous AI platform.
