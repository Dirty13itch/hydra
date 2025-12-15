# Hydra Transparency and Control Framework

## Philosophy: The Trusted Steward Model

The Hydra Autonomous Steward operates with a clear principle: **"Act autonomously, but always accountably."**

This means:
1. **Every action is logged** - Nothing happens in the dark
2. **Every decision is explainable** - The "why" is always available
3. **Every process is interruptible** - Humans can always intervene
4. **Every change is reversible** - Actions can be undone when possible

The steward is like a trusted employee who:
- Reports what they're doing before and after
- Asks permission for significant changes
- Maintains a clear paper trail
- Makes it easy to course-correct

---

## Current State Assessment

### What's Autonomous Today

| System | Autonomous Actions | Visibility | User Control |
|--------|-------------------|------------|--------------|
| **n8n Workflows** | 7 workflows run on schedule/webhook | Only in n8n UI | Can disable in n8n UI |
| **Alertmanager** | Routes alerts, triggers webhooks | Config file only | No live control |
| **Self-Healing** | Restarts unhealthy containers | Audit log (partial) | Rate-limited only |
| **Letta Memory** | Updates agent knowledge | No visibility | No control |
| **RouteLLM** | Selects models for requests | No visibility | No override |
| **Disk Cleanup** | Deletes old files (when active) | No visibility | No control |

### Critical Gaps

1. **No Unified Activity Feed** - Actions scattered across services
2. **No Pending Actions Queue** - Can't see what's about to happen
3. **No Kill Switch** - Can't disable all automation at once
4. **No Decision Explanations** - Don't know why actions were taken
5. **No Approval Workflows** - Critical actions don't require approval

---

## Transparency Architecture

### Layer 1: Unified Activity Log

All autonomous actions flow to a single persistent log.

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED ACTIVITY LOG                          │
│                   (PostgreSQL: hydra_activity)                   │
├─────────────────────────────────────────────────────────────────┤
│  id | timestamp | source | action | target | params | result    │
│  ---|-----------|--------|--------|--------|--------|--------   │
│  1  | 08:00:01  | n8n    | health_check | cluster | {} | ok     │
│  2  | 08:00:15  | alert  | fire | ContainerDown | {name:x} | -  │
│  3  | 08:00:16  | n8n    | restart | hydra-x | {alert:2} | ok   │
│  4  | 08:05:00  | letta  | memory_update | steward | {k:v} | ok │
│  5  | 09:00:00  | route  | model_select | inference | {m:7b} | - │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Activity Feed  │
                    │   (Real-time)   │
                    │  Control Plane  │
                    └─────────────────┘
```

**Schema:**
```sql
CREATE TABLE hydra_activity (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    source VARCHAR(50) NOT NULL,        -- n8n, alert, route, letta, mcp, user
    source_id VARCHAR(100),             -- workflow id, alert fingerprint, etc.
    action VARCHAR(100) NOT NULL,       -- health_check, restart, memory_update, etc.
    action_type VARCHAR(20) NOT NULL,   -- autonomous, triggered, manual, scheduled
    target VARCHAR(200),                -- container name, model name, etc.
    params JSONB,                       -- action parameters
    result VARCHAR(20),                 -- ok, error, pending, approved, rejected
    result_details JSONB,               -- response, error message, etc.
    decision_reason TEXT,               -- WHY this action was taken
    parent_id INTEGER REFERENCES hydra_activity(id),  -- chain of causation
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(100),
    approved_at TIMESTAMPTZ
);

CREATE INDEX idx_activity_timestamp ON hydra_activity(timestamp DESC);
CREATE INDEX idx_activity_source ON hydra_activity(source);
CREATE INDEX idx_activity_action_type ON hydra_activity(action_type);
CREATE INDEX idx_activity_pending ON hydra_activity(result) WHERE result = 'pending';
```

### Layer 2: Decision Transparency

Every autonomous decision includes its reasoning.

**Self-Healing Example:**
```json
{
  "action": "container_restart",
  "target": "hydra-litellm",
  "decision_reason": "Container reported unhealthy for 3+ minutes. Health check failed: HTTP 503 on /health. Previous successful restart 2 days ago resolved similar issue.",
  "alternatives_considered": [
    {"action": "wait", "rejected_because": "Already waited 3 minutes"},
    {"action": "alert_only", "rejected_because": "Auto-remediation enabled for this container"}
  ],
  "confidence": 0.85,
  "reversible": true,
  "undo_action": "Container will auto-start, no undo needed"
}
```

**RouteLLM Example:**
```json
{
  "action": "model_route",
  "target": "qwen2.5-7b",
  "decision_reason": "Prompt classified as 'simple question' (complexity: 0.23). Token estimate: 45. No code patterns detected.",
  "alternatives_considered": [
    {"model": "midnight-miqu-70b", "rejected_because": "Complexity below threshold (0.6)"},
    {"model": "qwen2.5-coder-7b", "rejected_because": "No code patterns detected"}
  ],
  "user_can_override": true,
  "override_instruction": "Add 'use 70b' or 'prefer_quality=true' to force quality tier"
}
```

### Layer 3: User Control Points

**Control Hierarchy:**

```
┌──────────────────────────────────────────────────────────────────┐
│                     MASTER CONTROL PANEL                          │
├──────────────────────────────────────────────────────────────────┤
│  🔴 EMERGENCY STOP                                                │
│  [Disable All Automation]  [Pause Workflows]  [Safe Mode]        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  AUTOMATION STATUS                              QUICK TOGGLES     │
│  ┌────────────────────────────────┐            ┌──────────────┐  │
│  │ Self-Healing      ✅ ACTIVE    │            │ ☑ Container  │  │
│  │ Memory Updates    ✅ ACTIVE    │            │   Restarts   │  │
│  │ Health Digests    ✅ ACTIVE    │            │ ☑ Memory     │  │
│  │ Research Agent    ⏸️ PAUSED    │            │   Updates    │  │
│  │ Disk Cleanup      ⬚ DISABLED  │            │ ☑ Health     │  │
│  └────────────────────────────────┘            │   Reports    │  │
│                                                │ ☐ Research   │  │
│  PENDING APPROVALS (2)                         │   Agent      │  │
│  ┌────────────────────────────────┐            │ ☐ Disk       │  │
│  │ ⚠️ Restart hydra-postgres      │            │   Cleanup    │  │
│  │   [Approve] [Reject] [Details] │            └──────────────┘  │
│  │                                │                              │
│  │ ⚠️ Update Letta memory block   │                              │
│  │   [Approve] [Reject] [Details] │                              │
│  └────────────────────────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

**Control Modes:**

| Mode | Description | Automation Level |
|------|-------------|------------------|
| **Full Auto** | All workflows active, self-healing enabled | Everything runs |
| **Supervised** | Actions require approval for protected resources | Approval queue |
| **Notify Only** | Actions logged and notified, but not executed | Passive monitoring |
| **Safe Mode** | All automation disabled, manual control only | Emergency stop |

### Layer 4: Real-Time Activity Feed

**What You See:**

```
┌──────────────────────────────────────────────────────────────────┐
│  ACTIVITY FEED                                    [Filter ▾] 🔄  │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🟢 08:15:32  HEALTH CHECK                                       │
│     Hydra Daily Health Digest completed                          │
│     Result: 98% cluster health, all services nominal             │
│     [View Report]                                                │
│                                                                   │
│  🟡 08:14:15  MODEL ROUTE                                        │
│     Routed "explain quantum computing" → midnight-miqu-70b       │
│     Reason: High complexity (0.72), analysis task detected       │
│     [Why This Model?]                                            │
│                                                                   │
│  🟢 08:10:00  MEMORY UPDATE                                      │
│     Letta steward memory updated                                 │
│     Added: cluster_state block (147 bytes)                       │
│     [View Changes]                                               │
│                                                                   │
│  🔵 08:05:22  CONTAINER RESTART                                  │
│     hydra-kokoro-tts restarted (auto-healing)                    │
│     Trigger: Health check timeout (30s)                          │
│     Result: Container healthy after 12s                          │
│     [View Logs] [Undo Not Available]                             │
│                                                                   │
│  🔴 08:00:15  ALERT FIRED                                        │
│     ContainerUnhealthy: hydra-kokoro-tts                         │
│     Severity: warning                                            │
│     Auto-action: Restart scheduled                               │
│     [View Alert] [Suppress] [Escalate]                           │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Activity Database (Foundation)

**Create unified activity logging:**

1. Add `hydra_activity` table to PostgreSQL
2. Create Activity API endpoints on MCP:
   - `POST /activity` - Log new activity
   - `GET /activity` - Query activities
   - `GET /activity/stream` - SSE real-time feed
   - `GET /activity/{id}` - Single activity with full context

3. Instrument all autonomous sources:
   - n8n: Add HTTP node to log execution start/end
   - Alertmanager: Webhook logs to activity API
   - RouteLLM: Log every routing decision
   - Letta: Log memory updates
   - MCP: Already logs to audit, migrate to activity

### Phase 2: Control Panel (User Agency)

**Build master control interface:**

1. Automation Status Panel
   - Show all n8n workflows with status
   - Enable/disable toggles (calls n8n API)
   - Last execution time and result

2. Approval Queue
   - List pending actions requiring approval
   - Approve/Reject buttons
   - Auto-expire after configurable timeout

3. Quick Toggles
   - Category-level controls (all self-healing, all memory, etc.)
   - Master kill switch for all automation

4. Safe Mode
   - One-click disable all autonomous behavior
   - Visual indicator when in safe mode
   - Auto-timeout option (safe mode for 1 hour, then restore)

### Phase 3: Decision Transparency (Understanding)

**Make every decision explainable:**

1. Decision Chain Visualization
   - Click any activity to see what triggered it
   - Follow the chain: Alert → Workflow → Action → Result

2. "Why This?" Feature
   - Every autonomous action has "Why?" button
   - Shows decision tree, thresholds, alternatives considered

3. Model Routing Transparency
   - Show RouteLLM decisions in activity feed
   - Allow override for future similar requests
   - Learn from user corrections

### Phase 4: Intervention Tools (Control)

**Enable user intervention:**

1. Action Preview
   - Before autonomous action executes, show preview
   - Configurable delay (5s, 30s, 5min) for intervention window

2. Undo/Rollback
   - Where possible, offer undo for recent actions
   - Show which actions are reversible

3. Override Memory
   - User can correct Letta memory entries
   - Mark entries as "user-verified" vs "auto-captured"

4. Alert Management
   - Acknowledge alerts (stops re-triggering)
   - Suppress alerts (time-based or permanent)
   - Escalate alerts (to phone, other channels)

---

## UI Components Specification

### 1. ActivityFeed Component

```tsx
interface Activity {
  id: number;
  timestamp: string;
  source: 'n8n' | 'alert' | 'route' | 'letta' | 'mcp' | 'user';
  sourceId?: string;
  action: string;
  actionType: 'autonomous' | 'triggered' | 'manual' | 'scheduled';
  target?: string;
  params?: Record<string, any>;
  result: 'ok' | 'error' | 'pending' | 'approved' | 'rejected';
  resultDetails?: Record<string, any>;
  decisionReason?: string;
  parentId?: number;
  requiresApproval: boolean;
}

interface ActivityFeedProps {
  limit?: number;
  filter?: {
    sources?: string[];
    actionTypes?: string[];
    results?: string[];
    since?: string;
  };
  onActivityClick?: (activity: Activity) => void;
  showApprovalButtons?: boolean;
}
```

### 2. AutomationControlPanel Component

```tsx
interface Workflow {
  id: string;
  name: string;
  active: boolean;
  lastExecution?: {
    timestamp: string;
    status: 'success' | 'error' | 'running';
    duration: number;
  };
  schedule?: string;  // cron expression
  category: 'health' | 'memory' | 'research' | 'creative' | 'maintenance';
}

interface AutomationControlPanelProps {
  workflows: Workflow[];
  systemMode: 'full_auto' | 'supervised' | 'notify_only' | 'safe_mode';
  onModeChange: (mode: string) => void;
  onWorkflowToggle: (workflowId: string, active: boolean) => void;
  pendingApprovals: PendingApproval[];
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
}
```

### 3. DecisionExplainer Component

```tsx
interface Decision {
  action: string;
  target: string;
  reason: string;
  confidence: number;
  alternatives: Array<{
    action: string;
    rejectedBecause: string;
  }>;
  reversible: boolean;
  undoAction?: string;
  triggerChain: Activity[];  // What led to this decision
}

interface DecisionExplainerProps {
  activityId: number;
  onOverride?: (newDecision: string) => void;
  onUndo?: () => void;
}
```

### 4. ApprovalQueue Component

```tsx
interface PendingApproval {
  id: string;
  activityId: number;
  action: string;
  target: string;
  reason: string;
  requestedAt: string;
  expiresAt: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  context: Record<string, any>;
}

interface ApprovalQueueProps {
  approvals: PendingApproval[];
  onApprove: (id: string, comment?: string) => void;
  onReject: (id: string, reason: string) => void;
  onViewDetails: (id: string) => void;
}
```

---

## API Endpoints

### Activity API

```
# Log new activity
POST /api/activity
{
  "source": "n8n",
  "sourceId": "workflow-123",
  "action": "container_restart",
  "actionType": "autonomous",
  "target": "hydra-litellm",
  "params": {"reason": "unhealthy"},
  "decisionReason": "Container unhealthy for 3+ minutes",
  "requiresApproval": false
}

# Query activities
GET /api/activity?source=n8n&since=2025-12-14T00:00:00Z&limit=100

# Real-time stream (SSE)
GET /api/activity/stream

# Get single activity with context
GET /api/activity/{id}?include_chain=true

# Get pending approvals
GET /api/activity/pending

# Approve/reject pending activity
POST /api/activity/{id}/approve
POST /api/activity/{id}/reject
```

### Control API

```
# Get system mode
GET /api/control/mode
# Response: {"mode": "full_auto", "since": "2025-12-14T08:00:00Z"}

# Set system mode
POST /api/control/mode
{"mode": "safe_mode", "duration": 3600}  # Safe mode for 1 hour

# Get workflow status
GET /api/control/workflows
# Response: [{"id": "...", "name": "...", "active": true, ...}]

# Toggle workflow
POST /api/control/workflows/{id}/toggle
{"active": false}

# Emergency stop
POST /api/control/emergency-stop
# Disables all automation, sends notifications
```

---

## Trust Indicators

### Visual Cues in UI

| Indicator | Meaning |
|-----------|---------|
| 🟢 Green pulse | System healthy, automation active |
| 🟡 Yellow pulse | Action pending approval |
| 🔴 Red pulse | Error occurred, attention needed |
| ⏸️ Pause icon | Automation paused/safe mode |
| 🔒 Lock icon | Protected resource, requires approval |
| 👁️ Eye icon | User is watching (manual oversight) |
| 🤖 Robot icon | Autonomous action |
| 👤 Person icon | User-initiated action |

### Notification Levels

| Level | When | How |
|-------|------|-----|
| **Silent** | Routine operations | Activity feed only |
| **Inform** | Notable events | Toast notification |
| **Alert** | Issues detected | Sound + persistent banner |
| **Interrupt** | Approval needed | Modal dialog |
| **Emergency** | Critical failure | Full-screen + external notification |

---

## Configuration

### System Defaults (config/transparency.yaml)

```yaml
transparency:
  # Activity logging
  activity_retention_days: 90
  activity_log_level: detailed  # minimal, standard, detailed, verbose

  # Approval requirements
  approval_required:
    - container_restart:protected
    - memory_update:persona
    - model_switch:70b
    - disk_cleanup:aggressive

  approval_timeout_minutes: 30

  # Intervention windows
  autonomous_action_delay_seconds: 5  # Time to cancel before action
  show_preview_for:
    - container_restart
    - memory_update
    - disk_cleanup

  # Notification preferences
  notifications:
    activity_feed: always
    toast: notable_events
    sound: alerts_only
    external: critical_only

  # Safe mode
  safe_mode:
    auto_restore_after_hours: 24
    protected_during_safe_mode:
      - all_workflows
      - container_actions
      - memory_updates

# Override decisions
routing_overrides:
  # Always use 70b for these patterns
  force_quality:
    - "analyze*"
    - "explain in detail*"
    - "write a comprehensive*"

  # Always use code model for these
  force_code:
    - "*python*"
    - "*javascript*"
    - "*fix this code*"
```

---

## Implementation Priority

### Week 1: Foundation
1. Create `hydra_activity` table
2. Add Activity API to MCP
3. Instrument n8n workflows to log start/end
4. Create basic ActivityFeed component

### Week 2: Control
1. Build AutomationControlPanel
2. Add workflow toggle API (via n8n)
3. Implement system mode switching
4. Add safe mode with timeout

### Week 3: Transparency
1. Add decision logging to RouteLLM
2. Create DecisionExplainer component
3. Build activity chain visualization
4. Add "Why?" buttons throughout UI

### Week 4: Polish
1. Real-time activity stream (SSE)
2. Approval queue with notifications
3. Override/correction interface
4. Mobile-responsive controls

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Time to understand** | <30 seconds | User can explain last autonomous action |
| **Intervention rate** | <5% | Most actions don't need intervention |
| **False positive rate** | <1% | Approvals that shouldn't have been needed |
| **User confidence** | >90% | Survey: "I trust the system to act correctly" |
| **Recovery time** | <2 minutes | Time from error to user-initiated fix |

---

## The Trust Contract

**What Hydra Promises:**

1. **I will tell you what I'm doing** - Every autonomous action appears in the activity feed within 1 second

2. **I will explain my decisions** - Every action has a "Why?" that shows my reasoning

3. **I will ask before major changes** - Protected resources require your approval

4. **I will let you stop me** - Safe mode is always one click away

5. **I will remember your preferences** - If you override me, I learn from it

6. **I will not hide mistakes** - Errors are prominently displayed, not buried

**What I Ask of You:**

1. **Review the activity feed occasionally** - Trust but verify

2. **Respond to approval requests** - Don't let them timeout silently

3. **Tell me when I'm wrong** - Override and correct my decisions

4. **Adjust thresholds as needed** - Fine-tune the automation boundaries

---

*Transparency Framework v1.0*
*December 14, 2025*
*Hydra Autonomous Steward*
