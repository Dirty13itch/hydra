# Hydra: Full File Analysis & Reconciliation

_Generated: 2025-12-13T05:50:49.263269_

This report analyzes every file inside the attached archives:

- **projects.zip** → group `projects`: **286 files**, total **0.0MB**
- **hydra-control-plane-frontend.zip** → group `hydra-control-plane-frontend`: **10 files**, total **0.0KB**
- **other.zip** → group `other`: **17 files**, total **0.2KB**
- **.claude.zip** → group `dotclaude`: **381 files**, total **0.1MB**

It also cross-checks against `Hydra_Snapshot_20251212_222505.txt` (your live cluster snapshot).

## Executive summary (tell-it-like-it-is)

1. **Your live cluster is real and coherent**: hydra-storage is the “services backbone”, hydra-compute is the GPU workload runner (Ollama/ComfyUI/whisper), hydra-ai is the “big inference” box (TabbyAPI).
2. **Your docs and code are drifting in a few key places**: the *big one* is old inference URLs pointing at **192.168.1.251** and old compute URLs pointing at **192.168.1.175**—those need to be eradicated or centrally aliased.
3. **You have sensitive material in plain text** inside the archives (most critically: Claude OAuth credentials and at least one DB credential in a docker-compose). Treat these zips as sensitive; don’t commit them; rotate what matters.
4. **You have three competing “control plane” concepts** in the files: Hydra MCP server (cluster control API), Hydra UI (cluster dashboard), and “Empire Control Plane” (project-specific orchestration API). They need explicit naming boundaries so your future self doesn’t get gaslit by your own repo.

## Live cluster: current ground truth (from snapshot)

### Nodes

- **hydra-compute (NixOS)**: SSH 22, ComfyUI 8188, GPU exporter 9835, Ollama 11434, node-exporter 9100, whisper-asr 9002.
- **hydra-ai (NixOS)**: SSH 22, TabbyAPI 5000/5001, dcgm-exporter 9835, node-exporter 9100.
- **hydra-storage (Unraid)**: 112-core EPYC box running **60 containers** (service backbone).
- **ShaunsDesktop (Windows 11 Pro)**: desktop workstation on **192.168.1.167**.

### Notable runtime wiring

- `hydra-compute` mounts the models share from `hydra-storage` via NFS (`/mnt/models`).
- `hydra-compute` runs 3 docker-compose stacks: `comfyui`, `kohya_docker`, `whisper-asr`.
- `hydra-ai` has multiple IPs (192.168.1.250 plus additional 192.168.1.205 and 192.168.1.50). This matters for binding/advertising services.

## Archive analysis

### 1) projects.zip (group `projects`)

This is the *real* repo: `projects/projects/hydra/` contains the Hydra cluster docs, the MCP server code, the Next.js UI, and a full project called **Empire of Broken Queens**.

**Top-level contents (hydra repo)**
- `.claude/` (2 files)
- `config/` (2 files)
- `Empire of Broken Queens/` (34 files)
- `hydra-claude-code-v2/` (0 files)
- `knowledge/` (9 files)
- `mcp/` (6 files)
- `n8n-workflows/` (1 files)
- `scripts/` (5 files)
- `temp/` (3 files)
- `ui/` (41 files)
- `{knowledge,.claude/` (0 files)
- `.mcp.json` (233B)
- `alert_rules.yml` (0.0KB)
- `api_fixed.ts` (0.0KB)
- `ARCHITECTURE.md` (0.1KB)
- `grafana-ai-dashboard.json` (0.0KB)
- `hydra-docs.tar.gz` (0.0KB)
- `hydra-fun-stack-merge.tar.gz` (0.0KB)
- `HYDRA-MASTER-SYNTHESIS.md` (0.0KB)
- `HYDRA-SETUP-GUIDE.md` (0.0KB)
- `import_knowledge.ps1` (0.0KB)
- `import_knowledge_to_letta.py` (0.0KB)
- `LEARNINGS.md` (0.0KB)
- `mcp_server_original.py` (0.0KB)
- `mcp_server_websocket.py` (0.0KB)
- `model_management.py` (0.0KB)
- `n8n_auto_recovery_workflow.json` (0.0KB)
- `page_fix.tsx` (0.0KB)
- `patch_api_auth.py` (0.0KB)
- `patch_discord_webhook.py` (0.0KB)
- `patch_gpu_metrics.py` (0.0KB)
- `patch_inference_tracking.py` (0.0KB)
- `patch_litellm_health.py` (0.0KB)
- `patch_mcp.py` (0.0KB)
- `patch_models.py` (0.0KB)
- `patch_proxy_endpoints.py` (0.0KB)
- `patch_rag_pipeline.py` (0.0KB)
- `README.md` (0.0KB)
- `ROADMAP.md` (0.0KB)
- `STATE.json` (0.0KB)
- `storage_endpoint.py` (0.0KB)
- `ui_api_fixed.ts` (0.0KB)
- `update_api.py` (0.0KB)
- `VISION.md` (0.0KB)

**Key components inside `hydra/`**
- **MCP server**: `hydra/mcp/mcp_server.py` (FastAPI) + related variants. This is the cluster control API layer that bridges metrics, docker, and safety-confirmed actions.
- **UI**: `hydra/ui/` is a Next.js app intended as a Hydra control plane dashboard.
- **Monitoring configs**: Prometheus/Grafana/Alertmanager rules and dashboards (`alert_rules.yml`, `grafana-*-dashboard.json`, `config/alertmanager.yml`).
- **Automation**: n8n workflow export `n8n-workflows/hydra-auto-recovery-workflow.json` and an additional workflow file at repo root.
- **Project: Empire of Broken Queens**: contains its own FastAPI “control plane” (`Empire of Broken Queens/api/main.py`) and compose to deploy it.

**Red flags / drift found in this repo**
- **Hardcoded old inference host:** several UI/API files reference Ollama at `http://192.168.1.251:11434` (but live Ollama is on hydra-compute at 192.168.1.203:11434).
- **Old compute host:** `model_management.py` + `patch_models.py` still reference `192.168.1.175` for Ollama.
- **Plaintext DB credential:** `Empire of Broken Queens/api/docker-compose.yml` contains a `postgresql://user:password@...` URI. Move it into Vaultwarden/SOPS and rotate the password.
- **Stray mistaken directories:** `hydra/{knowledge,.claude/` and `hydra/{knowledge,.claude/commands,PRPs,agents,examples}/` look like accidental brace-expansion artifacts and should be deleted.

### 2) hydra-control-plane-frontend.zip (group `hydra-control-plane-frontend`)

This is a tiny Next.js skeleton (10 files). It overlaps conceptually with `projects/projects/hydra/ui/`, but has far less code. Treat as **prototype/legacy** unless you know it’s deployed somewhere.

### 3) other.zip (group `other`)

This looks like an earlier experimental bundle:

- `hydra-control-plane-backend-main.py`: FastAPI backend that queries Prometheus for cluster metrics.
- `hydra-task-hub-main.py`: FastAPI “task hub” for autonomous job routing.
- `hydra-control-plane-MASTER_BLUEPRINT.md`: conceptual blueprint for the control plane.
- Caddyfile + dashboard JSONs + scripts.

It overlaps with the MCP server direction, but it’s not what your snapshot shows running. So: **good reference material, not canonical runtime**.

### 4) .claude.zip (group `dotclaude`)

This is your local Claude Code brain-dump: settings, history, transcripts, and a credentials file.

- ✅ It contains valuable ops context (`.claude/CLAUDE.md`) that accurately describes your node roles/IPs.
- ⚠️ It also contains high-sensitivity material: `.claude/.credentials.json` plus many transcripts/file-history items that may include tokens/URLs. Treat it like a password vault export.


## Reconciliation: what should be treated as canonical

Here’s the clean, low-confusion split that matches your snapshot reality:

1. **Canonical infra & cluster docs/code:** `projects/projects/hydra/` (especially `ARCHITECTURE.md`, `knowledge/`, `mcp/`, and monitoring config).
2. **Canonical runtime truth:** `Hydra_Snapshot_20251212_222505.txt` (regenerate anytime; this is your reality check).
3. **Personal operator context:** `.claude/` (keep private; do not commit).
4. **Legacy/prototypes:** `other.zip` + `hydra-control-plane-frontend.zip` (keep, but quarantine into `/legacy/` if you fold them into the repo).

## Concrete drift list (what I would change first)

### A) Fix the two suspicious hardcoded service IPs

- Replace `192.168.1.251` (old Ollama host) → `192.168.1.203` (hydra-compute).
- Replace `192.168.1.175` (old compute) → `192.168.1.203`.

### B) Stop baking IPs into code at all

Use one of these patterns (in descending order of sanity):

1. **DNS names** (AdGuard Home is already on hydra-storage): `ollama.hydra.lan`, `tabby.hydra.lan`, `mcp.hydra.lan`, etc.
2. **Environment variables** with `.env` files stored in Vaultwarden/SOPS.
3. **Single `hydra.config.json`** consumed by UI + scripts, generated from NixOS + Unraid compose.

### C) Secrets hygiene

- Move DB passwords, API keys, and tokens out of repo/archives.
- Rotate anything that looks like a real credential (especially OAuth tokens from `.claude/.credentials.json`).


## Quantitative findings

- Total files analyzed in zips: **694**
- Total size analyzed: **0.1MB**
- Files with at least one `http(s)://<ip>` URL: **179**
- Files referencing the suspicious URL IPs (192.168.1.251 / 192.168.1.175): **14**
- Files flagged for potential secrets (pattern match): **76** (mostly inside `.claude/`)

## Appendices

### Appendix A: Full per-file manifest

- See `HYDRA_FILE_MANIFEST.csv` for **every file** with size, category, short summary, IP/URL references, and secret-flag markers.

### Appendix B: Files that reference the old Ollama host (192.168.1.251)

- `projects/projects/hydra/patch_proxy_endpoints.py`
- `projects/projects/hydra/ui/src/components/ServiceList.tsx`
- `projects/projects/hydra/ui/src/lib/api.ts`

### Appendix C: Files that reference the old compute host (192.168.1.175)

- `projects/projects/hydra/model_management.py`
- `projects/projects/hydra/patch_models.py`