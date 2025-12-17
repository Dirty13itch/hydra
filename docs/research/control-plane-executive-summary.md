# Hydra Control Plane: Executive Summary
## Research Findings & Architectural Recommendations

**Date:** 2025-12-16
**Status:** Research Complete
**Full Report:** `control-plane-dashboard-architecture-2025.md`

---

## TL;DR: Top 5 Decisions

1. **Use SSE (not WebSockets)** for real-time dashboard updates - it's the 2025 standard
2. **Backend-for-Frontend (BFF) API Gateway** - separate optimized APIs for web, CLI, mobile
3. **Drag-and-Drop UI with Database Storage** - avoid YAML configuration hell
4. **Embed Grafana Panels** - unified observability in one dashboard (Ray pattern)
5. **Next.js 15 + FastAPI + PostgreSQL + Redis** - modern, proven, fast

---

## Critical Insights from Research

### What Makes Great Dashboards in 2025

**Performance:**
- Sub-1-second load times (static generation where possible)
- <100ms real-time update latency
- Lightweight visualizations (avoid heavy heatmaps)

**UX Patterns:**
- **5-Second Rule**: User understands critical status in 5 seconds
- **Drag-and-drop** beats YAML for 90% of users
- **Dynamic RBAC UI**: Show only relevant controls per role
- **Dark mode** is essential (not optional) for 24/7 monitoring

**Architecture:**
- **SSE dominates 2025** for unidirectional real-time (dashboards, feeds, AI streaming)
- **WebSockets** still best for bidirectional (chat, collaboration)
- **Event-driven** with message queues for scalability
- **Auto-discovery** minimizes manual configuration

---

## Benchmark Learnings

### Infrastructure Management

| Platform | Best Feature | Apply to Hydra |
|----------|-------------|----------------|
| **Portainer** | GitOps built-in, secure agent-based connections | GitOps mode for advanced users, no SSH keys needed |
| **Rancher** | Steve API with Kubernetes watch → WebSocket | Similar pattern for Docker/NixOS state streaming |
| **Proxmox** | Hub-and-spoke WebSocket, 2-second polling | Lightweight agents per node with gRPC |
| **Unraid** | Nchan pub/sub for real-time without polling | Redis pub/sub for events |
| **Cockpit** | Zero memory when idle (systemd socket activation) | On-demand activation for resource efficiency |

### AI/ML Platforms

| Platform | Best Feature | Apply to Hydra |
|----------|-------------|----------------|
| **MLflow** | Full metric history visualization | Track inference metrics over time (latency, throughput) |
| **Langfuse** | Customizable dashboards, open-source (MIT) | Build custom views for different users/teams |
| **LangSmith** | Pre-built dashboards + native alerting | Auto-generated dashboards for each service |
| **Ray** | Embedded Grafana = single pane of glass | Embed Grafana panels directly in Hydra dashboard |

### Home Lab Dashboards

| Platform | Best Feature | Apply to Hydra |
|----------|-------------|----------------|
| **Homepage** | Static generation + secure API proxying | Fast initial load, hide API keys |
| **Homarr** | Drag-and-drop UI, 30+ integrations | Primary config method (not YAML) |
| **Dashy** | 50+ widgets, deep customization | Widget library for extensibility |

---

## Recommended Technology Stack

### Backend

```
┌─────────────────────────────────────────────────────────────┐
│                     Edge Layer                               │
│  Traefik (reverse proxy, TLS termination, routing)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  API Gateway (BFF Layer)                     │
│  FastAPI (Python, async, OpenAPI docs)                      │
│  - Web BFF (optimized for browser)                          │
│  - CLI BFF (efficient JSON for terminal)                    │
│  - Automation BFF (webhooks for n8n)                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  - Inference Service (TabbyAPI integration)                 │
│  - Container Service (Docker API wrapper)                   │
│  - NixOS Service (systemd management via agents)            │
│  - Metrics Service (Prometheus queries)                     │
│  - Alert Service (threshold evaluation)                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  PostgreSQL: config, users, alerts, audit logs              │
│  Redis: cache, session state, pub/sub                       │
│  Prometheus: metrics storage                                │
│  Loki: log aggregation                                      │
└─────────────────────────────────────────────────────────────┘
```

### Frontend

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js 15 Dashboard                      │
│  - Static generation for fast load                          │
│  - SSE integration for real-time updates                    │
│  - shadcn/ui components (Tailwind, accessible)              │
│  - TanStack Query (server state, caching)                   │
│  - Zustand (client state)                                   │
│  - Recharts (lightweight charts)                            │
│  - Embedded Grafana panels (iframe)                         │
└─────────────────────────────────────────────────────────────┘
                            ↑
                    SSE Stream (eventsource-parser)
                            ↑
┌─────────────────────────────────────────────────────────────┐
│                    Event Stream Endpoint                     │
│  FastAPI SSE endpoint                                        │
│  Redis Pub/Sub → SSE stream                                 │
└─────────────────────────────────────────────────────────────┘
```

### Node Agents

```
┌─────────────────────────────────────────────────────────────┐
│            hydra-ai / hydra-compute Agents                   │
│  Language: Rust or Go (lightweight, efficient)               │
│  Protocol: gRPC (typed, efficient)                           │
│  Deployment: NixOS systemd service                           │
│  Responsibilities:                                           │
│  - Collect metrics (CPU, GPU, memory, disk)                  │
│  - Report service status                                     │
│  - Execute commands (restart, load model)                    │
│  - Stream logs to Loki                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Architecture Decisions

### 1. SSE for Real-Time (Not WebSockets)

**Why:**
- 2025 trend: SSE is having a "glorious comeback"
- Perfect for dashboards (unidirectional: cluster → UI)
- Lower overhead than WebSockets
- HTTP-compatible (no firewall issues)
- Built-in browser reconnection
- Proven: 10,000+ clients at <20ms latency

**Implementation:**
```python
# FastAPI SSE endpoint
@app.get("/api/events/cluster")
async def cluster_events(request: Request):
    async def event_generator():
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe("cluster:events")
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                yield {
                    "event": "cluster_update",
                    "data": json.dumps(message["data"])
                }
    return EventSourceResponse(event_generator())
```

### 2. BFF API Gateway Pattern

**Structure:**
- **Web BFF**: Returns HTML-optimized payloads
- **CLI BFF**: Efficient JSON, table-friendly formats
- **Automation BFF**: Webhook-friendly, idempotent

**Why:**
- Each client gets exactly what it needs
- No over-fetching or under-fetching
- Independent evolution of APIs
- Better performance

### 3. Drag-and-Drop UI (Database-Backed)

**Model:**
```typescript
// User dashboard configuration stored in PostgreSQL
interface DashboardConfig {
  user_id: string;
  layout: LayoutItem[];  // Grid positions
  widgets: Widget[];     // Enabled widgets
  theme: Theme;
  preferences: UserPreferences;
}

// Auto-discovered services (Docker labels)
interface Service {
  id: string;
  name: string;
  category: string;
  url: string;
  health_endpoint: string;
  icon: string;
  auto_discovered: boolean;
  source: "docker" | "nixos" | "manual";
}
```

**Why:**
- Homarr proves drag-and-drop wins for UX
- Database storage enables per-user customization
- Optional YAML export for power users
- Git sync for version control (advanced feature)

### 4. RBAC with Dynamic UI

**Implementation:**
```typescript
// Central policy engine (OSO or similar)
role Admin {
  permissions = ["*"];
}

role Operator {
  permissions = [
    "service:read", "service:restart",
    "metrics:read", "logs:read"
  ];
}

role Viewer {
  permissions = ["service:read", "metrics:read"];
}

// React component checks permissions
function ServiceCard({ service }) {
  const { can } = usePermissions();

  return (
    <Card>
      <ServiceStatus service={service} />
      {can("service:restart") && (
        <Button onClick={() => restartService(service)}>
          Restart
        </Button>
      )}
    </Card>
  );
}
```

**Why:**
- Portainer and Homarr prove this works at scale
- Dynamic UI reduces clutter
- Central policy engine ensures consistency
- Audit logging built-in

---

## Implementation Phases

### Phase 1: MVP (2 weeks)

**Goal:** Basic dashboard with real-time cluster status

- [ ] FastAPI backend with basic routing
- [ ] PostgreSQL schema (users, services, config)
- [ ] Redis pub/sub for events
- [ ] SSE endpoint for real-time updates
- [ ] Next.js dashboard with cluster overview
- [ ] Docker service discovery (label-based)
- [ ] Simple auth (username/password)

**Deliverable:** Dashboard showing all services with health status, updated in real-time

---

### Phase 2: Core Features (3 weeks)

**Goal:** Full service management and monitoring

- [ ] Inference monitoring (TabbyAPI integration)
- [ ] Resource charts (CPU, GPU, memory per node)
- [ ] Quick actions (restart service, view logs)
- [ ] Log streaming in UI
- [ ] Basic alerting (threshold-based)
- [ ] Embedded Grafana panels
- [ ] Drag-and-drop dashboard customization

**Deliverable:** Full-featured dashboard replacing manual SSH/docker commands

---

### Phase 3: Advanced (4 weeks)

**Goal:** Enterprise features and intelligence

- [ ] NixOS service management via agents
- [ ] Advanced RBAC (custom roles, SSO)
- [ ] Mobile-responsive design
- [ ] n8n workflow integration
- [ ] Advanced alerting (anomaly detection)
- [ ] Performance optimization
- [ ] API documentation (OpenAPI)

**Deliverable:** Production-ready unified control plane

---

### Phase 4: Autonomous (ongoing)

**Goal:** Self-healing and intelligence

- [ ] Predictive alerts (AI-powered)
- [ ] Automated remediation workflows
- [ ] Capacity planning (resource forecasting)
- [ ] Usage analytics and optimization suggestions
- [ ] Multi-user collaboration features

**Deliverable:** Hydra control plane that actively maintains cluster health

---

## Success Metrics

### Performance
- Dashboard load time: **<1 second** (target)
- Real-time update latency: **<100ms** (target)
- API response time (p95): **<200ms** (target)
- SSE concurrent connections: **100+** (target)

### User Experience
- **5-second rule compliance**: 100% (user understands status in 5 seconds)
- **Zero-click health check**: Status visible on dashboard load
- **Onboarding time**: <5 minutes for new users
- **Common operations**: 100% via UI (no SSH needed)

### Reliability
- Dashboard uptime: **99.9%** (target)
- Zero data loss on service restart
- MTTR (dashboard issues): **<5 minutes** (target)

### Observability
- Service coverage: **100%** (all services monitored)
- Alert latency: **<1 minute** (event to notification)
- Zero blind spots: All critical metrics visible

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|------------|
| SSE scalability concerns | Redis pub/sub handles 10k+ connections; proven in 2025 case studies |
| Single point of failure (dashboard down) | CLI fallback always available; core services independent |
| Complex NixOS integration | Start with read-only monitoring; add write operations incrementally |
| Real-time performance degradation | Pre-aggregation, caching, and incremental loading |

### Operational Risks

| Risk | Mitigation |
|------|------------|
| User adoption (prefer SSH/CLI) | Make dashboard faster and easier than manual commands |
| Configuration migration | Import existing configs; provide migration guide |
| Learning curve for new tech | Comprehensive docs; video walkthroughs; tooltips in UI |

---

## Open Questions for Shaun

1. **Authentication**: SSO requirement? (OIDC/LDAP) or start with simple username/password?
2. **Mobile App**: Priority? Or mobile-responsive web sufficient for Phase 1-3?
3. **Multi-Tenancy**: Single admin or multiple users with different permissions from start?
4. **Branding**: Custom theme/logo for Hydra, or stick with default UI framework?
5. **External Access**: Tailscale-only or public-facing with stronger auth?

---

## Next Steps

1. **Review this summary** and full research document
2. **Confirm tech stack** (Next.js + FastAPI + PostgreSQL + Redis)
3. **Approve phased approach** (MVP → Core → Advanced → Autonomous)
4. **Answer open questions** above
5. **Kickoff Phase 1 MVP** (2-week sprint)

---

## Resources

**Full Research Document:**
- `/mnt/user/appdata/hydra-dev/docs/research/control-plane-dashboard-architecture-2025.md` (60+ pages, 50+ sources)

**Key Inspirations:**
- **Portainer**: Docker/K8s management done right
- **Homarr**: Best home lab dashboard UX
- **Ray Dashboard**: Unified observability with embedded Grafana
- **Langfuse**: Open-source LLM observability (customizable dashboards)

**Technology Docs:**
- Next.js 15: https://nextjs.org/docs
- FastAPI: https://fastapi.tiangolo.com/
- SSE Guide: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- shadcn/ui: https://ui.shadcn.com/

---

**Prepared by:** Claude (Hydra Autonomous Steward v5.0)
**Research Date:** 2025-12-16
**Status:** Ready for Review and Approval
