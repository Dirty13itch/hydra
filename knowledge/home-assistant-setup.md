# Home Assistant Integration Setup

## Getting a Long-Lived Access Token

1. **Open Home Assistant** at http://192.168.1.244:8123
2. **Go to your profile**: Click your name in the bottom left
3. **Scroll to "Long-Lived Access Tokens"**
4. **Click "Create Token"**
5. **Name it**: "Hydra Presence Automation"
6. **Copy the token** (you can only see it once!)

## Configure Hydra

### Option 1: Environment Variable (Recommended)

Add to your docker run command:
```bash
docker run -d \
  --name hydra-tools-api \
  -p 8700:8700 \
  -v /mnt/user/appdata/hydra-tools:/data \
  -e HYDRA_DATA_DIR=/data \
  -e HA_TOKEN="your_token_here" \
  hydra-tools:dev
```

### Option 2: Via API

```bash
# Configure token via API
curl -X POST "http://192.168.1.244:8700/presence/configure" \
  -H "Content-Type: application/json" \
  -d '{"ha_token": "your_token_here"}'
```

## Creating Presence Input Select in Home Assistant

Add to your `configuration.yaml`:

```yaml
input_select:
  presence_mode:
    name: Presence Mode
    options:
      - home
      - away
      - sleep
      - vacation
    initial: home
    icon: mdi:home-account
```

Then create an automation to update it based on phone presence:

```yaml
automation:
  - alias: "Update Presence Mode - Away"
    trigger:
      - platform: state
        entity_id: person.shaun
        to: "not_home"
        for:
          minutes: 5
    action:
      - service: input_select.select_option
        target:
          entity_id: input_select.presence_mode
        data:
          option: "away"

  - alias: "Update Presence Mode - Home"
    trigger:
      - platform: state
        entity_id: person.shaun
        to: "home"
    action:
      - service: input_select.select_option
        target:
          entity_id: input_select.presence_mode
        data:
          option: "home"
```

## Testing the Integration

```bash
# Check current presence state
curl http://192.168.1.244:8700/presence/status

# Manually set presence (for testing)
curl -X POST "http://192.168.1.244:8700/presence/set?state=away"

# Check what actions would be taken
curl http://192.168.1.244:8700/presence/config
```

## Presence Actions

| State | GPU Power | Inference | Containers | Monitoring |
|-------|-----------|-----------|------------|------------|
| home | 450W | Enabled | All | 60s |
| away | 200W | Enabled | Essential | 300s |
| sleep | 100W | Disabled | Minimal | 600s |
| vacation | 100W | Disabled | Minimal | 3600s |
