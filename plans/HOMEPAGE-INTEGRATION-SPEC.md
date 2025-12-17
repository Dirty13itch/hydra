# HOMEPAGE INTEGRATION SPECIFICATION
## Integrating Homepage Services into Hydra Command Center

> **Version:** 1.0.0
> **Date:** 2025-12-17

---

## OVERVIEW

This document specifies how to integrate the 22 Homepage services into the Hydra Command Center for a unified control interface.

---

## CURRENT STATE

### Homepage Configuration
**Location:** `/mnt/user/appdata/hydra-stack/homepage/services.yaml`
**Format:** Static YAML with manual service definitions

### Command Center
**Location:** `http://192.168.1.244:3210`
**API:** Hydra Tools API v2.3.0 at port 8700
**Features:** Real-time SSE updates, dynamic health checking

---

## INTEGRATION ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                   UNIFIED SERVICE DASHBOARD                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐    ┌─────────────────┐                   │
│   │   Homepage      │    │   Hydra Tools   │                   │
│   │   services.yaml │───▶│   API /health   │                   │
│   └─────────────────┘    └─────────────────┘                   │
│           │                      │                              │
│           ▼                      ▼                              │
│   ┌─────────────────────────────────────────┐                  │
│   │         SERVICE REGISTRY                 │                  │
│   │  - Static config (Homepage)              │                  │
│   │  - Dynamic health (API)                  │                  │
│   │  - Combined service map                  │                  │
│   └─────────────────────────────────────────┘                  │
│                      │                                          │
│                      ▼                                          │
│   ┌─────────────────────────────────────────┐                  │
│   │         COMMAND CENTER UI                │                  │
│   │  - ServiceGrid component                 │                  │
│   │  - Real-time status badges              │                  │
│   │  - Quick-launch links                   │                  │
│   │  - Health history graphs                │                  │
│   └─────────────────────────────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## SERVICE MAPPING

### Category 1: AI & Inference (PRIORITY: HIGH)
| Homepage Service | Hydra Health Endpoint | Integration |
|------------------|----------------------|-------------|
| Open WebUI | `/health/cluster` (Open WebUI) | Full |
| SillyTavern | HTTP check | Partial |
| TabbyAPI | `/health/cluster` (TabbyAPI) | Full |
| Ollama | `/health/cluster` (Ollama) | Full |

### Category 2: Image Generation (PRIORITY: HIGH)
| Homepage Service | Hydra Health Endpoint | Integration |
|------------------|----------------------|-------------|
| ComfyUI | `/health/cluster` (ComfyUI) | Full |
| Stash | HTTP check | Partial |

### Category 3: Automation (PRIORITY: HIGH)
| Homepage Service | Hydra Health Endpoint | Integration |
|------------------|----------------------|-------------|
| n8n | `/health/cluster` (n8n) | Full |
| Home Assistant | HTTP check | Partial |
| Perplexica | HTTP check | Partial |
| SearXNG | HTTP check | Partial |

### Category 4: Observability (PRIORITY: HIGH)
| Homepage Service | Hydra Health Endpoint | Integration |
|------------------|----------------------|-------------|
| Grafana | `/health/cluster` (Grafana) | Full |
| Portainer | HTTP check | Partial |
| Prometheus | `/health/cluster` (Prometheus) | Full |

### Category 5: Media (PRIORITY: LOW)
| Homepage Service | Hydra Health Endpoint | Integration |
|------------------|----------------------|-------------|
| Plex | HTTP check | Minimal |
| Sonarr | HTTP check | Minimal |
| Radarr | HTTP check | Minimal |
| Lidarr | HTTP check | Minimal |

### Category 6: Downloads (PRIORITY: LOW)
| Homepage Service | Hydra Health Endpoint | Integration |
|------------------|----------------------|-------------|
| qBittorrent | HTTP check | Minimal |
| SABnzbd | HTTP check | Minimal |
| Prowlarr | HTTP check | Minimal |

### Category 7: Infrastructure (PRIORITY: MEDIUM)
| Homepage Service | Hydra Health Endpoint | Integration |
|------------------|----------------------|-------------|
| AdGuard DNS | HTTP check | Partial |
| Miniflux | HTTP check | Partial |

---

## API ENDPOINT DESIGN

### New Endpoint: `/api/v1/services/unified`

```python
@router.get("/services/unified")
async def get_unified_services():
    """
    Returns combined service data from Homepage config and live health checks.
    """
    return {
        "services": [
            {
                "id": "tabbyapi",
                "name": "TabbyAPI",
                "category": "inference",
                "url": "http://192.168.1.250:5000/docs",
                "icon": "si-api",
                "description": "70B Uncensored LLM API",
                "status": "healthy",  # from /health/cluster
                "latency_ms": 31,
                "source": "hydra",  # vs "homepage"
                "node": "hydra-ai"
            },
            {
                "id": "plex",
                "name": "Plex",
                "category": "media",
                "url": "http://192.168.1.244:32400/web",
                "icon": "plex.svg",
                "description": "Media streaming server",
                "status": "unknown",  # not monitored by Hydra
                "latency_ms": null,
                "source": "homepage",
                "node": "hydra-storage"
            }
        ],
        "categories": ["inference", "automation", "observability", ...],
        "counts": {
            "total": 22,
            "healthy": 15,
            "unhealthy": 0,
            "unknown": 7
        }
    }
```

### New Endpoint: `/api/v1/services/config`

```python
@router.get("/services/config")
async def get_services_config():
    """
    Returns parsed Homepage services.yaml configuration.
    """
    # Parse /mnt/user/appdata/hydra-stack/homepage/services.yaml
    return {"services": [...]}
```

---

## FRONTEND COMPONENTS

### ServiceGrid Component

```tsx
// apps/hydra-command-center/src/components/ServiceGrid.tsx

interface Service {
  id: string;
  name: string;
  category: string;
  url: string;
  icon: string;
  description: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  latency_ms: number | null;
  source: 'hydra' | 'homepage';
  node: string;
}

const ServiceGrid: React.FC<{services: Service[]}> = ({services}) => {
  // Group by category
  const grouped = groupBy(services, 'category');

  return (
    <div className="grid grid-cols-4 gap-4">
      {Object.entries(grouped).map(([category, items]) => (
        <ServiceCategory key={category} name={category} services={items} />
      ))}
    </div>
  );
};
```

### ServiceCard Component

```tsx
const ServiceCard: React.FC<{service: Service}> = ({service}) => {
  return (
    <a
      href={service.url}
      target="_blank"
      className="p-4 rounded-lg bg-surface-elevated hover:bg-surface-hover"
    >
      <div className="flex items-center gap-3">
        <img src={`/icons/${service.icon}`} className="w-8 h-8" />
        <div>
          <h3 className="font-medium">{service.name}</h3>
          <p className="text-sm text-muted">{service.description}</p>
        </div>
        <StatusBadge status={service.status} latency={service.latency_ms} />
      </div>
    </a>
  );
};
```

---

## IMPLEMENTATION PLAN

### Phase 1: API Backend (Day 1)
1. Create `routers/services.py` with unified endpoint
2. Parse Homepage YAML configuration
3. Merge with `/health/cluster` data
4. Add caching (5-second TTL)

### Phase 2: Frontend Components (Day 2)
1. Create ServiceGrid component
2. Create ServiceCard component
3. Create StatusBadge component
4. Add to Dashboard view

### Phase 3: Real-time Updates (Day 3)
1. Add SSE event for service status changes
2. Subscribe ServiceGrid to updates
3. Add connection status indicator

### Phase 4: Polish (Day 4)
1. Add service icons
2. Implement search/filter
3. Add category toggles
4. Add service quick-actions

---

## DATA FLOW

```
1. User loads Command Center
   ↓
2. Dashboard fetches /api/v1/services/unified
   ↓
3. Backend merges:
   - Homepage services.yaml (22 services)
   - /health/cluster (15 monitored services)
   ↓
4. Returns unified service list with:
   - Static config (name, url, icon)
   - Live health (status, latency)
   ↓
5. ServiceGrid renders grouped cards
   ↓
6. SSE events update status in real-time
```

---

## BENEFITS

1. **Single Pane of Glass** - All services in one view
2. **Live Status** - Real-time health for monitored services
3. **Quick Launch** - One-click access to any service
4. **Categorization** - Logical grouping by function
5. **Consistency** - Unified styling and UX

---

## FILES TO CREATE/MODIFY

### New Files
- `src/hydra_tools/routers/services.py` - Unified services router
- `apps/hydra-command-center/src/components/ServiceGrid.tsx`
- `apps/hydra-command-center/src/components/ServiceCard.tsx`

### Modified Files
- `src/hydra_tools/api.py` - Wire services router
- `apps/hydra-command-center/src/views/Dashboard.tsx` - Add ServiceGrid

---

## SUCCESS METRICS

- [ ] All 22 Homepage services visible in Command Center
- [ ] 15 monitored services show live health status
- [ ] Status updates within 5 seconds of change
- [ ] Page load time < 500ms
- [ ] Mobile-responsive layout

---

*Generated by Hydra Autonomous System*
*ULTRATHINK Mode - Integration Specification*
