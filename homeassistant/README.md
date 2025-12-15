# Hydra Cluster Home Assistant Integration

This integration provides comprehensive monitoring and control of the Hydra AI cluster from Home Assistant.

## Features

- **Real-time cluster health monitoring** via REST sensors
- **GPU temperature and power monitoring** via SSH
- **Node availability tracking** via ping sensors
- **Automated alerts** for critical services, temperature, and power
- **Model management** buttons and presets
- **Service control** via shell commands
- **Custom Lovelace dashboard** with gauges and controls

## Installation

### 1. Copy Configuration Files

Copy these files to your Home Assistant config directory:

```bash
# On hydra-storage
cp configuration.yaml /mnt/user/appdata/homeassistant/hydra_cluster.yaml
cp automations.yaml /mnt/user/appdata/homeassistant/hydra_automations.yaml
cp shell_commands.yaml /mnt/user/appdata/homeassistant/hydra_shell_commands.yaml
```

### 2. Include in Main Configuration

Add to your `configuration.yaml`:

```yaml
# Include Hydra cluster monitoring
homeassistant:
  packages:
    hydra: !include hydra_cluster.yaml

automation: !include_dir_merge_list automations/
shell_command: !include hydra_shell_commands.yaml
```

Or merge the contents directly into your existing files.

### 3. Set Up SSH Keys

For GPU monitoring and shell commands to work, Home Assistant needs SSH access:

```bash
# Generate SSH key for Home Assistant (if not exists)
docker exec -it homeassistant ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N ""

# Copy public key to cluster nodes
docker exec homeassistant cat /root/.ssh/id_ed25519.pub
# Then add to ~/.ssh/authorized_keys on each node

# Test connections
docker exec homeassistant ssh -o StrictHostKeyChecking=no typhon@192.168.1.250 "echo OK"
docker exec homeassistant ssh -o StrictHostKeyChecking=no typhon@192.168.1.203 "echo OK"
docker exec homeassistant ssh -o StrictHostKeyChecking=no root@192.168.1.244 "echo OK"
```

### 4. Install Dashboard

1. Go to Settings > Dashboards > Add Dashboard
2. Create a new dashboard named "Hydra Cluster"
3. Edit the dashboard and switch to YAML mode
4. Paste contents of `lovelace-dashboard.yaml`

Or use the UI dashboard editor to recreate the cards manually.

### 5. Configure Mobile App

For push notifications, ensure:
- Home Assistant Companion app is installed
- Update `notify.mobile_app_phone` to match your device name
- Or create a notification group for multiple devices

## Entities Created

### Sensors

| Entity | Description | Update Interval |
|--------|-------------|-----------------|
| `sensor.hydra_cluster_status` | Overall status (healthy/degraded/unhealthy) | 60s |
| `sensor.hydra_services_healthy` | Count of healthy services | 60s |
| `sensor.hydra_services_unhealthy` | Count of unhealthy services | 60s |
| `sensor.hydra_health_score` | Percentage health score | Template |
| `sensor.tabbyapi_model` | Currently loaded model | 120s |
| `sensor.ollama_models_count` | Available Ollama models | 300s |
| `sensor.hydra_ai_gpu_0_temperature` | RTX 5090 temperature | 60s |
| `sensor.hydra_ai_gpu_1_temperature` | RTX 4090 temperature | 60s |
| `sensor.hydra_compute_gpu_0_temperature` | RTX 5070 Ti temperature | 60s |
| `sensor.hydra_ai_gpu_power` | Total AI node GPU power | 30s |
| `sensor.hydra_ai_vram_used` | Total VRAM usage | 60s |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.hydra_critical_alert` | Critical services down |
| `binary_sensor.hydra_ai_node_available` | hydra-ai reachable |
| `binary_sensor.hydra_compute_node_available` | hydra-compute reachable |
| `binary_sensor.hydra_storage_node_available` | hydra-storage reachable |
| `binary_sensor.litellm_available` | LiteLLM gateway status |
| `binary_sensor.qdrant_available` | Qdrant vector DB status |

### Input Helpers

| Entity | Description |
|--------|-------------|
| `input_select.hydra_model_preset` | Model preset selector |
| `input_boolean.hydra_notifications` | Enable/disable alerts |

## Automations

| Automation | Trigger | Action |
|------------|---------|--------|
| `hydra_critical_alert` | Critical service down | Mobile + persistent notification |
| `hydra_critical_resolved` | Critical alert cleared | Dismiss notifications |
| `hydra_node_offline` | Node unreachable 2min | Mobile notification |
| `hydra_node_online` | Node back online | Dismiss notification |
| `hydra_gpu_hot` | GPU > 80°C for 5min | Mobile warning |
| `hydra_gpu_critical` | GPU > 85°C | Immediate mobile alert |
| `hydra_power_high` | GPU power > 700W 2min | Mobile warning |
| `hydra_daily_summary` | 8:00 AM daily | Health summary notification |
| `hydra_model_changed` | Model changes | Mobile notification |
| `hydra_auto_restart_litellm` | LiteLLM down 5min | Auto-restart + alert if failed |

## Shell Commands

| Command | Description |
|---------|-------------|
| `hydra_restart_litellm` | Restart LiteLLM container |
| `hydra_restart_tabbyapi` | Restart TabbyAPI service |
| `hydra_restart_ollama` | Restart Ollama service |
| `hydra_restart_openwebui` | Restart Open WebUI |
| `hydra_gpu_power_limit_ai` | Set GPU power limits |
| `hydra_load_model_default` | Load 70B model |
| `hydra_load_model_fast` | Load 8B model |
| `hydra_load_model_coding` | Load coding model |
| `hydra_unload_model` | Unload current model |
| `hydra_health_check` | Trigger health check |
| `hydra_docker_cleanup` | Clean Docker resources |

## Customization

### Adding More GPU Sensors

Add to `configuration.yaml`:

```yaml
command_line:
  - sensor:
      name: "Hydra Compute GPU 1 Temperature"
      command: "ssh typhon@192.168.1.203 'nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits -i 1'"
      unit_of_measurement: "°C"
      scan_interval: 60
```

### Adding Container Monitoring

For specific Docker container status:

```yaml
command_line:
  - binary_sensor:
      name: "Hydra n8n Running"
      command: "ssh root@192.168.1.244 'docker inspect -f {{.State.Running}} n8n'"
      payload_on: "true"
      payload_off: "false"
```

### Discord Notifications

Replace mobile notifications with Discord:

```yaml
action:
  - service: notify.discord
    data:
      target: "CHANNEL_ID"
      message: "{{ message }}"
```

## Troubleshooting

### SSH Commands Failing

```bash
# Test from HA container
docker exec -it homeassistant bash
ssh -v typhon@192.168.1.250

# Check SSH key permissions
chmod 600 ~/.ssh/id_ed25519
```

### REST Sensors Unavailable

```bash
# Verify health service is running
curl http://192.168.1.244:8600/health/summary

# Check HA logs
docker logs homeassistant | grep -i hydra
```

### Missing Notifications

1. Check `input_boolean.hydra_notifications` is `on`
2. Verify mobile app entity name matches
3. Check HA notification settings

## Dependencies

- Home Assistant 2024.1+
- REST integration (built-in)
- Command Line integration (built-in)
- Ping integration (built-in)
- SSH access to cluster nodes
- hydra-health service running on port 8600
