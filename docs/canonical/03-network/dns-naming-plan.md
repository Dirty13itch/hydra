# DNS Naming Plan for Hydra Cluster

This document defines the DNS naming convention and implementation for the Hydra cluster using AdGuard Home.

## Domain Scheme

| Type | Pattern | Example |
|------|---------|---------|
| Domain | `hydra.lan` | - |
| Node hostnames | `<node>.hydra.lan` | `storage.hydra.lan` |
| Service CNAMEs | `<service>.hydra.lan` | `plex.hydra.lan` |

## Node Hostnames

| Hostname | IP Address | Node |
|----------|------------|------|
| `storage.hydra.lan` | 192.168.1.244 | hydra-storage (Unraid) |
| `compute.hydra.lan` | 192.168.1.203 | hydra-compute (NixOS) |
| `ai.hydra.lan` | 192.168.1.250 | hydra-ai (NixOS) |

### Legacy Aliases (for compatibility)

| Alias | Target |
|-------|--------|
| `hydra-storage.hydra.lan` | 192.168.1.244 |
| `hydra-compute.hydra.lan` | 192.168.1.203 |
| `hydra-ai.hydra.lan` | 192.168.1.250 |

## Service CNAMEs

All services resolve to the node hosting them.

### hydra-storage (192.168.1.244)

| CNAME | Port | Service |
|-------|------|---------|
| `plex.hydra.lan` | 32400 | Plex Media Server |
| `grafana.hydra.lan` | 3003 | Grafana |
| `prometheus.hydra.lan` | 9090 | Prometheus |
| `portainer.hydra.lan` | 9000 | Portainer |
| `home.hydra.lan` | 3333 | Homepage Dashboard |
| `n8n.hydra.lan` | 5678 | n8n Automation |
| `litellm.hydra.lan` | 4000 | LiteLLM Proxy |
| `qdrant.hydra.lan` | 6333 | Qdrant Vector DB |
| `redis.hydra.lan` | 6379 | Redis |
| `postgres.hydra.lan` | 5432 | PostgreSQL |
| `searx.hydra.lan` | 8888 | SearXNG |
| `firecrawl.hydra.lan` | 3005 | Firecrawl |
| `docling.hydra.lan` | 5001 | Docling |
| `miniflux.hydra.lan` | 8180 | Miniflux RSS |
| `sillytavern.hydra.lan` | 8000 | SillyTavern |
| `kokoro.hydra.lan` | 8880 | Kokoro TTS |
| `perplexica.hydra.lan` | 3030 | Perplexica |
| `homeassistant.hydra.lan` | 8123 | Home Assistant |
| `stash.hydra.lan` | 9999 | Stash |
| `qbit.hydra.lan` | 8082 | qBittorrent |
| `sabnzbd.hydra.lan` | 8085 | SABnzbd |
| `prowlarr.hydra.lan` | 9696 | Prowlarr |
| `sonarr.hydra.lan` | 8989 | Sonarr |
| `radarr.hydra.lan` | 7878 | Radarr |
| `lidarr.hydra.lan` | 8686 | Lidarr |
| `bazarr.hydra.lan` | 6767 | Bazarr |
| `adguard.hydra.lan` | 3053 | AdGuard Home (setup UI) |
| `vault.hydra.lan` | 8444 | Vaultwarden |

### hydra-ai (192.168.1.250)

| CNAME | Port | Service |
|-------|------|---------|
| `tabby.hydra.lan` | 5000 | TabbyAPI |
| `openwebui.hydra.lan` | 3000 | Open WebUI |

### hydra-compute (192.168.1.203)

| CNAME | Port | Service |
|-------|------|---------|
| `ollama.hydra.lan` | 11434 | Ollama |
| `comfyui.hydra.lan` | 8188 | ComfyUI |

## Implementation: AdGuard Home DNS Rewrites

AdGuard Home is running on hydra-storage at `192.168.1.244:53` (DNS) and `192.168.1.244:3053` (web UI).

### Step 1: Access AdGuard Home

1. Open browser to `http://192.168.1.244:3053`
2. Navigate to **Filters** → **DNS rewrites**

### Step 2: Add Node Rewrites

Add these DNS rewrites (one per line in the UI):

```
storage.hydra.lan → 192.168.1.244
compute.hydra.lan → 192.168.1.203
ai.hydra.lan → 192.168.1.250
hydra-storage.hydra.lan → 192.168.1.244
hydra-compute.hydra.lan → 192.168.1.203
hydra-ai.hydra.lan → 192.168.1.250
```

### Step 3: Add Service Rewrites

For services on hydra-storage:
```
plex.hydra.lan → 192.168.1.244
grafana.hydra.lan → 192.168.1.244
prometheus.hydra.lan → 192.168.1.244
portainer.hydra.lan → 192.168.1.244
home.hydra.lan → 192.168.1.244
n8n.hydra.lan → 192.168.1.244
litellm.hydra.lan → 192.168.1.244
qdrant.hydra.lan → 192.168.1.244
redis.hydra.lan → 192.168.1.244
postgres.hydra.lan → 192.168.1.244
searx.hydra.lan → 192.168.1.244
firecrawl.hydra.lan → 192.168.1.244
docling.hydra.lan → 192.168.1.244
miniflux.hydra.lan → 192.168.1.244
sillytavern.hydra.lan → 192.168.1.244
kokoro.hydra.lan → 192.168.1.244
perplexica.hydra.lan → 192.168.1.244
homeassistant.hydra.lan → 192.168.1.244
stash.hydra.lan → 192.168.1.244
qbit.hydra.lan → 192.168.1.244
sabnzbd.hydra.lan → 192.168.1.244
prowlarr.hydra.lan → 192.168.1.244
sonarr.hydra.lan → 192.168.1.244
radarr.hydra.lan → 192.168.1.244
lidarr.hydra.lan → 192.168.1.244
bazarr.hydra.lan → 192.168.1.244
adguard.hydra.lan → 192.168.1.244
vault.hydra.lan → 192.168.1.244
```

For services on hydra-ai:
```
tabby.hydra.lan → 192.168.1.250
openwebui.hydra.lan → 192.168.1.250
```

For services on hydra-compute:
```
ollama.hydra.lan → 192.168.1.203
comfyui.hydra.lan → 192.168.1.203
```

### Step 4: Configure Clients to Use AdGuard

**Option A: Per-device (recommended for testing)**
Set DNS server to `192.168.1.244` on individual devices.

**Option B: Router-wide**
Configure router DHCP to advertise `192.168.1.244` as primary DNS.

**Option C: NixOS nodes**
Add to `/etc/nixos/configuration.nix`:
```nix
networking.nameservers = [ "192.168.1.244" ];
```
Then: `sudo nixos-rebuild switch`

### Step 5: Verify

```bash
# From any client using AdGuard DNS
nslookup plex.hydra.lan
# Should return: 192.168.1.244

nslookup tabby.hydra.lan
# Should return: 192.168.1.250
```

## Notes

- Ports are **not** handled by DNS; you still need `http://plex.hydra.lan:32400`
- For port-free access, implement a reverse proxy (see `ingress-reverse-proxy-plan.md`)
- The `.lan` TLD is commonly used for local networks and won't conflict with public DNS

---

*Last updated: 2025-12-13*
