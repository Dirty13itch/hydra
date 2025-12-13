# Ingress & Reverse Proxy Plan for Hydra Cluster

This document outlines the reverse proxy strategy for providing clean URLs and TLS for Hydra services.

## Recommendation: Caddy on hydra-storage

**Why Caddy over Traefik:**
- Automatic HTTPS with Let's Encrypt (if using public domain)
- Simpler configuration (Caddyfile vs YAML/labels)
- Built-in local CA for `.lan` domains
- Lower resource usage for this scale

## Architecture

```
Client Request
      │
      ▼
┌─────────────┐
│   Caddy     │  ← hydra-storage:80/443
│ (Container) │
└─────────────┘
      │
      ├──► plex.hydra.lan     → 192.168.1.244:32400
      ├──► grafana.hydra.lan  → 192.168.1.244:3003
      ├──► tabby.hydra.lan    → 192.168.1.250:5000
      └──► comfyui.hydra.lan  → 192.168.1.203:8188
```

## TLS Strategy

### Option A: Self-Signed Local CA (Recommended)

Caddy can generate a local CA and issue certs for `.lan` domains.

**Pros:**
- No external dependencies
- Works offline
- HTTPS everywhere

**Cons:**
- Browsers show warning until CA is trusted
- Must install CA cert on each client device

### Option B: HTTP Only (Simplest)

Skip TLS for internal-only services.

**Pros:**
- Zero certificate management
- No browser warnings

**Cons:**
- No encryption on LAN (usually acceptable for homelab)

### Option C: Tailscale HTTPS (For Remote Access)

Use Tailscale's built-in HTTPS certs for `*.ts.net` domains.

**Pros:**
- Valid public certs
- Works over Tailscale VPN

**Cons:**
- Only works via Tailscale
- Different URLs than LAN

## Service Mappings

### Priority 1: High-Traffic Services

| URL | Backend | Notes |
|-----|---------|-------|
| `plex.hydra.lan` | 192.168.1.244:32400 | Media streaming |
| `home.hydra.lan` | 192.168.1.244:3333 | Homepage dashboard |
| `grafana.hydra.lan` | 192.168.1.244:3003 | Metrics |
| `openwebui.hydra.lan` | 192.168.1.250:3000 | Chat UI |

### Priority 2: Management Services

| URL | Backend | Notes |
|-----|---------|-------|
| `portainer.hydra.lan` | 192.168.1.244:9000 | Container management |
| `n8n.hydra.lan` | 192.168.1.244:5678 | Automation |
| `homeassistant.hydra.lan` | 192.168.1.244:8123 | Home automation |
| `vault.hydra.lan` | 192.168.1.244:8444 | Password manager |

### Priority 3: Media Automation

| URL | Backend | Notes |
|-----|---------|-------|
| `sonarr.hydra.lan` | 192.168.1.244:8989 | TV |
| `radarr.hydra.lan` | 192.168.1.244:7878 | Movies |
| `prowlarr.hydra.lan` | 192.168.1.244:9696 | Indexers |
| `qbit.hydra.lan` | 192.168.1.244:8082 | Torrents |

### Priority 4: AI/Inference

| URL | Backend | Notes |
|-----|---------|-------|
| `tabby.hydra.lan` | 192.168.1.250:5000 | TabbyAPI |
| `ollama.hydra.lan` | 192.168.1.203:11434 | Ollama |
| `comfyui.hydra.lan` | 192.168.1.203:8188 | Image gen |
| `litellm.hydra.lan` | 192.168.1.244:4000 | LLM proxy |

## Implementation

### Step 1: Create Caddy Directory

```bash
ssh root@hydra-storage
mkdir -p /mnt/user/appdata/caddy
```

### Step 2: Create Caddyfile

Create `/mnt/user/appdata/caddy/Caddyfile`:

```caddyfile
# Global options
{
    # For .lan domains, use internal CA
    local_certs
    # Or for HTTP only:
    # auto_https off
}

# Homepage Dashboard
home.hydra.lan {
    reverse_proxy 192.168.1.244:3333
}

# Plex
plex.hydra.lan {
    reverse_proxy 192.168.1.244:32400
}

# Grafana
grafana.hydra.lan {
    reverse_proxy 192.168.1.244:3003
}

# Portainer
portainer.hydra.lan {
    reverse_proxy 192.168.1.244:9000
}

# Open WebUI
openwebui.hydra.lan {
    reverse_proxy 192.168.1.250:3000
}

# TabbyAPI
tabby.hydra.lan {
    reverse_proxy 192.168.1.250:5000
}

# n8n
n8n.hydra.lan {
    reverse_proxy 192.168.1.244:5678
}

# Home Assistant
homeassistant.hydra.lan {
    reverse_proxy 192.168.1.244:8123
}

# Sonarr
sonarr.hydra.lan {
    reverse_proxy 192.168.1.244:8989
}

# Radarr
radarr.hydra.lan {
    reverse_proxy 192.168.1.244:7878
}

# Prowlarr
prowlarr.hydra.lan {
    reverse_proxy 192.168.1.244:9696
}

# qBittorrent
qbit.hydra.lan {
    reverse_proxy 192.168.1.244:8082
}

# LiteLLM
litellm.hydra.lan {
    reverse_proxy 192.168.1.244:4000
}

# Ollama
ollama.hydra.lan {
    reverse_proxy 192.168.1.203:11434
}

# ComfyUI
comfyui.hydra.lan {
    reverse_proxy 192.168.1.203:8188
}

# Vaultwarden (already has HTTPS, proxy HTTP)
vault.hydra.lan {
    reverse_proxy 192.168.1.244:8444 {
        transport http {
            tls_insecure_skip_verify
        }
    }
}
```

### Step 3: Create Docker Compose

Create `/mnt/user/appdata/caddy/docker-compose.yml`:

```yaml
version: "3.8"

services:
  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /mnt/user/appdata/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - /mnt/user/appdata/caddy/data:/data
      - /mnt/user/appdata/caddy/config:/config
    networks:
      - hydra-net

networks:
  hydra-net:
    external: true
```

### Step 4: Deploy

```bash
cd /mnt/user/appdata/caddy
docker-compose up -d
docker-compose logs -f
```

### Step 5: Trust Local CA (Optional)

If using `local_certs`, export and install Caddy's root CA:

```bash
# Export CA cert
docker exec caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root-ca.crt

# Install on:
# - Windows: Double-click, install to "Trusted Root Certification Authorities"
# - macOS: Add to Keychain, set to "Always Trust"
# - Linux: Copy to /usr/local/share/ca-certificates/ and run update-ca-certificates
```

## Port Conflicts

**Potential conflicts on hydra-storage:**
- Port 80: Currently unused (available for Caddy)
- Port 443: Currently unused (available for Caddy)

If Nginx or another web server is running, stop it first:
```bash
docker stop nginx  # if exists
```

## WebSocket Support

Some services require WebSocket. Caddy handles this automatically, but for explicit config:

```caddyfile
comfyui.hydra.lan {
    reverse_proxy 192.168.1.203:8188 {
        header_up Upgrade {http.request.header.Upgrade}
        header_up Connection {http.request.header.Connection}
    }
}
```

## Health Checks

Add to Uptime Kuma after deployment:
- `https://home.hydra.lan` (keyword: Homepage)
- `https://grafana.hydra.lan` (keyword: Grafana)
- `https://plex.hydra.lan/web` (keyword: Plex)

## Rollback

If Caddy causes issues:

```bash
cd /mnt/user/appdata/caddy
docker-compose down
```

Services remain accessible via direct IP:port.

---

*Last updated: 2025-12-13*
