# Infrastructure Knowledge Base

## Hardware Specifications

### hydra-ai (Primary Inference Node)
- **IP:** 192.168.1.250
- **OS:** NixOS (kernel 6.12+)
- **CPU:** AMD Threadripper 7960X (24 cores / 48 threads)
- **RAM:** 128GB DDR5
- **GPUs:**
  - NVIDIA RTX 5090 32GB (Blackwell, sm_120)
  - NVIDIA RTX 4090 24GB (Ada Lovelace, sm_89)
  - Combined VRAM: 56GB (tensor parallel)
- **Storage:** 
  - NVMe for OS
  - NFS mount for models (/mnt/models)
- **Network:**
  - eno1: Aquantia AQC113C 10GbE (PRIMARY - use this for data)
  - enp71s0: Realtek 2.5GbE (management only)
- **Power:** ~800W sustained, ~1425W peak (both GPUs maxed)

### hydra-compute (Secondary Inference + Image Gen)
- **IP:** 192.168.1.203
- **OS:** NixOS (kernel 6.12+)
- **CPU:** AMD Ryzen 9950X (16 cores / 32 threads)
- **RAM:** 64GB DDR5
- **GPUs:**
  - NVIDIA RTX 5070 Ti 16GB (Blackwell, sm_120)
  - NVIDIA RTX 3060 12GB (Ampere, sm_86)
- **Storage:**
  - NVMe for OS
  - NFS mount for models
- **Network:**
  - enp1s0f0: Intel X540-T2 10GbE
- **Power:** ~400W sustained, ~650W peak

### hydra-storage (Unraid NAS + Services)
- **IP:** 192.168.1.244
- **IPMI:** 192.168.1.216
- **OS:** Unraid 7.2.x
- **CPU:** AMD EPYC 7663 (56 cores / 112 threads)
- **RAM:** 256GB DDR4 ECC
- **GPU:** Intel Arc A380 (transcoding, light inference)
- **Storage:** ~180TB mixed array
  - NVMe cache pool
  - HDD parity array
  - SSD for Docker appdata
- **Network:**
  - eth0/eth1: Intel X550-T2 dual 10GbE (LACP bonded)
- **Power:** ~400W sustained, ~530W peak

### hydra-dev (Development VM on Unraid)
- **IP:** DHCP (check Unraid VM tab)
- **Host:** hydra-storage (libvirt/KVM)
- **OS:** Ubuntu 24.04 LTS
- **vCPUs:** 16 (pinned to cores 0-15)
- **RAM:** 64GB
- **Storage:** 500GB qcow2 vdisk
- **Graphics:** QXL (VNC access)
- **Purpose:** Development environment, Antigravity IDE, Parsec remote
- **VNC Access:** 192.168.1.244:5900
- **NFS Mounts:**
  - /mnt/models → 192.168.1.244:/mnt/user/models
  - /mnt/shared → 192.168.1.244:/mnt/user/hydra_shared
- **Setup Script:** `/mnt/user/hydra_shared/hydra-dev-setup.sh`
- **VM Management:**
  ```bash
  # On hydra-storage
  virsh -c qemu:///system list --all
  virsh -c qemu:///system start hydra-dev
  virsh -c qemu:///system shutdown hydra-dev
  ```

## Network Infrastructure

### UniFi Equipment
| Device | IP | Role |
|--------|-----|------|
| UDM Pro | 192.168.1.1 | Router, Controller |
| USW-Pro-24-PoE | 192.168.3.113 | Main switch |
| USW-Pro-XG-10-PoE | - | 10GbE backbone |
| USW-Lite-8-PoE | 192.168.1.76 | Living room switch |
| USW-Flex | 192.168.1.139 | Garage switch |
| U6 Pro | 192.168.1.135 | Basement AP |
| U6+ (Master BR) | 192.168.1.120 | Bedroom AP |
| U6+ (Den) | 192.168.1.118 | Den AP |
| U6+ (Dining) | 192.168.1.184 | Dining AP |

### Network Configuration
- **Primary Subnet:** 192.168.1.0/24
- **VLAN:** Not currently used (single flat network)
- **Jumbo Frames:** Enabled (MTU 9000) on all 10GbE paths
- **DNS:** AdGuard Home on 192.168.1.244:53 (configured in NixOS nodes)

### 10GbE Performance
- **Validated throughput:** 9.4 Gbps
- **NFS throughput:** 1.1 GB/s theoretical, 549 MB/s typical with overhead
- **Model loading:** Reduced from 5+ minutes to ~30 seconds

### NFS Mount Configuration (NixOS)
```nix
fileSystems."/mnt/models" = {
  device = "192.168.1.244:/mnt/user/models";
  fsType = "nfs";
  options = [
    "nfsvers=4.2"
    "nconnect=8"
    "rsize=1048576"
    "wsize=1048576"
    "hard"
    "intr"
    "noatime"
  ];
};
```

## Power Infrastructure

### UPS Configuration
| UPS | Model | Capacity | Connected |
|-----|-------|----------|-----------|
| UPS 1 | APC SMT1500RM2U | 1500VA / 1000W | hydra-ai (partial) |
| UPS 2 | CyberPower CP1500PFCRM2U | 1500VA / ~1000W | hydra-compute, network |

**Total Capacity:** ~2000W real power
**Challenge:** hydra-ai alone can peak at 1425W

### Power Recommendations
1. **GPU Power Limits:**
   - RTX 5090: 450W limit (saves ~75W headroom)
   - RTX 4090: 350W limit (saves ~150W headroom)
   - Combined savings: ~225W peak reduction

2. **Upgrade Path:**
   - Consider 5000VA online UPS (APC SRT5KRMXLT or CyberPower OL5KRTHD)
   - Run hydra-ai on dedicated high-capacity UPS
   - Keep compute/storage on current UPS pair

### Power Monitoring
```bash
# Check GPU power draw
nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits

# Set power limit (requires root)
sudo nvidia-smi -pl 450  # For 5090
sudo nvidia-smi -pl 350  # For 4090
```

## Port Allocation Master List

### hydra-ai (192.168.1.250)
| Port | Service | Protocol |
|------|---------|----------|
| 22 | SSH | TCP |
| 3000 | Open WebUI | HTTP |
| 5000 | TabbyAPI | HTTP |
| 9100 | Node Exporter | HTTP |
| 9835 | NVIDIA Metrics | HTTP |

### hydra-compute (192.168.1.203)
| Port | Service | Protocol |
|------|---------|----------|
| 22 | SSH | TCP |
| 8188 | ComfyUI | HTTP |
| 9100 | Node Exporter | HTTP |
| 9835 | NVIDIA Metrics | HTTP |
| 10200 | Piper TTS | HTTP |
| 11434 | Ollama | HTTP |

### hydra-storage (192.168.1.244)
| Port | Service | Protocol |
|------|---------|----------|
| 22 | SSH | TCP |
| 53 | AdGuard DNS | UDP/TCP |
| 80/443 | Traefik | HTTP/HTTPS |
| 1883 | Mosquitto MQTT | TCP |
| 2283 | Immich | HTTP |
| 3004 | Uptime Kuma | HTTP |
| 3005 | Firecrawl | HTTP |
| 3003 | Grafana | HTTP |
| 3030 | Perplexica | HTTP |
| 3080 | LibreChat | HTTP |
| 3100 | Loki | HTTP |
| 4000 | LiteLLM | HTTP |
| 5001 | Docling | HTTP |
| 5432 | PostgreSQL | TCP |
| 5678 | n8n | HTTP |
| 6333 | Qdrant HTTP | HTTP |
| 6334 | Qdrant gRPC | gRPC |
| 6379 | Redis | TCP |
| 6767 | Bazarr | HTTP |
| 6969 | Whisparr | HTTP |
| 7474 | Neo4j HTTP | HTTP |
| 7687 | Neo4j Bolt | TCP |
| 7700 | Meilisearch | HTTP |
| 7878 | Radarr | HTTP |
| 8000 | SillyTavern | HTTP |
| 8080 | SearXNG | HTTP |
| 8888 | SearXNG (hydra-stack) | HTTP |
| 8082 | qBittorrent | HTTP |
| 8085 | SABnzbd | HTTP |
| 8123 | Home Assistant | HTTP |
| 8180 | Miniflux | HTTP |
| 8283 | Letta | HTTP |
| 8686 | Lidarr | HTTP |
| 8787 | Readarr | HTTP |
| 8880 | Kokoro TTS | HTTP |
| 8989 | Sonarr | HTTP |
| 9000 | MinIO API | HTTP |
| 9001 | MinIO Console | HTTP |
| 9090 | Prometheus | HTTP |
| 9093 | Alertmanager | HTTP |
| 9100 | Node Exporter | HTTP |
| 9696 | Prowlarr | HTTP |
| 9999 | Stash | HTTP |
| 11434 | Ollama (CPU) | HTTP |
| 32400 | Plex | HTTP |

## Directory Structure (Unraid)

```
/mnt/user/
├── appdata/
│   ├── hydra-stack/           # Main Docker stack
│   │   ├── docker-compose.yml
│   │   ├── .env
│   │   ├── litellm/
│   │   │   └── config.yaml
│   │   ├── prometheus/
│   │   │   ├── prometheus.yml
│   │   │   └── alerts/
│   │   ├── grafana/
│   │   │   └── provisioning/
│   │   └── n8n/
│   ├── media-stack/           # Plex, Stash, Immich
│   ├── download-stack/        # Gluetun, qBit, SABnzbd, *arrs
│   └── homeassistant/
├── models/                    # NFS export to AI nodes
│   ├── exl2/                  # ExLlamaV2 quantized
│   ├── gguf/                  # llama.cpp format
│   ├── embeddings/            # nomic, bge, etc.
│   └── diffusion/             # SD checkpoints, LoRAs
├── databases/                 # Persistent DB storage
│   ├── postgres/
│   ├── qdrant/
│   ├── redis/
│   └── minio/
├── hydra_shared/              # Scratch space, datasets
└── media/                     # Media files
    ├── movies/
    ├── tv/
    ├── music/
    └── stash/
```

## NixOS Essential Configuration

### Enable NVIDIA with Open Kernel Module (Blackwell)
```nix
# /etc/nixos/configuration.nix
{ config, pkgs, ... }:

{
  # Enable NVIDIA
  hardware.nvidia = {
    modesetting.enable = true;
    open = true;  # Required for Blackwell (RTX 50xx)
    nvidiaSettings = true;
    package = config.boot.kernelPackages.nvidiaPackages.beta;
  };

  # Enable Docker with NVIDIA
  virtualisation.docker = {
    enable = true;
    enableNvidia = true;
  };

  # Add user to docker group
  users.users.typhon.extraGroups = [ "docker" ];

  # Enable SSH
  services.openssh.enable = true;

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [ 22 3000 5000 ];
  };
}
```

### Ollama Configuration (hydra-compute)
```nix
# /etc/nixos/configuration.nix (hydra-compute)
services.ollama = {
  enable = true;
  acceleration = "cuda";
  host = "0.0.0.0";
  port = 11434;
  home = "/mnt/models/ollama";
};

# Open firewall port
networking.firewall.allowedTCPPorts = [ 22 8188 11434 ];
```

**Available Ollama Models:**
- `qwen2.5:7b` - General purpose fast model (4.7GB)
- `qwen2.5-coder:7b` - Code assistance (4.7GB)
- `llama3.2:3b` - Lightweight tasks (2.0GB)
- `nomic-embed-text` - Embeddings (274MB)

### PyTorch with CUDA 12.8 (Blackwell Support)
```bash
pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/cu128
```

## Service Credentials

### Core Services
| Service | URL | Username | Password |
|---------|-----|----------|----------|
| Letta | http://192.168.1.244:8283 | - | HydraLetta2024! |
| Grafana | http://192.168.1.244:3003 | admin | HydraGrafana2024! |
| Uptime Kuma | http://192.168.1.244:3004 | admin | HydraKuma2024! |
| Miniflux | http://192.168.1.244:8180 | admin | HydraMiniflux2024! |
| LiteLLM | http://192.168.1.244:4000 | - | sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7 |
| Firecrawl Admin | http://192.168.1.244:3005/admin/HydraFirecrawl2024/queues | - | - |

### Database Credentials
| Service | Host | User | Password |
|---------|------|------|----------|
| PostgreSQL | localhost:5432 | hydra | g9cUyFK6unpMQ8XBmeJNZJPoY6viGg6 |
| Letta-DB (pgvector) | letta-db:5432 | letta | HydraLettaDB2024! |
| Redis | localhost:6379 | - | ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC |

## LiteLLM Routing Configuration

LiteLLM routes requests to multiple backends:

| Model Alias | Backend | Target |
|-------------|---------|--------|
| llama-70b, gpt-4 | TabbyAPI | 192.168.1.250:5000 |
| qwen2.5-7b, gpt-3.5-turbo | Ollama | 192.168.1.203:11434 |
| qwen-coder | Ollama | 192.168.1.203:11434 |
| text-embedding-nomic, text-embedding-ada-002 | Ollama | 192.168.1.203:11434 |

```bash
# Test LiteLLM routing
curl -X POST "http://192.168.1.244:4000/chat/completions" \
  -H "Authorization: Bearer sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5-7b", "messages": [{"role": "user", "content": "Hello"}]}'
```

## Firecrawl Web Scraping

Firecrawl converts web pages to LLM-ready markdown for RAG pipelines.

```bash
# Scrape a URL to markdown
curl -X POST "http://192.168.1.244:3005/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Crawl an entire site
curl -X POST "http://192.168.1.244:3005/v1/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "limit": 10}'
```
