# Rule: Canonical IP Addresses

**Priority:** CRITICAL

## Correct IPs (USE THESE)

| Node | IP | Role |
|------|----|----|
| hydra-ai | 192.168.1.250 | Primary inference, TabbyAPI |
| hydra-compute | 192.168.1.203 | Ollama, ComfyUI |
| hydra-storage | 192.168.1.244 | Docker services, NFS |
| ShaunsDesktop | 192.168.1.167 | Development workstation |

## Deprecated IPs (NEVER USE)

These IPs appear in old files and must be replaced:

- `192.168.1.251` - OLD Ollama host (use 192.168.1.203)
- `192.168.1.175` - OLD compute host (use 192.168.1.203)
- `192.168.1.100` - OLD NFS server (use 192.168.1.244)

## Tailscale IPs (Remote Access)

| Node | Tailscale IP |
|------|-------------|
| hydra-ai | 100.84.120.44 |
| hydra-compute | 100.74.73.44 |
| hydra-storage | 100.111.54.59 |

## Self-Check

If you see any deprecated IP in code, flag it for replacement.
