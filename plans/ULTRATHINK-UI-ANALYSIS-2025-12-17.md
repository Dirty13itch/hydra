# ULTRATHINK: Hydra Frontend & UI Analysis
## Date: 2025-12-17T04:30:00Z

---

## EXECUTIVE SUMMARY

**Total UIs/Frontends: 9**
| Category | Count |
|----------|-------|
| Custom Built | 2 |
| Third-Party (Self-Hosted) | 5 |
| External APIs | 2 |

---

## CUSTOM FRONTENDS

### 1. Hydra Control Plane (Primary UI)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.244:3200 |
| **Framework** | Next.js 14.2.0 |
| **Stack** | React 18, TypeScript, Tailwind CSS, SWR |
| **Port** | 3200 (mapped from container 3000) |
| **Container** | hydra-control-plane-ui |
| **Status** | Running |

**Domain Views:**
| View | Purpose |
|------|---------|
| Overview | Cluster health dashboard, node status, service map |
| Inference | LLM model status, GPU metrics, inference endpoints |
| Storage | NFS shares, storage pools, disk health |
| Automation | n8n workflow status, scheduled tasks |
| Creative | ComfyUI integration, character generation |
| Home | Home automation controls (Lutron, Bond, Nest) |
| Intelligence | Agent orchestration, memory systems |

**Key Components (48 .tsx files):**
- `ControlPlane.tsx` - Main dashboard layout
- `LettaChat.tsx` - Conversational AI interface (Letta/MemGPT)
- `VoiceInterfacePanel.tsx` - Voice synthesis controls
- `SelfImprovementPanel.tsx` - DGM benchmark display
- `AgentOrchestrationPanel.tsx` - Multi-agent coordination
- `ServiceDependencyGraph.tsx` - Visual service topology
- `GPUMetricsPanel.tsx` - Real-time GPU monitoring
- `GrafanaEmbed.tsx` - Embedded Grafana panels
- `ComfyUIQueuePanel.tsx` - Image generation queue

**API Integration:**
- Connects to `http://192.168.1.244:8700` (Hydra Tools API)
- Uses SWR for data fetching with auto-refresh
- WebSocket support for real-time updates

---

### 2. Hydra Command Center (Agent Control)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.244:3210 (planned) |
| **Framework** | Vite + React |
| **Stack** | React 18, TypeScript, Tailwind CSS, Google GenAI |
| **Location** | /src/hydra-command-center |
| **Status** | Development |

**Views:**
| View | Purpose |
|------|---------|
| Mission | Current objectives, task queue |
| Agents | Agent fleet management, status |
| Projects | Multi-project coordination |
| Studio | Creative asset management |
| Knowledge | RAG/memory exploration |
| Lab | Experiments, benchmarks |
| Infra | Infrastructure monitoring |
| Home | Personal dashboard |

**Key Features:**
- Authentication system (AuthContext)
- Agent watching (AgentWatchContext)
- Notification system (NotificationContext)
- Conversation bridge for multi-agent chat
- ThinkingStream component for agent reasoning display

**Context Providers:**
```
AuthProvider → NotificationProvider → DashboardDataProvider → AgentProvider → AgentWatchProvider
```

---

## THIRD-PARTY FRONTENDS (Self-Hosted)

### 3. Grafana (Monitoring Dashboards)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.244:3003 |
| **Container** | hydra-grafana |
| **Data Sources** | Prometheus, Loki |
| **Status** | Running |

**Dashboards Available:**
- Cluster Overview
- GPU Metrics (DCGM)
- Container Performance
- n8n Workflow Metrics
- Inference Latency
- Alert History

**Interaction:** Embedded via iframe in Control Plane (GrafanaEmbed.tsx)

---

### 4. n8n (Workflow Automation)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.244:5678 |
| **Container** | hydra-n8n |
| **Workflows** | 20 active |
| **Status** | Running |

**Key Workflows:**
- container-restart (auto-remediation)
- wake-word-voice-chat (voice pipeline)
- llm-agent-scheduler (multi-agent)
- predictive-maintenance
- research-pipeline

**Interaction:** API triggers from Hydra Tools API, WebSocket notifications

---

### 5. Prometheus (Metrics UI)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.244:9090 |
| **Container** | hydra-prometheus |
| **Targets** | 11/11 up |
| **Status** | Running |

**Metrics Scraped:**
- Node Exporter (hydra-ai, hydra-compute, hydra-storage)
- DCGM (GPU metrics)
- cadvisor (container metrics)
- Application metrics (TabbyAPI, Ollama)

**Interaction:** Backend for Grafana, queried by Control Plane for real-time metrics

---

### 6. Open WebUI (LLM Chat)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.244:3001 |
| **Container** | open-webui |
| **Backend** | LiteLLM → TabbyAPI/Ollama |
| **Status** | Running |

**Features:**
- Multi-model chat interface
- Conversation history
- RAG document upload
- Custom personas

**Interaction:** Independent chat interface, uses same inference backends

---

### 7. Portainer (Container Management)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.244:9000 |
| **Container** | portainer |
| **Scope** | hydra-storage Docker |
| **Status** | Running |

**Capabilities:**
- Container start/stop/restart
- Log viewing
- Volume management
- Network configuration

**Interaction:** Administrative tool, not integrated with Hydra APIs

---

## EXTERNAL SERVICE UIs

### 8. ComfyUI (Image Generation)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.203:8188 |
| **Node** | hydra-compute |
| **Container** | comfyui-cu128 |
| **Status** | Running |

**Capabilities:**
- Workflow editor
- Queue management
- Model management
- Output gallery

**Interaction:** Workflows triggered via API from Hydra Tools, embedded queue status in Control Plane

---

### 9. TabbyAPI (Inference Admin)
| Attribute | Value |
|-----------|-------|
| **URL** | http://192.168.1.250:5000/docs |
| **Node** | hydra-ai |
| **Model** | Midnight-Miqu-70B |
| **Status** | Running |

**Endpoints Used:**
- `/v1/completions` - Text generation
- `/v1/model` - Model info
- `/health` - Service status

**Interaction:** Primary inference backend, OpenAI-compatible API

---

## UI INTERACTION DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐     ┌──────────────────┐                     │
│  │ Control Plane    │     │ Command Center   │                     │
│  │ (Next.js)        │     │ (Vite)           │                     │
│  │ :3200            │     │ :3210 (planned)  │                     │
│  └────────┬─────────┘     └────────┬─────────┘                     │
│           │                        │                                │
│           └───────────┬────────────┘                                │
│                       │                                             │
│                       ▼                                             │
│           ┌──────────────────────┐                                  │
│           │   Hydra Tools API    │◄───────────────────┐             │
│           │   :8700              │                    │             │
│           │   312 endpoints      │                    │             │
│           └──────────┬───────────┘                    │             │
│                      │                                │             │
│      ┌───────────────┼───────────────┐               │             │
│      │               │               │               │             │
│      ▼               ▼               ▼               │             │
│ ┌────────┐    ┌──────────┐   ┌───────────┐          │             │
│ │ Grafana│    │   n8n    │   │ Prometheus│          │             │
│ │ :3003  │    │  :5678   │   │   :9090   │          │             │
│ └────────┘    └────┬─────┘   └───────────┘          │             │
│                    │                                 │             │
│                    │ Triggers                        │             │
│                    ▼                                 │             │
│      ┌─────────────────────────────┐                │             │
│      │      External Services      │                │             │
│      ├─────────────────────────────┤                │             │
│      │ TabbyAPI (hydra-ai:5000)    │────────────────┘             │
│      │ Ollama (hydra-compute:11434)│                              │
│      │ ComfyUI (hydra-compute:8188)│                              │
│      │ Qdrant (local:6333)         │                              │
│      │ Kokoro TTS (local:8880)     │                              │
│      └─────────────────────────────┘                              │
│                                                                    │
│  Standalone:                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                        │
│  │Open WebUI│  │ Portainer│  │ Unraid   │                        │
│  │  :3001   │  │  :9000   │  │ WebGUI   │                        │
│  └──────────┘  └──────────┘  └──────────┘                        │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## DATA FLOW ANALYSIS

### Real-Time Updates
1. **Control Plane** polls Hydra Tools API every 5-30 seconds via SWR
2. **Grafana** pulls Prometheus metrics every 15s
3. **n8n** triggers webhooks to Hydra Tools API on workflow events
4. **WebSocket** connections available for:
   - Voice chat streaming
   - Agent status updates
   - ComfyUI progress

### Authentication
| UI | Auth Method |
|----|-------------|
| Control Plane | None (internal network) |
| Command Center | Custom AuthContext (token-based) |
| Grafana | Basic auth (admin/hydra) |
| n8n | Basic auth |
| Portainer | Local auth |
| Open WebUI | Local accounts |

---

## GAPS & RECOMMENDATIONS

### 1. Unified Authentication (HIGH)
**Issue:** Each UI has separate auth, no SSO
**Recommendation:** Implement OAuth2/OIDC via Authentik or Keycloak

### 2. Command Center Deployment (HIGH)
**Issue:** Not deployed, only in development
**Recommendation:** Build and deploy to port 3210

### 3. Mobile Responsiveness (MEDIUM)
**Issue:** Control Plane has limited mobile support
**Recommendation:** Add responsive breakpoints for tablet/phone

### 4. Dark Mode Consistency (LOW)
**Issue:** Some UIs don't respect system dark mode
**Recommendation:** Propagate theme settings across all UIs

### 5. Event Bus (MEDIUM)
**Issue:** No centralized event system for cross-UI updates
**Recommendation:** Implement Redis pub/sub or NATS for real-time events

### 6. Unified Dashboard (FUTURE)
**Issue:** Users must navigate multiple UIs
**Recommendation:** Create single-pane-of-glass embedding all key widgets

---

## COMPONENT INVENTORY

### Control Plane Components (48 total)
| Category | Components | Purpose |
|----------|------------|---------|
| Core | 8 | Layout, routing, state |
| Monitoring | 12 | GPU, services, nodes, storage |
| Domain Views | 7 | Inference, automation, creative, etc. |
| Embedded | 4 | Grafana, ComfyUI, workflows, home |
| Chat/Voice | 3 | LettaChat, VoiceInterface |
| Utility | 14 | Skeleton, Toast, StatusIndicator |

### Command Center Views (8 total)
- Mission, Agents, Projects, Studio, Knowledge, Lab, Infra, Home

### Context Providers (5 total)
- Auth, Notification, AgentWatch, Agent, DashboardData

---

## CONCLUSION

The Hydra system has a comprehensive UI ecosystem with:
- **2 custom frontends** providing cluster management and agent orchestration
- **5 self-hosted tools** for monitoring, automation, and container management
- **2 external UIs** for image generation and LLM inference

**Key Integrations:**
- All custom UIs connect through Hydra Tools API (312 endpoints)
- Grafana embeds provide monitoring without context switching
- n8n provides automation triggers via webhooks
- ComfyUI workflows are triggered via API

**Primary Gap:** Command Center is not deployed - would provide dedicated agent management UI.

**Interaction Flow:**
```
User → Control Plane/Command Center → Hydra Tools API → Backend Services
```

All UIs are operational on hydra-storage (192.168.1.244) except:
- ComfyUI (hydra-compute:8188)
- TabbyAPI (hydra-ai:5000)
