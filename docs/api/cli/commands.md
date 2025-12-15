# Hydra CLI Commands

The `hydra` command provides cluster management from the terminal.

## Installation

```bash
pip install hydra-cluster
# or
pip install -e /path/to/hydra
```

## Commands

### hydra status

Show overall cluster health.

```bash
hydra status
```

**Output:**

```
╭───────────────────────────────────────╮
│      Hydra Cluster Status             │
╰───────────────────────────────────────╯

          Nodes
┌──────────────┬───────────────┬──────────┬────────────────────┐
│ Node         │ IP            │ Status   │ Role               │
├──────────────┼───────────────┼──────────┼────────────────────┤
│ hydra-ai     │ 192.168.1.250 │ ● Online │ Primary inference  │
│ hydra-compute│ 192.168.1.203 │ ● Online │ Secondary inference│
│ hydra-storage│ 192.168.1.244 │ ● Online │ Storage & services │
└──────────────┴───────────────┴──────────┴────────────────────┘

        Services
┌────────────┬───────────────┬──────┬──────────┬─────────┐
│ Service    │ Node          │ Port │ Status   │ Latency │
├────────────┼───────────────┼──────┼──────────┼─────────┤
│ tabbyapi   │ hydra-ai      │ 5000 │ ● HTTP 200│ 12.5ms │
│ ollama     │ hydra-compute │ 11434│ ● HTTP 200│ 8.2ms  │
...
```

### hydra nodes

List cluster nodes with details.

```bash
hydra nodes
```

Shows each node's IP, user, role, status, and uptime.

### hydra services

List services with optional filtering.

```bash
# All services
hydra services

# Filter by node
hydra services --node hydra-storage

# Filter by category
hydra services --category inference
```

### hydra gpu

GPU status and management.

```bash
# Show GPU status
hydra gpu
hydra gpu status

# Set power limit
hydra gpu power hydra-ai 0 450
```

**Output:**

```
╭─────────────────────────────╮
│        GPU Status           │
╰─────────────────────────────╯

hydra-ai
┌─────┬─────────────────────┬───────────┬───────────┬────────┬──────┐
│ GPU │ Name                │ VRAM Used │ VRAM Total│ Power  │ Temp │
├─────┼─────────────────────┼───────────┼───────────┼────────┼──────┤
│ 0   │ RTX 5090            │ 28000 MiB │ 32768 MiB │ 320.5W │ 65°C │
│ 1   │ RTX 4090            │ 18000 MiB │ 24576 MiB │ 280.0W │ 62°C │
└─────┴─────────────────────┴───────────┴───────────┴────────┴──────┘
```

### hydra models

List loaded LLM models.

```bash
hydra models
```

Shows models loaded in TabbyAPI and Ollama.

### hydra logs

View service logs.

```bash
# View last 50 lines
hydra logs tabbyapi

# View more lines
hydra logs ollama -n 200

# Follow logs (streaming)
hydra logs litellm -f
```

### hydra ssh

SSH to a cluster node.

```bash
hydra ssh hydra-ai
hydra ssh hydra-storage
```

### hydra backup

Backup operations.

```bash
# Create backup
hydra backup create

# Verify existing backups
hydra backup verify

# List backups
hydra backup list
```

### hydra config

Configuration management.

```bash
# Show cluster config
hydra config show

# Edit a specific config
hydra config edit tabbyapi
hydra config edit litellm
hydra config edit prometheus
```

## Global Options

```bash
hydra --version    # Show version
hydra --help       # Show help
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Connection error |
| 3 | Service unavailable |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HYDRA_SSH_KEY` | SSH key path | `~/.ssh/id_ed25519` |
| `HYDRA_TIMEOUT` | Command timeout | 30 |
| `HYDRA_NO_COLOR` | Disable colors | unset |

## Tips

1. **Tab completion** - Install shell completions:
   ```bash
   hydra --install-completion
   ```

2. **Quick health check** - Just run `hydra` (defaults to status)

3. **Combine with watch** - Monitor continuously:
   ```bash
   watch -n 5 hydra status
   ```

4. **Pipeline to jq** - For scripting (when JSON output is added):
   ```bash
   hydra status --json | jq '.nodes'
   ```
