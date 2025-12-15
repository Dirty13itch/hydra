# Cluster Tools

Tools for cluster management, SSH execution, and service status.

## ssh_execute

Execute commands on cluster nodes via SSH.

```python
from hydra_tools.cluster import ssh_execute

# Run command on specific node
result = ssh_execute(
    command="nvidia-smi",
    node="hydra-ai"
)

# Run on storage node
result = ssh_execute(
    command="docker ps --format '{{.Names}}'",
    node="hydra-storage"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `command` | str | required | Shell command to execute |
| `node` | str | required | Node name or IP |
| `timeout` | int | 30 | Timeout in seconds |
| `sudo` | bool | False | Run with sudo |

### Nodes

| Node | IP | User | Role |
|------|-----|------|------|
| `hydra-ai` | 192.168.1.250 | typhon | Primary inference |
| `hydra-compute` | 192.168.1.203 | typhon | Secondary inference |
| `hydra-storage` | 192.168.1.244 | root | Storage & Docker |

## cluster_status

Get comprehensive cluster status.

```python
from hydra_tools.cluster import cluster_status

status = cluster_status()
```

### Response Format

```json
{
  "nodes": {
    "hydra-ai": {
      "online": true,
      "uptime": "5 days",
      "load": [0.5, 0.4, 0.3]
    }
  },
  "services": {
    "tabbyapi": {"status": "healthy", "latency_ms": 12.5},
    "ollama": {"status": "healthy", "latency_ms": 8.2}
  },
  "gpus": {
    "hydra-ai": [
      {"name": "RTX 5090", "vram_used": "28GB", "vram_total": "32GB"}
    ]
  },
  "timestamp": "2025-12-13T10:30:00Z"
}
```

## check_service

Check health of a specific service.

```python
from hydra_tools.cluster import check_service

# Check TabbyAPI
health = check_service("tabbyapi")
print(f"Status: {health['status']}, Latency: {health['latency_ms']}ms")

# Check by URL
health = check_service("http://192.168.1.244:6333/health")
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service` | str | required | Service name or URL |
| `timeout` | float | 5.0 | Request timeout |

### Known Services

| Service | Port | Health Endpoint |
|---------|------|-----------------|
| tabbyapi | 5000 | /health |
| ollama | 11434 | /api/tags |
| litellm | 4000 | /health |
| qdrant | 6333 | /health |
| prometheus | 9090 | /-/healthy |
| grafana | 3003 | /api/health |

## gpu_status

Get GPU status across cluster.

```python
from hydra_tools.cluster import gpu_status

# All GPUs
gpus = gpu_status()

# Specific node
gpus = gpu_status(node="hydra-ai")
```

### Response Format

```json
{
  "hydra-ai": [
    {
      "index": 0,
      "name": "NVIDIA GeForce RTX 5090",
      "memory_used": 28000,
      "memory_total": 32768,
      "power_draw": 320.5,
      "temperature": 65
    }
  ]
}
```

## docker_containers

List Docker containers on hydra-storage.

```python
from hydra_tools.cluster import docker_containers

# All containers
containers = docker_containers()

# Only running
containers = docker_containers(running_only=True)

# Filter by name
containers = docker_containers(filter="hydra-")
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `running_only` | bool | False | Only show running containers |
| `filter` | str | None | Filter by name pattern |

## restart_service

Restart a cluster service.

```python
from hydra_tools.cluster import restart_service

# Restart TabbyAPI (systemd)
result = restart_service("tabbyapi", node="hydra-ai")

# Restart Docker container
result = restart_service("hydra-litellm", node="hydra-storage")
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service` | str | required | Service or container name |
| `node` | str | required | Node to restart on |

## Error Handling

```python
from hydra_tools import ToolError
from hydra_tools.cluster import ssh_execute

try:
    result = ssh_execute("nvidia-smi", "hydra-ai")
except ToolError as e:
    if "timeout" in str(e).lower():
        print("Node unreachable")
    elif "permission" in str(e).lower():
        print("SSH key not authorized")
```

## Security Notes

- SSH uses key authentication only
- Commands are executed as the configured user (typhon/root)
- Use `sudo=True` for privileged operations on NixOS nodes
- Avoid passing secrets in command arguments

## Best Practices

1. **Use service names** - Abstracts IP/port details
2. **Handle timeouts** - Remote nodes may be slow to respond
3. **Check status before actions** - Verify service is running before restart
4. **Log important operations** - Keep audit trail of cluster changes
