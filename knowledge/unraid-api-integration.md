# Unraid Server Management APIs and Integration

## Executive Summary

Unraid 7.2+ includes a built-in GraphQL API that provides comprehensive programmatic access to server management, monitoring, and control. This document covers official API capabilities, third-party alternatives, integration patterns, and how to incorporate Unraid into a unified control plane.

## Table of Contents

1. [Official Unraid API](#official-unraid-api)
2. [API Capabilities](#api-capabilities)
3. [Third-Party APIs](#third-party-apis)
4. [Monitoring and Metrics](#monitoring-and-metrics)
5. [Notification System](#notification-system)
6. [Integration Patterns](#integration-patterns)
7. [Unified Control Plane Integration](#unified-control-plane-integration)
8. [Code Examples](#code-examples)

---

## QUICK START: Unraid 7.2 API Key Setup

**For Shaun:** Follow these steps to enable the Unraid GraphQL API for Hydra integration.

### Step 1: Access API Key Settings
1. Open Unraid WebGUI: http://192.168.1.244
2. Navigate to: **Settings → Management Access → API Keys**

### Step 2: Create API Key via WebGUI (Recommended)
1. Click **"Add API Key"** or **"Create New Key"**
2. Configure:
   - **Name:** `hydra-tools-api`
   - **Description:** `Unified control plane access for Hydra cluster`
   - **Role:** Select **ADMIN** (required for full Docker/Array control)
3. Click **Create** and copy the generated key immediately
4. **IMPORTANT:** The key is only shown once - save it securely!

### Step 3: Create API Key via CLI (Alternative)
SSH into Unraid and run:
```bash
# Create the API key with ADMIN role
unraid-api apikey --create \
  --name "hydra-tools-api" \
  --roles ADMIN \
  --description "Unified control plane access" \
  --json | tee /tmp/hydra-api-key.json

# Extract just the key
cat /tmp/hydra-api-key.json | grep -o '"key":"[^"]*"' | cut -d'"' -f4
```

### Step 4: Configure Hydra Tools API
Add the API key to the container environment:
```bash
# Stop and update the container
docker stop hydra-tools-api

# Run with the new API key
docker run -d --name hydra-tools-api \
  --restart unless-stopped \
  -p 8700:8700 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /mnt/user/appdata/hydra-stack/data:/data \
  -e UNRAID_API_URL=http://192.168.1.244 \
  -e UNRAID_API_KEY=YOUR_KEY_HERE \
  -e PROMETHEUS_URL=http://192.168.1.244:9090 \
  -e QDRANT_URL=http://192.168.1.244:6333 \
  -e LITELLM_URL=http://192.168.1.244:4000 \
  hydra-tools-api:latest
```

### Step 5: Verify Integration
```bash
# Test the API key works
curl -s http://192.168.1.244:8700/api/v1/unraid/health | jq .

# Expected: {"status": "healthy", ...}
```

### Troubleshooting
- **400 Bad Request:** API key missing or invalid
- **401 Unauthorized:** Key doesn't have required permissions
- **Introspection Disabled:** Normal - use specific queries, not introspection

---

## Official Unraid API

### Overview

- **Type:** GraphQL (not REST)
- **Availability:** Built-in starting with Unraid 7.2
- **Pre-7.2:** Available via Unraid Connect plugin
- **Open Source:** Yes (https://github.com/unraid/api)
- **Documentation:** https://docs.unraid.net/API/

### Key Features

- **GraphQL Interface:** Modern, strongly-typed API with introspection
- **Multiple Authentication:** API keys, session cookies, SSO/OIDC
- **Comprehensive Coverage:** Array, Docker, VMs, users, notifications, services
- **Built-in Developer Tools:** Apollo GraphQL Studio sandbox
- **Fine-Grained Permissions:** Role-based access control (RBAC)

### Enabling the API

```bash
# Navigate to: Settings → Management Access → API Keys
# Or enable GraphQL Sandbox at: Settings → Management Access → Developer Options
```

### Authentication Methods

| Method | Use Case | Implementation |
|--------|----------|----------------|
| API Keys | Programmatic access, automation | `x-api-key: <your-key>` header |
| Session Cookies | WebGUI-authenticated requests | Automatic when signed in |
| SSO/OIDC | Enterprise integrations | External provider configuration |

### Available Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| ADMIN | Full system access | Automation, management tools |
| CONNECT | Unraid Connect features | Remote access apps |
| VIEWER | Read-only access | Monitoring dashboards |
| GUEST | Limited access | Public-facing displays |

### Available Resources

```
ACTIVATION_CODE, API_KEY, ARRAY, CLOUD, CONFIG, CONNECT,
CONNECT__REMOTE_ACCESS, CUSTOMIZATIONS, DASHBOARD, DISK,
DISPLAY, DOCKER, FLASH, INFO, LOGS, ME, NETWORK, NOTIFICATIONS,
ONLINE, OS, OWNER, PERMISSION, REGISTRATION, SERVERS, SERVICES,
SHARE, VARS, VMS, WELCOME
```

### Available Actions (per resource)

```
CREATE_ANY, CREATE_OWN, READ_ANY, READ_OWN,
UPDATE_ANY, UPDATE_OWN, DELETE_ANY, DELETE_OWN
```

---

## API Capabilities

### 1. Array Management

**Capabilities:**
- Query array status and configuration
- Start/stop array operations
- Monitor disk status and health
- Perform parity checks (start, pause, resume, cancel)
- Read disk SMART data
- Manage storage pools

**Example Query:**
```graphql
query {
  disks {
    device
    name
    size
    temperature
    smartStatus
    interfaceType
    spundown
  }
}
```

**Example Mutation:**
```graphql
mutation {
  # Start a parity check
  startParityCheck(correct: false)

  # Other operations:
  # pauseParityCheck
  # resumeParityCheck
  # cancelParityCheck
}
```

### 2. Docker Management

**Capabilities:**
- List and manage Docker containers
- Monitor container status
- Start/stop/restart containers
- Manage Docker networks
- Query container resource usage
- Configure autostart settings

**Example Query:**
```graphql
query {
  dockerContainers {
    id
    names
    image
    state
    status
    autoStart
    ports {
      ip
      privatePort
      publicPort
      type
    }
  }
}
```

**Example Mutation:**
```graphql
mutation {
  # Start a container
  dockerContainerStart(id: "container_id")

  # Stop a container
  dockerContainerStop(id: "container_id")

  # Restart a container
  dockerContainerRestart(id: "container_id")
}
```

### 3. Virtual Machine Management

**Capabilities:**
- List and manage VMs
- Query VM state and configuration
- Start/stop/pause VMs
- Create VM snapshots and clones
- Manage VM templates
- View/edit VM XML configuration

**Example Query:**
```graphql
query {
  vms {
    domain {
      uuid
      name
      state
      vcpu
      memory
      autostart
    }
  }
}
```

**Example Mutation:**
```graphql
mutation {
  # Start a VM
  vmStart(uuid: "vm-uuid")

  # Stop a VM
  vmStop(uuid: "vm-uuid")

  # Pause a VM
  vmPause(uuid: "vm-uuid")
}
```

### 4. User Management

**Capabilities:**
- Create, modify, delete users
- Assign permissions and roles
- Manage share access
- Configure security settings

**Example Mutation:**
```graphql
mutation {
  addUser(input: {
    name: "john"
    password: "securepassword"
    description: "John Doe"
  }) {
    id
    name
    roles
  }
}
```

### 5. Share Management

**Capabilities:**
- Query share configuration
- Monitor share usage
- Configure export settings (SMB, NFS, FTP)
- Set security and access controls
- Manage share visibility

**Note:** The official API provides read capabilities. Write operations for shares are primarily through the WebGUI or direct configuration file editing via scripts.

**Integration via Scripts:**
```bash
# User Scripts plugin recommended for share automation
# Access via: Settings → User Scripts
```

### 6. System Information

**Capabilities:**
- Query system details (CPU, memory, OS)
- Monitor system status and health
- Access baseboard and hardware info
- Check service status
- Read system logs

**Example Query:**
```graphql
query {
  systemInfo {
    cpu {
      model
      cores
      threads
    }
    memory {
      total
      available
      used
    }
    os {
      version
      kernel
    }
  }
}
```

### 7. API Key Management

**CLI (Programmatic):**
```bash
# Create API key non-interactively
unraid-api apikey create \
  --name "automation-key" \
  --description "For automation scripts" \
  --roles ADMIN

# Create with specific permissions
unraid-api apikey create \
  --name "docker-only" \
  --permissions "DOCKER:READ_ANY,DOCKER:UPDATE_ANY"

# List API keys
unraid-api apikey list

# Delete API key
unraid-api apikey delete --id <key-id>
```

**GraphQL:**
```graphql
mutation {
  apiKey {
    create(input: {
      name: "My API Key"
      description: "API key for my application"
      roles: [ADMIN]
    }) {
      id
      key
      name
      roles
      permissions
    }
  }
}
```

### 8. Notifications

**Capabilities:**
- Query notification history
- Send custom notifications
- Configure notification settings
- Integrate with notification agents

**Example Query:**
```graphql
query {
  notifications {
    id
    timestamp
    subject
    description
    importance
  }
}
```

---

## Third-Party APIs

### 1. Unraid Simple Monitoring API (REST)

**Purpose:** Lightweight REST API for basic metrics, designed for Homepage/dashboard integration

**GitHub:** https://github.com/NebN/unraid-simple-monitoring-api

**Installation:**
```bash
# Available in Community Applications
# Or via Docker Compose
docker run -d \
  --name unraid-monitoring \
  -p 24940:24940 \
  -v /mnt/user/appdata/unraid-simple-monitoring-api:/app \
  -v /:/hostfs:ro \
  ghcr.io/nebn/unraid-simple-monitoring-api:latest
```

**Configuration (conf.yml):**
```yaml
networks:
  - eth0
disks:
  array:
    - /mnt/disk1
    - /mnt/disk2
    - /mnt/disk3
  cache:
    - /mnt/cache
  custom_pool:
    - /mnt/pool1
```

**Endpoints:**
```bash
# Get all metrics
curl http://192.168.1.244:24940/

# Response includes:
# - array_total: {free, used, total, used_percent, temp, is_spinning}
# - cache_total: {free, used, total, used_percent, temp, is_spinning}
# - network_total: {rx_MiBs, tx_MiBs}
# - cpu: {usage_percent}
# - memory: {used, total, used_percent}
```

**Use Case:** Homepage dashboard custom API widget, lightweight monitoring

### 2. Unraid Management Agent (Go-based)

**GitHub:** https://github.com/ruaan-deysel/unraid-management-agent

**Features:**
- REST API and WebSocket interfaces
- Real-time system monitoring
- Docker/VM control
- Comprehensive hardware metrics

**REST Endpoints:**
```bash
# Start Docker container
curl -X POST http://localhost:8043/api/v1/docker/nginx/start

# Stop Docker container
curl -X POST http://localhost:8043/api/v1/docker/nginx/stop

# Get system metrics
curl http://localhost:8043/api/v1/metrics
```

### 3. ElectricBrain UnraidAPI (Node.js)

**GitHub:** https://github.com/ElectricBrainUK/UnraidAPI

**Features:**
- Node.js API for controlling multiple Unraid instances
- MQTT integration for Home Assistant
- Multi-server support

**Use Case:** Home automation integration, multi-server management

---

## Monitoring and Metrics

### 1. SMART Data and Disk Health

**Official API:**
```graphql
query {
  disks {
    device
    smartStatus
    temperature
    smartAttributes {
      id
      name
      value
      worst
      threshold
      raw
    }
  }
}
```

**Third-Party Tools:**

#### Scrutiny (Recommended)
- **Purpose:** Hard drive health dashboard with historical SMART data
- **Features:** Real-world failure rate predictions (Backblaze data)
- **Installation:** Community Applications → Scrutiny
- **Image:** linuxserver/scrutiny

#### Integration with Prometheus
```yaml
# Prometheus can scrape Unraid metrics via:
# 1. Node Exporter (install in Unraid)
# 2. Custom exporters for SMART data
# 3. Scrutiny metrics endpoint
```

### 2. UPS Monitoring (NUT Integration)

**Plugin:** Network UPS Tools (NUT) by desertwitch

**Installation:**
```bash
# Install from Community Applications
# Configure at: Settings → NUT Settings
```

**Configuration:**
- **Mode:** Master (if UPS connected via USB) or Slave (if reading from remote NUT server)
- **Master IP:** IP of NUT server (if in slave mode)
- **Shutdown Timer:** Time on battery before shutdown (minutes)

**API Access:**
```bash
# NUT provides upsc command-line tool
upsc ups@192.168.1.244

# Third-party wrappers available:
# - NodeJS NUT client module
# - REST API wrapper for upsc (outputs JSON)
# - Tiny dashboard for NUT (Web-UI + REST API)
```

**Telegraf Integration:**
```toml
[[inputs.upsd]]
  address = "192.168.1.244:3493"
```

**Home Assistant Integration:**
```yaml
# Configuration.yaml
sensor:
  - platform: nut
    host: 192.168.1.244
    port: 3493
    resources:
      - ups.load
      - ups.status
      - battery.charge
      - battery.runtime
```

**Grafana Dashboards:**
- Dashboard ID 10914: "Unraid NUT UPS Dashboard TR"
- Dashboard ID 20846: "NUT UPS Telegraf"

### 3. Docker/Container Stats

**cAdvisor (Container Advisor):**
```yaml
# Include in docker-compose.yml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:latest
  ports:
    - "8080:8080"
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
```

**Prometheus Scrape Config:**
```yaml
scrape_configs:
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['192.168.1.244:8080']
```

### 4. Network Stats

**Via Official API:**
```graphql
query {
  network {
    interfaces {
      name
      rxBytes
      txBytes
      rxPackets
      txPackets
      rxErrors
      txErrors
    }
  }
}
```

**Via Unraid Simple Monitoring API:**
```bash
curl http://192.168.1.244:24940/ | jq '.network_total'
# Returns: {rx_MiBs, tx_MiBs}
```

---

## Notification System

### Built-in Notification Agents

Unraid supports multiple notification methods out of the box:

| Agent | Configuration Location | Features |
|-------|------------------------|----------|
| Email | Settings → Notifications → Email | SMTP integration |
| Discord | Settings → Notifications → Discord | Webhook URL |
| Pushover | Settings → Notifications → Pushover | Mobile push |
| Slack | Settings → Notifications → Slack | Webhook URL |
| Telegram | Settings → Notifications → Telegram | Bot token + chat ID |

### Discord Integration (Example)

**Setup:**
1. Navigate to Settings → Notifications → Notification Agents
2. Enable Discord agent
3. Enter Discord Webhook URL
4. Configure which events trigger notifications

**Event Types:**
- Array issues (parity errors, disk offline)
- Backup completion
- Temperature warnings
- Service restarts
- Custom script events

### Home Assistant Integration via Webhooks

**Trick:** Unraid's Discord agent accepts any webhook URL, not just Discord

```yaml
# Home Assistant automation
automation:
  - alias: "Unraid Notification Handler"
    trigger:
      platform: webhook
      webhook_id: unraid_notifications
    action:
      service: notify.mobile_app
      data:
        title: "{{ trigger.json.title }}"
        message: "{{ trigger.json.message }}"
```

**Unraid Configuration:**
- Discord Webhook URL: `http://192.168.1.244:8123/api/webhook/unraid_notifications`
- Sends notifications as JSON to Home Assistant

### Custom Scripts with User Scripts Plugin

**Installation:** Community Applications → User Scripts

**Use Cases:**
- Schedule custom automation (cron jobs)
- Send custom notifications
- React to UPS events
- Automate backup workflows

**Example: UPS Power Event Script**
```bash
#!/bin/bash
# Monitor UPS status and stop services on low battery

UPS_STATUS=$(upsc ups@192.168.1.244 ups.status)
BATTERY_CHARGE=$(upsc ups@192.168.1.244 battery.charge)

if [[ "$UPS_STATUS" == "OB" ]] && (( $(echo "$BATTERY_CHARGE < 30" | bc -l) )); then
  echo "UPS on battery, low charge. Stopping Plex..."
  docker stop plex

  # Send notification via webhook
  curl -X POST http://192.168.1.244:5678/webhook/ups-alert \
    -H "Content-Type: application/json" \
    -d '{"status": "low_battery", "charge": "'$BATTERY_CHARGE'"}'
fi
```

**Scheduling:**
- User Scripts GUI: Select script → Schedule → Every 5 minutes

### Webhook-Based Automation

**Feature Request Status:** Community has requested generic webhooks (currently pending)

**Current Workaround:**
- Use Discord agent with n8n/Home Assistant webhook endpoint
- Use User Scripts with curl for custom webhooks
- Integrate via MQTT (ElectricBrain UnraidAPI)

---

## Integration Patterns

### 1. Homepage Dashboard Integration

**Official Unraid Widget (Homepage):**

**Requirements:**
- Unraid 7.2+ or Unraid Connect plugin 2025.08.19.1850+
- API key with ADMIN role

**Configuration (services.yaml):**
```yaml
- Unraid:
    widget:
      type: unraid
      url: http://192.168.1.244
      key: your-api-key-here
      pool1: cache
      pool2: array
```

**Available Fields:**
```yaml
# Pool metrics (requires pool name in config)
{{pool1.free}} {{pool1.used}} {{pool1.total}}
{{pool1.used_percent}} {{pool1.free_percent}}
{{pool1.temp}} {{pool1.is_spinning}}

# Network
{{network.rx_MiBs}} {{network.tx_MiBs}}

# System
{{cpu.usage}} {{memory.used}} {{memory.total}}
```

**Alternative: Custom API Widget with Simple Monitoring API**
```yaml
- Unraid Metrics:
    widget:
      type: customapi
      url: http://192.168.1.244:24940
      mappings:
        - field: array_total
          label: Array Used
          format: percent
        - field: cache_total
          label: Cache Used
          format: percent
        - field: network_total
          label: Network
          format: text
```

### 2. Home Assistant Integration

**Method 1: MQTT (via ElectricBrain UnraidAPI)**

**Container Setup:**
```yaml
unraid-api:
  image: electricbrainuk/unraidapi:latest
  environment:
    MQTT_HOST: 192.168.1.244
    MQTT_PORT: 1883
    UNRAID_HOST: 192.168.1.244
    UNRAID_PORT: 80
```

**Home Assistant Discovery:**
- Automatically creates sensors for array, Docker, VMs
- MQTT topics: `homeassistant/sensor/unraid/*`

**Method 2: REST Sensors (via GraphQL API)**

```yaml
# configuration.yaml
sensor:
  - platform: rest
    name: Unraid Array Status
    resource: http://192.168.1.244/graphql
    method: POST
    headers:
      x-api-key: your-api-key
      Content-Type: application/json
    payload: '{"query": "{ disks { name temperature smartStatus } }"}'
    value_template: "{{ value_json.data.disks | length }}"
    json_attributes:
      - data
```

**Method 3: Custom Integration (Community)**

- GitHub: Search for "Unraid Home Assistant integration"
- Features: Comprehensive monitoring and control
- Sensors: Array, Docker, VMs, UPS, temperatures

### 3. Grafana/Prometheus Integration

**Architecture:**
```
Unraid → Node Exporter → Prometheus → Grafana
Unraid → cAdvisor → Prometheus → Grafana
Unraid → Scrutiny → Prometheus → Grafana
Unraid → NUT → Telegraf → InfluxDB → Grafana
```

**Node Exporter on Unraid:**
```bash
# Install via Community Applications: "Prometheus Node Exporter"
# Or Docker:
docker run -d \
  --name node-exporter \
  --net="host" \
  --pid="host" \
  -v "/:/host:ro,rslave" \
  prom/node-exporter:latest \
  --path.rootfs=/host
```

**Prometheus Scrape Config:**
```yaml
scrape_configs:
  - job_name: 'unraid'
    static_configs:
      - targets: ['192.168.1.244:9100']
        labels:
          node: 'hydra-storage'
```

**Available Grafana Dashboards:**
- Node Exporter Full (ID 1860)
- Docker and System Monitoring (ID 893)
- Unraid NUT UPS Dashboard (ID 10914)
- cAdvisor (ID 14282)

### 4. n8n Workflow Automation

**Integration Points:**

**HTTP Request Node (GraphQL):**
```json
{
  "method": "POST",
  "url": "http://192.168.1.244/graphql",
  "headers": {
    "x-api-key": "{{$credentials.unraidApiKey}}",
    "Content-Type": "application/json"
  },
  "body": {
    "query": "{ dockerContainers { names state } }"
  }
}
```

**Webhook Trigger:**
- Receive notifications from Unraid (via Discord agent)
- Parse JSON payload
- Route to appropriate workflow

**Use Cases:**
- Auto-restart failed containers
- Send alerts to multiple channels
- Backup automation triggers
- Parity check scheduling and reporting

### 5. Organizr Integration

**Organizr** does not directly integrate with Unraid's API. Instead:

**Method 1: Tab Integration**
- Embed Unraid WebGUI as iframe tab
- Requires authentication passthrough

**Method 2: Custom Homepage Tabs**
- Use Homepage widgets within Organizr
- Display Unraid metrics in custom HTML

**Method 3: Reverse Proxy**
- Traefik/Nginx reverse proxy for Unraid WebGUI
- SSO integration via Authelia/Authentik

---

## Unified Control Plane Integration

### Architecture Vision

```
┌─────────────────────────────────────────────────────────────┐
│              Hydra Unified Control Plane                     │
│                 (Hydra Tools API v1.x)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Inference   │  │   Storage    │  │   Compute    │      │
│  │   Management  │  │   Management │  │   Management │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Unified API Gateway / Router             │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  hydra-ai      │  │ hydra-storage  │  │ hydra-compute  │
│  TabbyAPI      │  │ Unraid GraphQL │  │ Ollama API     │
│  (Direct REST) │  │ API + Metrics  │  │ ComfyUI API    │
└────────────────┘  └────────────────┘  └────────────────┘
```

### Control Plane Endpoints

**Proposed Structure:**

```
/api/v1/infrastructure/
├── /nodes                      # Query all nodes (ai, compute, storage)
├── /storage
│   ├── /array                  # Unraid array status
│   ├── /disks                  # Disk health, SMART data
│   ├── /pools                  # Cache/storage pool metrics
│   └── /shares                 # Share configuration
├── /containers                 # All Docker containers (all nodes)
├── /vms                        # Virtual machines (Unraid)
├── /services
│   ├── /inference              # TabbyAPI, Ollama, LiteLLM
│   ├── /databases              # PostgreSQL, Qdrant, Redis
│   ├── /media                  # Plex, *Arr stack
│   └── /automation             # n8n, Home Assistant
├── /monitoring
│   ├── /metrics                # Prometheus data
│   ├── /logs                   # Loki logs
│   ├── /alerts                 # Active alerts
│   └── /health                 # Health checks
└── /power
    ├── /ups                    # UPS status (all nodes)
    └── /gpu                    # GPU power/temperature
```

### Implementation Strategy

**Phase 1: Read-Only Integration**

1. **Unraid GraphQL Client:**
   ```python
   # /src/hydra_tools/clients/unraid_client.py
   from gql import gql, Client
   from gql.transport.requests import RequestsHTTPTransport

   class UnraidClient:
       def __init__(self, base_url: str, api_key: str):
           transport = RequestsHTTPTransport(
               url=f"{base_url}/graphql",
               headers={"x-api-key": api_key}
           )
           self.client = Client(transport=transport)

       def get_array_status(self):
           query = gql("""
               query {
                   array {
                       state
                       numDisks
                       numProtected
                       numUnprotected
                       parityCheck {
                           status
                           progress
                       }
                   }
               }
           """)
           return self.client.execute(query)

       def get_docker_containers(self):
           query = gql("""
               query {
                   dockerContainers {
                       id
                       names
                       state
                       status
                       autoStart
                   }
               }
           """)
           return self.client.execute(query)

       def get_disk_health(self):
           query = gql("""
               query {
                   disks {
                       device
                       name
                       temperature
                       smartStatus
                       spundown
                   }
               }
           """)
           return self.client.execute(query)
   ```

2. **REST Wrapper Endpoint:**
   ```python
   # /src/hydra_tools/routers/infrastructure.py
   from fastapi import APIRouter, Depends
   from hydra_tools.clients.unraid_client import UnraidClient

   router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])

   @router.get("/storage/array")
   async def get_array_status(client: UnraidClient = Depends()):
       """Get Unraid array status"""
       return client.get_array_status()

   @router.get("/storage/disks")
   async def get_disk_health(client: UnraidClient = Depends()):
       """Get disk health and SMART data"""
       return client.get_disk_health()

   @router.get("/containers/unraid")
   async def get_unraid_containers(client: UnraidClient = Depends()):
       """Get Docker containers on Unraid"""
       return client.get_docker_containers()
   ```

3. **Aggregated Metrics Endpoint:**
   ```python
   @router.get("/monitoring/overview")
   async def get_cluster_overview():
       """Aggregate metrics from all nodes"""
       return {
           "storage": {
               "array": unraid_client.get_array_status(),
               "disks": unraid_client.get_disk_health(),
               "utilization": simple_monitoring_api.get_metrics()
           },
           "inference": {
               "tabbyapi": tabbyapi_client.get_status(),
               "ollama": ollama_client.list_models()
           },
           "services": {
               "containers": aggregate_all_containers(),
               "health": uptime_kuma.get_status()
           }
       }
   ```

**Phase 2: Write Operations**

4. **Container Control:**
   ```python
   @router.post("/containers/{container_id}/start")
   async def start_container(container_id: str, client: UnraidClient = Depends()):
       """Start a Docker container on Unraid"""
       mutation = gql("""
           mutation($id: ID!) {
               dockerContainerStart(id: $id) {
                   id
                   state
               }
           }
       """)
       return client.client.execute(mutation, variable_values={"id": container_id})

   @router.post("/containers/{container_id}/stop")
   async def stop_container(container_id: str, client: UnraidClient = Depends()):
       """Stop a Docker container on Unraid"""
       mutation = gql("""
           mutation($id: ID!) {
               dockerContainerStop(id: $id) {
                   id
                   state
               }
           }
       """)
       return client.client.execute(mutation, variable_values={"id": container_id})
   ```

5. **Array Operations:**
   ```python
   @router.post("/storage/array/start")
   async def start_array(client: UnraidClient = Depends()):
       """Start Unraid array"""
       mutation = gql("""
           mutation {
               arrayStart {
                   state
               }
           }
       """)
       return client.client.execute(mutation)

   @router.post("/storage/parity-check")
   async def start_parity_check(correct: bool = False, client: UnraidClient = Depends()):
       """Start parity check"""
       mutation = gql("""
           mutation($correct: Boolean!) {
               startParityCheck(correct: $correct)
           }
       """)
       return client.client.execute(mutation, variable_values={"correct": correct})
   ```

**Phase 3: Event Integration**

6. **Webhook Handler:**
   ```python
   @router.post("/webhooks/unraid")
   async def handle_unraid_webhook(payload: dict):
       """Receive notifications from Unraid (via Discord agent)"""
       event_type = payload.get("type")

       if event_type == "disk_warning":
           # Trigger alert workflow
           await alertmanager.send_alert(payload)
       elif event_type == "parity_complete":
           # Log to database, notify user
           await db.log_event(payload)
           await notify_discord(payload)

       return {"status": "received"}
   ```

7. **Real-time Metrics via WebSocket:**
   ```python
   from fastapi import WebSocket

   @router.websocket("/ws/metrics")
   async def metrics_stream(websocket: WebSocket):
       await websocket.accept()
       while True:
           metrics = {
               "array": await get_array_status(),
               "disks": await get_disk_health(),
               "containers": await get_unraid_containers()
           }
           await websocket.send_json(metrics)
           await asyncio.sleep(5)  # Update every 5 seconds
   ```

### Configuration Management

**Environment Variables:**
```bash
# /mnt/user/appdata/hydra-stack/.env
UNRAID_API_URL=http://192.168.1.244
UNRAID_API_KEY=your-generated-api-key
UNRAID_MONITORING_API_URL=http://192.168.1.244:24940
```

**API Key Setup:**
```bash
# On Unraid
unraid-api apikey create \
  --name "hydra-tools-api" \
  --description "Unified control plane access" \
  --roles ADMIN \
  --non-interactive
```

### Security Considerations

1. **API Key Rotation:**
   - Store keys in environment variables, not code
   - Rotate keys quarterly
   - Use separate keys for different services

2. **Network Security:**
   - Use HTTPS for production (Traefik reverse proxy)
   - Restrict API access to internal network
   - Implement rate limiting

3. **Permission Scoping:**
   ```bash
   # Instead of ADMIN, use specific permissions
   unraid-api apikey create \
     --name "monitoring-only" \
     --permissions "ARRAY:READ_ANY,DOCKER:READ_ANY,VMS:READ_ANY,DISK:READ_ANY"
   ```

4. **Audit Logging:**
   - Log all API calls to Loki
   - Monitor for unusual access patterns
   - Alert on failed authentication attempts

---

## Code Examples

### Complete Python Client

```python
# /src/hydra_tools/clients/unraid_client.py

from typing import Dict, List, Optional
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import requests

class UnraidClient:
    """Comprehensive Unraid API client"""

    def __init__(self, base_url: str, api_key: str):
        # GraphQL client
        transport = RequestsHTTPTransport(
            url=f"{base_url}/graphql",
            headers={"x-api-key": api_key}
        )
        self.gql_client = Client(transport=transport)

        # REST client for Simple Monitoring API (if available)
        self.monitoring_url = "http://192.168.1.244:24940"

    # Array Management
    def get_array_status(self) -> Dict:
        """Get array status and configuration"""
        query = gql("""
            query {
                array {
                    state
                    numDisks
                    numProtected
                    numUnprotected
                    parityCheck {
                        status
                        progress
                        errors
                    }
                }
            }
        """)
        return self.gql_client.execute(query)

    def start_array(self) -> Dict:
        """Start the array"""
        mutation = gql("""
            mutation {
                arrayStart {
                    state
                }
            }
        """)
        return self.gql_client.execute(mutation)

    def stop_array(self) -> Dict:
        """Stop the array"""
        mutation = gql("""
            mutation {
                arrayStop {
                    state
                }
            }
        """)
        return self.gql_client.execute(mutation)

    def start_parity_check(self, correct: bool = False) -> bool:
        """Start a parity check"""
        mutation = gql("""
            mutation($correct: Boolean!) {
                startParityCheck(correct: $correct)
            }
        """)
        result = self.gql_client.execute(mutation, variable_values={"correct": correct})
        return result.get("startParityCheck", False)

    # Disk Management
    def get_disks(self) -> List[Dict]:
        """Get disk information and SMART data"""
        query = gql("""
            query {
                disks {
                    device
                    name
                    size
                    temperature
                    smartStatus
                    interfaceType
                    spundown
                    smartAttributes {
                        id
                        name
                        value
                        worst
                        threshold
                        raw
                    }
                }
            }
        """)
        result = self.gql_client.execute(query)
        return result.get("disks", [])

    def get_disk_health_summary(self) -> Dict:
        """Get summary of disk health"""
        disks = self.get_disks()
        return {
            "total_disks": len(disks),
            "healthy": sum(1 for d in disks if d["smartStatus"] == "PASS"),
            "warning": sum(1 for d in disks if d["smartStatus"] == "WARNING"),
            "failed": sum(1 for d in disks if d["smartStatus"] == "FAIL"),
            "avg_temperature": sum(d.get("temperature", 0) for d in disks) / len(disks) if disks else 0
        }

    # Docker Management
    def get_containers(self) -> List[Dict]:
        """Get all Docker containers"""
        query = gql("""
            query {
                dockerContainers {
                    id
                    names
                    image
                    state
                    status
                    autoStart
                    ports {
                        privatePort
                        publicPort
                        type
                    }
                }
            }
        """)
        result = self.gql_client.execute(query)
        return result.get("dockerContainers", [])

    def start_container(self, container_id: str) -> Dict:
        """Start a Docker container"""
        mutation = gql("""
            mutation($id: ID!) {
                dockerContainerStart(id: $id) {
                    id
                    state
                }
            }
        """)
        return self.gql_client.execute(mutation, variable_values={"id": container_id})

    def stop_container(self, container_id: str) -> Dict:
        """Stop a Docker container"""
        mutation = gql("""
            mutation($id: ID!) {
                dockerContainerStop(id: $id) {
                    id
                    state
                }
            }
        """)
        return self.gql_client.execute(mutation, variable_values={"id": container_id})

    def restart_container(self, container_id: str) -> Dict:
        """Restart a Docker container"""
        mutation = gql("""
            mutation($id: ID!) {
                dockerContainerRestart(id: $id) {
                    id
                    state
                }
            }
        """)
        return self.gql_client.execute(mutation, variable_values={"id": container_id})

    # VM Management
    def get_vms(self) -> List[Dict]:
        """Get all virtual machines"""
        query = gql("""
            query {
                vms {
                    domain {
                        uuid
                        name
                        state
                        vcpu
                        memory
                        autostart
                    }
                }
            }
        """)
        result = self.gql_client.execute(query)
        return result.get("vms", [])

    def start_vm(self, vm_uuid: str) -> Dict:
        """Start a VM"""
        mutation = gql("""
            mutation($uuid: ID!) {
                vmStart(uuid: $uuid) {
                    uuid
                    state
                }
            }
        """)
        return self.gql_client.execute(mutation, variable_values={"uuid": vm_uuid})

    def stop_vm(self, vm_uuid: str) -> Dict:
        """Stop a VM"""
        mutation = gql("""
            mutation($uuid: ID!) {
                vmStop(uuid: $uuid) {
                    uuid
                    state
                }
            }
        """)
        return self.gql_client.execute(mutation, variable_values={"uuid": vm_uuid})

    # System Info
    def get_system_info(self) -> Dict:
        """Get system information"""
        query = gql("""
            query {
                systemInfo {
                    cpu {
                        model
                        cores
                        threads
                    }
                    memory {
                        total
                        available
                        used
                    }
                    os {
                        version
                        kernel
                    }
                }
            }
        """)
        return self.gql_client.execute(query)

    # Monitoring (Simple API)
    def get_simple_metrics(self) -> Optional[Dict]:
        """Get metrics from Unraid Simple Monitoring API"""
        try:
            response = requests.get(self.monitoring_url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching simple metrics: {e}")
            return None

    # User Management
    def list_users(self) -> List[Dict]:
        """List all users"""
        query = gql("""
            query {
                users {
                    id
                    name
                    description
                    roles
                }
            }
        """)
        result = self.gql_client.execute(query)
        return result.get("users", [])

    def create_user(self, name: str, password: str, description: str = "") -> Dict:
        """Create a new user"""
        mutation = gql("""
            mutation($name: String!, $password: String!, $description: String) {
                addUser(input: {name: $name, password: $password, description: $description}) {
                    id
                    name
                    roles
                }
            }
        """)
        return self.gql_client.execute(mutation, variable_values={
            "name": name,
            "password": password,
            "description": description
        })

# Example usage
if __name__ == "__main__":
    client = UnraidClient(
        base_url="http://192.168.1.244",
        api_key="your-api-key-here"
    )

    # Get array status
    array_status = client.get_array_status()
    print(f"Array state: {array_status['array']['state']}")

    # Get disk health summary
    health = client.get_disk_health_summary()
    print(f"Disk health: {health['healthy']}/{health['total_disks']} healthy")

    # List containers
    containers = client.get_containers()
    for container in containers:
        print(f"{container['names'][0]}: {container['state']}")

    # Get simple metrics (if available)
    metrics = client.get_simple_metrics()
    if metrics:
        print(f"Array usage: {metrics['array_total']['used_percent']}%")
```

### FastAPI Integration

```python
# /src/hydra_tools/routers/unraid.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from hydra_tools.clients.unraid_client import UnraidClient
import os

router = APIRouter(prefix="/unraid", tags=["unraid"])

def get_unraid_client() -> UnraidClient:
    """Dependency to get Unraid client"""
    return UnraidClient(
        base_url=os.getenv("UNRAID_API_URL", "http://192.168.1.244"),
        api_key=os.getenv("UNRAID_API_KEY")
    )

# Array endpoints
@router.get("/array/status")
async def get_array_status(client: UnraidClient = Depends(get_unraid_client)):
    """Get Unraid array status"""
    return client.get_array_status()

@router.post("/array/start")
async def start_array(client: UnraidClient = Depends(get_unraid_client)):
    """Start the Unraid array"""
    return client.start_array()

@router.post("/array/stop")
async def stop_array(client: UnraidClient = Depends(get_unraid_client)):
    """Stop the Unraid array"""
    return client.stop_array()

@router.post("/array/parity-check")
async def start_parity_check(
    correct: bool = False,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Start a parity check"""
    success = client.start_parity_check(correct=correct)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start parity check")
    return {"status": "started", "correcting": correct}

# Disk endpoints
@router.get("/disks")
async def get_disks(client: UnraidClient = Depends(get_unraid_client)):
    """Get disk information and SMART data"""
    return client.get_disks()

@router.get("/disks/health")
async def get_disk_health(client: UnraidClient = Depends(get_unraid_client)):
    """Get disk health summary"""
    return client.get_disk_health_summary()

# Docker endpoints
@router.get("/containers")
async def list_containers(client: UnraidClient = Depends(get_unraid_client)):
    """List all Docker containers on Unraid"""
    return client.get_containers()

@router.post("/containers/{container_id}/start")
async def start_container(
    container_id: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Start a Docker container"""
    return client.start_container(container_id)

@router.post("/containers/{container_id}/stop")
async def stop_container(
    container_id: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Stop a Docker container"""
    return client.stop_container(container_id)

@router.post("/containers/{container_id}/restart")
async def restart_container(
    container_id: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Restart a Docker container"""
    return client.restart_container(container_id)

# VM endpoints
@router.get("/vms")
async def list_vms(client: UnraidClient = Depends(get_unraid_client)):
    """List all virtual machines"""
    return client.get_vms()

@router.post("/vms/{vm_uuid}/start")
async def start_vm(
    vm_uuid: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Start a virtual machine"""
    return client.start_vm(vm_uuid)

@router.post("/vms/{vm_uuid}/stop")
async def stop_vm(
    vm_uuid: str,
    client: UnraidClient = Depends(get_unraid_client)
):
    """Stop a virtual machine"""
    return client.stop_vm(vm_uuid)

# System endpoints
@router.get("/system/info")
async def get_system_info(client: UnraidClient = Depends(get_unraid_client)):
    """Get system information"""
    return client.get_system_info()

@router.get("/metrics")
async def get_metrics(client: UnraidClient = Depends(get_unraid_client)):
    """Get comprehensive metrics"""
    simple_metrics = client.get_simple_metrics()
    disk_health = client.get_disk_health_summary()
    array_status = client.get_array_status()

    return {
        "array": array_status,
        "disks": disk_health,
        "metrics": simple_metrics
    }

# Webhook endpoint for Unraid notifications
@router.post("/webhook")
async def handle_webhook(payload: dict):
    """Handle webhook notifications from Unraid"""
    # Log the event
    print(f"Received Unraid webhook: {payload}")

    # Process based on event type
    # (Integrate with alerting system, log to database, etc.)

    return {"status": "received"}
```

### Docker Compose Addition

```yaml
# Add to /mnt/user/appdata/hydra-stack/docker-compose.yml

services:
  # ... existing services ...

  hydra-tools-api:
    image: your-registry/hydra-tools-api:latest
    container_name: hydra-tools-api
    environment:
      - UNRAID_API_URL=http://192.168.1.244
      - UNRAID_API_KEY=${UNRAID_API_KEY}
      - UNRAID_MONITORING_API_URL=http://192.168.1.244:24940
    ports:
      - "8700:8700"
    restart: unless-stopped
    networks:
      - hydra-network
```

---

## Best Practices

### 1. API Key Management

- **Use specific permissions** instead of ADMIN role when possible
- **Rotate keys quarterly** for security
- **Separate keys** for different services (monitoring vs. control)
- **Store securely** in environment variables, not in code
- **Document key purposes** for future reference

### 2. Error Handling

```python
from gql.transport.exceptions import TransportQueryError

try:
    result = client.get_array_status()
except TransportQueryError as e:
    print(f"GraphQL error: {e}")
    # Handle authentication errors, malformed queries, etc.
except Exception as e:
    print(f"Unexpected error: {e}")
    # Fallback behavior
```

### 3. Rate Limiting

- Don't poll GraphQL API too frequently (max 1/second recommended)
- Use WebSocket subscriptions for real-time data when available
- Cache results when data doesn't change frequently

### 4. Monitoring Integration

- Send all API calls to Loki for audit logging
- Create Grafana dashboards for API usage metrics
- Alert on failed authentication attempts

### 5. Testing

```python
# Test connectivity before deployment
def test_unraid_connection():
    client = UnraidClient(base_url="http://192.168.1.244", api_key="test-key")
    try:
        info = client.get_system_info()
        print(f"✓ Connected to Unraid {info['os']['version']}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
```

---

## Troubleshooting

### GraphQL API Not Responding

**Check API is enabled:**
```bash
# On Unraid web interface
# Settings → Management Access → API → Ensure API is enabled
```

**Test endpoint:**
```bash
curl -X POST http://192.168.1.244/graphql \
  -H "x-api-key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { queryType { name } } }"}'
```

### Permission Denied Errors

**Verify API key permissions:**
```bash
# List API keys and their permissions
unraid-api apikey list
```

**Check required permissions for operation:**
- Array operations: `ARRAY:READ_ANY`, `ARRAY:UPDATE_ANY`
- Docker: `DOCKER:READ_ANY`, `DOCKER:UPDATE_ANY`
- VMs: `VMS:READ_ANY`, `VMS:UPDATE_ANY`

### Simple Monitoring API Not Accessible

**Check container is running:**
```bash
docker ps | grep monitoring
```

**Verify configuration file exists:**
```bash
cat /mnt/user/appdata/unraid-simple-monitoring-api/conf.yml
```

**Test endpoint:**
```bash
curl http://192.168.1.244:24940
```

---

## References

### Official Documentation
- [Unraid API Docs](https://docs.unraid.net/API/)
- [How to Use the Unraid API](https://docs.unraid.net/API/how-to-use-the-api/)
- [Programmatic API Key Management](https://docs.unraid.net/API/programmatic-api-key-management/)
- [Unraid API GitHub](https://github.com/unraid/api)

### Third-Party Tools
- [Unraid Simple Monitoring API](https://github.com/NebN/unraid-simple-monitoring-api)
- [Unraid Management Agent](https://github.com/ruaan-deysel/unraid-management-agent)
- [ElectricBrain UnraidAPI](https://github.com/ElectricBrainUK/UnraidAPI)
- [Homepage Integration](https://gethomepage.dev/widgets/services/unraid/)

### Community Resources
- [Unraid Forums - API Support](https://forums.unraid.net/)
- [Unraid API Discussion on Home Assistant](https://community.home-assistant.io/t/unraid-api-connect-and-control-unraid-servers-through-home-assistant-via-mqtt/154198)
- [Scrutiny for SMART Monitoring](https://unraid-guides.com/2021/11/11/scrutiny-is-a-must-have-app-to-monitor-unraids-drives/)

---

*Knowledge file: unraid-api-integration.md*
*Created: December 16, 2025*
*For: Hydra Cluster - hydra-storage (Unraid)*
