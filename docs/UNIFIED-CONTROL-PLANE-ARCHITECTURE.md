# Hydra Unified Control Plane Architecture

## Executive Summary

After comprehensive ULTRATHINK analysis of 10+ web interfaces, 5 Grafana dashboards, and the existing Control Plane UI codebase, the recommendation is **NOT to merge all UIs into a monolith**, but rather to evolve the **Control Plane UI as a Universal Hub with Embedded Specialists**.

This document outlines the architecture, implementation strategy, and phased rollout for achieving a cohesive yet flexible control experience.

---

## Current State Analysis

### UI Landscape (December 2025)

| Category | UI | Port | Purpose | Merge Strategy |
|----------|-----|------|---------|----------------|
| **Hub** | Control Plane UI | 3200 | Primary dashboard | **ENHANCE** - Universal entry point |
| **Quick Access** | Homepage | 3333 | Service directory | **KEEP** - Lightweight backup |
| **Observability** | Grafana | 3003 | Deep metrics | **EMBED** - iframe integration |
| **Containers** | Portainer | 9000 | Docker management | **LINK** - Emergency access |
| **Monitoring** | Uptime Kuma | 3001 | Service uptime | **EMBED** - Status widget |
| **Chat** | Open WebUI | 3100 | LLM interface | **OPTIONAL** - Letta replaces most use |
| **Automation** | n8n | 5678 | Workflows | **EMBED** - Workflow status panel |
| **Home** | Home Assistant | 8123 | Smart home | **EMBED** - Device control widget |
| **Creative** | SillyTavern | 8000 | Character RP | **LINK** - Specialized use |
| **Creative** | ComfyUI | 8188 | Image gen | **EMBED** - Generation queue |
| **TTS** | Kokoro TTS | 8880 | Voice synthesis | **INTEGRATE** - Voice pipeline |

### Key Insights

1. **Control Plane UI is already 75% of the solution** - 23 components, comprehensive API integration
2. **Grafana excels at deep analysis** - Don't rebuild; embed
3. **Specialized tools have unique value** - ComfyUI, SillyTavern serve distinct workflows
4. **Fragmentation causes friction** - Users navigate 5+ UIs for daily operations
5. **The missing piece is unification**, not replacement

---

## Architecture Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HYDRA UNIFIED CONTROL PLANE                               │
│                         (Port 3200)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   CLUSTER   │ │     GPU     │ │  SERVICES   │ │    ALERTS   │           │
│  │   STATUS    │ │   METRICS   │ │    GRID     │ │    PANEL    │           │
│  │             │ │             │ │             │ │             │           │
│  │ • 3 nodes   │ │ • 4 GPUs    │ │ • 63 svcs   │ │ • Firing    │           │
│  │ • Health %  │ │ • VRAM bars │ │ • Status    │ │ • Silence   │           │
│  │ • Uptime    │ │ • Temp/Pwr  │ │ • Actions   │ │ • History   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    EMBEDDED SPECIALIST PANELS                         │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │   │
│  │  │  GRAFANA  │ │   n8n     │ │   HOME    │ │  COMFYUI  │           │   │
│  │  │  EMBED    │ │ WORKFLOWS │ │ASSISTANT  │ │   QUEUE   │           │   │
│  │  │           │ │           │ │           │ │           │           │   │
│  │  │ iframe    │ │ • Active  │ │ • Lights  │ │ • Jobs    │           │   │
│  │  │ dashboard │ │ • Pending │ │ • Climate │ │ • Preview │           │   │
│  │  │ selector  │ │ • Trigger │ │ • Scenes  │ │ • History │           │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      LETTA INTELLIGENT ASSISTANT                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐   │   │
│  │  │  > How's the cluster?                                          │   │   │
│  │  │  ◀ All 63 containers healthy. GPU temps normal. RTX 5090 at    │   │   │
│  │  │    87% VRAM with Qwen2.5-72B loaded. No active alerts.         │   │   │
│  │  │  > Dim the living room and switch to DeepSeek                  │   │   │
│  │  │  ◀ Done. Living room at 30%. Loading DeepSeek-R1-Distill-70B.  │   │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  │  [Listening...] 🎤 "Hey Hydra" wake word active                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Quick Actions: [Clear Cache] [Docker Prune] [Reload Config] [Switch Model] │
│  Links: [Grafana] [Portainer] [n8n Full] [SillyTavern] [ComfyUI Full]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. Hub-and-Spoke, Not Monolith

**Principle:** The Control Plane is a **command center**, not a replacement for specialized tools.

- **Hub (Control Plane):** Entry point, status overview, common actions, Letta assistant
- **Spokes (Embedded):** Grafana dashboards, n8n workflows, Home Assistant devices
- **Satellites (Linked):** SillyTavern, ComfyUI full UI, Portainer for emergencies

### 2. Progressive Disclosure

**Principle:** Show summary by default, reveal depth on demand.

- **Level 1 (Glance):** Node cards with health status
- **Level 2 (Inspect):** Click to expand GPU breakdown, container lists
- **Level 3 (Deep Dive):** Open embedded Grafana panel or full external UI

### 3. Voice-First Readiness

**Principle:** Every action should be invokable by voice via Letta.

- Cluster status queries
- Model switching
- Home automation control
- Alert acknowledgment
- Workflow triggering

### 4. Consistent Design Language

**Principle:** All embedded panels inherit the Hydra cyberpunk theme.

- Dark background (#0a0a0f)
- Cyan primary (#00ffff) with glow
- Magenta accents (#ff00ff)
- Monospace typography (JetBrains Mono)
- Neon borders and shadows

---

## Implementation Phases

### Phase A: Foundation Enhancement (Current + 1 Week)

**Goal:** Strengthen existing Control Plane UI

| Task | Component | Effort | Impact |
|------|-----------|--------|--------|
| A1 | Fix deprecated API calls (Ollama URL) | 1hr | HIGH |
| A2 | Add Grafana iframe embed component | 3hr | HIGH |
| A3 | Create dashboard selector dropdown | 2hr | MEDIUM |
| A4 | Add Uptime Kuma status widget | 2hr | MEDIUM |
| A5 | Implement keyboard shortcuts panel | 1hr | LOW |
| A6 | Add system-wide notification toasts | 2hr | MEDIUM |

**New Components:**
```tsx
// GrafanaEmbed.tsx
interface GrafanaEmbedProps {
  dashboard: 'cluster' | 'gpu' | 'inference' | 'services';
  timeRange?: string;
  variables?: Record<string, string>;
}

// UptimeKumaWidget.tsx
interface UptimeKumaWidgetProps {
  pageId: string;
  compact?: boolean;
}

// DashboardSelector.tsx
interface DashboardSelectorProps {
  dashboards: GrafanaDashboard[];
  onSelect: (dashboard: GrafanaDashboard) => void;
}
```

### Phase B: Workflow Integration (Week 2)

**Goal:** Surface n8n workflows in Control Plane

| Task | Component | Effort | Impact |
|------|-----------|--------|--------|
| B1 | Create n8n workflow status panel | 4hr | HIGH |
| B2 | Add manual workflow trigger buttons | 3hr | HIGH |
| B3 | Show recent execution history | 2hr | MEDIUM |
| B4 | Create execution log viewer | 3hr | MEDIUM |

**n8n API Integration:**
```typescript
// src/lib/n8n-api.ts
const N8N_URL = 'http://192.168.1.244:5678';

async function getWorkflows(): Promise<Workflow[]>;
async function getExecutions(workflowId: string): Promise<Execution[]>;
async function triggerWorkflow(workflowId: string): Promise<void>;
async function getWorkflowStatus(): Promise<WorkflowStatus[]>;
```

**New Components:**
```tsx
// WorkflowStatusPanel.tsx
// - Lists active workflows
// - Shows last execution time
// - Displays success/failure status
// - "Run Now" button for manual triggers

// ExecutionHistory.tsx
// - Recent executions across all workflows
// - Expandable to show execution details
// - Error highlighting
```

### Phase C: Home Automation Bridge (Week 3)

**Goal:** Bring Home Assistant controls into Control Plane

| Task | Component | Effort | Impact |
|------|-----------|--------|--------|
| C1 | Create Home Assistant API client | 3hr | HIGH |
| C2 | Build device control widget | 4hr | HIGH |
| C3 | Add scene activation buttons | 2hr | MEDIUM |
| C4 | Implement presence awareness | 3hr | MEDIUM |

**Home Assistant Integration:**
```typescript
// src/lib/homeassistant-api.ts
const HA_URL = 'http://192.168.1.244:8123';

async function getLights(): Promise<Light[]>;
async function setLightState(entityId: string, state: LightState): Promise<void>;
async function activateScene(sceneId: string): Promise<void>;
async function getPersonState(): Promise<PersonState[]>;
```

**New Components:**
```tsx
// HomeControlWidget.tsx
// - Quick light controls (Living Room, Office, Bedroom)
// - Scene buttons (Movie, Work, Sleep)
// - Climate at-a-glance
// - "Away Mode" toggle

// PresenceIndicator.tsx
// - Shows who's home
// - Last seen location
// - Device presence
```

### Phase D: Voice Interface MVP (Week 4)

**Goal:** Enable "Hey Hydra" voice control

| Task | Component | Effort | Impact |
|------|-----------|--------|--------|
| D1 | Integrate faster-whisper for STT | 4hr | CRITICAL |
| D2 | Create wake word detector | 6hr | CRITICAL |
| D3 | Build voice command router | 4hr | HIGH |
| D4 | Add Kokoro TTS for responses | 3hr | HIGH |
| D5 | Create voice status indicator | 2hr | MEDIUM |

**Voice Pipeline:**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Microphone  │ ──► │ Wake Word   │ ──► │  Whisper    │ ──► │   Letta     │
│   Input     │     │  Detector   │     │    STT      │     │  + Actions  │
└─────────────┘     │ "Hey Hydra" │     └─────────────┘     └─────────────┘
                    └─────────────┘                                │
                                                                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Speaker   │ ◄── │   Kokoro    │ ◄── │  Response   │ ◄── │   Action    │
│   Output    │     │    TTS      │     │ Generator   │     │  Executor   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**New Components:**
```tsx
// VoiceInterface.tsx
// - Microphone access button
// - Wake word status indicator
// - Listening animation
// - Transcript display
// - Response playback

// VoiceCommandRouter.tsx
// - Intent classification (status, control, query)
// - Action mapping
// - Letta passthrough for complex queries
```

### Phase E: Creative Pipeline Integration (Week 5-6)

**Goal:** Surface image generation in Control Plane

| Task | Component | Effort | Impact |
|------|-----------|--------|--------|
| E1 | Create ComfyUI queue status panel | 4hr | HIGH |
| E2 | Add image preview component | 3hr | MEDIUM |
| E3 | Build quick generation form | 4hr | MEDIUM |
| E4 | Show generation history | 3hr | LOW |

**ComfyUI Integration:**
```typescript
// src/lib/comfyui-api.ts
const COMFYUI_URL = 'http://192.168.1.203:8188';

async function getQueueStatus(): Promise<QueueStatus>;
async function getHistory(): Promise<Generation[]>;
async function submitWorkflow(workflow: ComfyWorkflow): Promise<string>;
async function getImage(filename: string): Promise<Blob>;
```

**New Components:**
```tsx
// ComfyUIQueuePanel.tsx
// - Current queue depth
// - Active generation progress
// - Recent completions with thumbnails
// - Link to full ComfyUI

// QuickGenerateForm.tsx
// - Character portrait preset
// - Background preset
// - Custom prompt input
// - Style selector
```

---

## Component Architecture

### New Directory Structure

```
ui/src/
├── app/
│   └── page.tsx                    # Main dashboard (existing)
├── components/
│   ├── core/                       # Existing components
│   │   ├── Header.tsx
│   │   ├── NodeCard.tsx
│   │   ├── ServiceList.tsx
│   │   └── ...
│   ├── embedded/                   # NEW: Embedded panels
│   │   ├── GrafanaEmbed.tsx
│   │   ├── UptimeKumaWidget.tsx
│   │   ├── WorkflowStatusPanel.tsx
│   │   ├── HomeControlWidget.tsx
│   │   └── ComfyUIQueuePanel.tsx
│   ├── voice/                      # NEW: Voice interface
│   │   ├── VoiceInterface.tsx
│   │   ├── WakeWordDetector.tsx
│   │   ├── TranscriptDisplay.tsx
│   │   └── VoiceStatusIndicator.tsx
│   └── layout/                     # NEW: Layout components
│       ├── DashboardGrid.tsx
│       ├── PanelContainer.tsx
│       └── TabNavigator.tsx
├── lib/
│   ├── api.ts                      # Existing (hydra-mcp)
│   ├── n8n-api.ts                  # NEW
│   ├── homeassistant-api.ts        # NEW
│   ├── comfyui-api.ts              # NEW
│   └── grafana-api.ts              # NEW
└── hooks/
    ├── useWebSocket.ts             # Existing
    ├── useVoiceInput.ts            # NEW
    ├── useWakeWord.ts              # NEW
    └── useTTS.ts                   # NEW
```

### API Gateway Pattern

All external service calls should flow through the MCP server to:
1. Centralize authentication
2. Enable caching
3. Provide consistent error handling
4. Allow rate limiting

```
Control Plane UI
       │
       ▼
  MCP Server (8600)
       │
       ├─► Grafana API
       ├─► n8n API
       ├─► Home Assistant API
       ├─► ComfyUI API
       ├─► Letta API
       └─► Prometheus API
```

**MCP Server Extensions Needed:**
```python
# mcp-servers/hydra-cluster/server.py additions

@app.get("/n8n/workflows")
async def get_n8n_workflows():
    """Proxy n8n workflow list"""

@app.post("/n8n/execute/{workflow_id}")
async def execute_n8n_workflow(workflow_id: str):
    """Trigger n8n workflow"""

@app.get("/homeassistant/states")
async def get_ha_states():
    """Get Home Assistant entity states"""

@app.post("/homeassistant/services/{domain}/{service}")
async def call_ha_service(domain: str, service: str, data: dict):
    """Call Home Assistant service"""

@app.get("/comfyui/queue")
async def get_comfyui_queue():
    """Get ComfyUI queue status"""

@app.post("/comfyui/prompt")
async def submit_comfyui_prompt(workflow: dict):
    """Submit ComfyUI workflow"""
```

---

## Grafana Embedding Strategy

### Approach: iframe with Dashboard Selectors

Grafana supports anonymous access with `allow_embedding=true`. This enables:
1. Dashboard iframe embedding
2. Panel-level embedding (specific visualizations)
3. Variable passing via URL parameters

### Configuration

**grafana.ini additions:**
```ini
[auth.anonymous]
enabled = true
org_name = Main Org.
org_role = Viewer

[security]
allow_embedding = true

[server]
root_url = http://192.168.1.244:3003
```

### Embed Component

```tsx
// components/embedded/GrafanaEmbed.tsx
import { useState } from 'react';

interface GrafanaEmbedProps {
  dashboard: string;
  panelId?: number;
  timeRange?: string;
  variables?: Record<string, string>;
  height?: number;
}

const GRAFANA_URL = 'http://192.168.1.244:3003';

export function GrafanaEmbed({
  dashboard,
  panelId,
  timeRange = '1h',
  variables = {},
  height = 400
}: GrafanaEmbedProps) {
  const params = new URLSearchParams({
    orgId: '1',
    from: `now-${timeRange}`,
    to: 'now',
    theme: 'dark',
    ...variables
  });

  const panelPath = panelId
    ? `/d-solo/${dashboard}?panelId=${panelId}`
    : `/d/${dashboard}`;

  const src = `${GRAFANA_URL}${panelPath}?${params}`;

  return (
    <div className="grafana-embed rounded-lg overflow-hidden border border-cyan-500/30">
      <iframe
        src={src}
        width="100%"
        height={height}
        frameBorder="0"
        className="bg-dark"
      />
    </div>
  );
}
```

### Dashboard Mappings

```typescript
const GRAFANA_DASHBOARDS = {
  cluster: 'cluster-overview',
  gpu: 'gpu-utilization-deep-dive',
  inference: 'inference-metrics',
  services: 'services-health'
};

const GRAFANA_PANELS = {
  gpuTemp: { dashboard: 'gpu', panelId: 2 },
  gpuPower: { dashboard: 'gpu', panelId: 4 },
  vramUsage: { dashboard: 'gpu', panelId: 6 },
  inferenceLatency: { dashboard: 'inference', panelId: 3 }
};
```

---

## Home Assistant Integration Design

### Device Categories

| Category | Entities | Control Type |
|----------|----------|--------------|
| **Lighting** | light.living_room, light.office, light.bedroom | On/Off/Dim |
| **Climate** | climate.thermostat | Temp set |
| **Media** | media_player.living_room, media_player.sonos | TTS/Play |
| **Presence** | person.shaun, device_tracker.* | Read-only |
| **Scenes** | scene.movie, scene.work, scene.sleep | Activate |

### Widget Design

```tsx
// components/embedded/HomeControlWidget.tsx
export function HomeControlWidget() {
  return (
    <div className="home-control grid grid-cols-2 gap-4 p-4">
      {/* Quick Lights */}
      <div className="lights">
        <h3 className="text-cyan-400 mb-2">Lights</h3>
        <LightToggle entity="light.living_room" name="Living Room" />
        <LightToggle entity="light.office" name="Office" />
        <LightToggle entity="light.bedroom" name="Bedroom" />
      </div>

      {/* Scene Buttons */}
      <div className="scenes">
        <h3 className="text-cyan-400 mb-2">Scenes</h3>
        <SceneButton scene="movie" icon="🎬" />
        <SceneButton scene="work" icon="💼" />
        <SceneButton scene="sleep" icon="🌙" />
      </div>

      {/* Climate At-a-Glance */}
      <div className="climate col-span-2">
        <ClimateDisplay entity="climate.thermostat" />
      </div>
    </div>
  );
}
```

---

## Voice Interface Architecture

### Wake Word Detection

Using a lightweight browser-based wake word detector:

```typescript
// hooks/useWakeWord.ts
import { useState, useEffect, useCallback } from 'react';

export function useWakeWord(wakePhrase: string = 'hey hydra') {
  const [isListening, setIsListening] = useState(false);
  const [isWoken, setIsWoken] = useState(false);

  // Use Web Speech API for continuous listening
  const recognition = new webkitSpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map(r => r[0].transcript)
      .join('')
      .toLowerCase();

    if (transcript.includes(wakePhrase)) {
      setIsWoken(true);
      // Start full transcription mode
    }
  };

  return { isListening, isWoken, startListening, stopListening };
}
```

### Full Voice Pipeline

```typescript
// Voice command flow
async function processVoiceCommand(audioBlob: Blob): Promise<string> {
  // 1. Send to Whisper for transcription
  const transcript = await whisperTranscribe(audioBlob);

  // 2. Classify intent via RouteLLM
  const intent = await classifyIntent(transcript);

  // 3. Route to appropriate handler
  switch (intent.type) {
    case 'cluster_status':
      return await getClusterStatus();
    case 'light_control':
      return await controlLight(intent.params);
    case 'model_switch':
      return await switchModel(intent.params);
    case 'general_query':
      return await queryLetta(transcript);
  }
}
```

---

## Navigation & Layout

### Tab-Based Navigation

```tsx
// Main page layout with tabs
export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="dashboard">
      <Header />

      <nav className="tabs flex gap-2 px-4 py-2 border-b border-cyan-500/30">
        <Tab id="overview" active={activeTab} onClick={setActiveTab}>
          Overview
        </Tab>
        <Tab id="gpu" active={activeTab} onClick={setActiveTab}>
          GPU Metrics
        </Tab>
        <Tab id="workflows" active={activeTab} onClick={setActiveTab}>
          Workflows
        </Tab>
        <Tab id="home" active={activeTab} onClick={setActiveTab}>
          Home
        </Tab>
        <Tab id="creative" active={activeTab} onClick={setActiveTab}>
          Creative
        </Tab>
      </nav>

      <main className="content p-4">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'gpu' && <GPUTab />}
        {activeTab === 'workflows' && <WorkflowsTab />}
        {activeTab === 'home' && <HomeTab />}
        {activeTab === 'creative' && <CreativeTab />}
      </main>

      {/* Persistent Letta chat */}
      <LettaChat />

      {/* Voice interface */}
      <VoiceInterface />
    </div>
  );
}
```

### Mobile Considerations

- Collapsible panels by default
- Bottom navigation bar on mobile
- Pull-to-refresh for status update
- Voice-first interaction on mobile

---

## What NOT to Merge

### Keep as Separate UIs

| UI | Reason |
|----|--------|
| **Grafana Full** | Complex query editing, dashboard creation |
| **Portainer** | Low-level Docker debugging |
| **n8n Full** | Visual workflow builder |
| **SillyTavern** | Specialized creative workflow |
| **ComfyUI Full** | Node-based image workflow |
| **Home Assistant Full** | Device configuration, automation rules |

These remain accessible via direct links in the Control Plane footer.

### Keep as Backup

| UI | Reason |
|----|--------|
| **Homepage** | Lightweight fallback when Control Plane is down |
| **Open WebUI** | Alternative chat if Letta unavailable |

---

## Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| **UIs visited per session** | 4-5 | 1-2 | User behavior analytics |
| **Time to cluster status** | 15s (load Grafana) | 0s (instant) | First contentful paint |
| **Actions without context switch** | 30% | 80% | Action logging |
| **Voice commands per day** | 0 | 20+ | Voice pipeline telemetry |
| **Mobile usability** | Poor | Good | User feedback |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Grafana iframe fails** | Fallback to direct link + embedded metrics summary |
| **Voice recognition inaccurate** | Text input always available, confirm destructive actions |
| **MCP server overload** | Response caching, request debouncing |
| **Embedded panels slow** | Lazy loading, skeleton placeholders |
| **Theme inconsistency** | CSS custom properties, Grafana theme override |

---

## Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | A: Foundation | Grafana embed, Uptime Kuma widget, API fixes |
| 2 | B: Workflows | n8n panel, workflow triggers, execution history |
| 3 | C: Home | HA device control, scenes, presence |
| 4 | D: Voice | Wake word, STT/TTS pipeline, command routing |
| 5-6 | E: Creative | ComfyUI queue, image preview, quick generate |
| 7+ | Polish | Performance optimization, mobile refinement |

---

## Conclusion

The Hydra Unified Control Plane will:

1. **Reduce friction** - Single entry point for 80% of daily operations
2. **Preserve specialist tools** - Don't rebuild what works
3. **Enable voice control** - "Hey Hydra" as primary interface
4. **Maintain flexibility** - Easy access to full UIs when needed
5. **Look cohesive** - Consistent cyberpunk design language

This is evolution, not revolution. Build on the excellent Control Plane UI foundation, embed the best of Grafana, n8n, and Home Assistant, and create the voice interface that ties it all together.

---

*Architecture Document v1.0*
*December 13, 2025*
*Hydra Autonomous Steward*
