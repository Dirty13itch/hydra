# HYDRA CLUSTER - Claude Code Setup Guide

## What You're Setting Up

You're configuring Claude Code (a command-line AI assistant) to autonomously manage your Hydra cluster. Once set up, you can tell it things like "deploy the databases" and it will SSH to your servers and do it.

**Time required:** ~15 minutes

---

## STEP 1: Install Claude Code

### On Your Windows PC

Open PowerShell (not as admin) and run:

```powershell
npm install -g @anthropic-ai/claude-code
```

**Don't have npm?** Install Node.js first from: https://nodejs.org/ (LTS version)

### Verify Installation

```powershell
claude --version
```

You should see a version number. If you get an error, close and reopen PowerShell.

---

## STEP 2: Create Your Project Folder

Open PowerShell and run these commands ONE AT A TIME:

```powershell
cd ~
```

```powershell
mkdir projects
```

```powershell
cd projects
```

```powershell
mkdir hydra
```

```powershell
cd hydra
```

You're now in: `C:\Users\YourName\projects\hydra\`

---

## STEP 3: Download the Configuration Package

### Option A: Download from Claude.ai (Easiest)

1. In this conversation, look for the download links I'll provide below
2. Download `hydra-claude-code-v2.zip`
3. Extract it into `C:\Users\YourName\projects\hydra\`

### Option B: I'll Create the Files Now

Tell me "create the package" and I'll generate a downloadable zip file.

---

## STEP 4: Verify Your Folder Structure

After extracting, your folder should look like this:

```
C:\Users\YourName\projects\hydra\
│
├── CLAUDE.md                    ← REQUIRED (Claude reads this automatically)
│
├── knowledge\                   ← Technical reference files
│   ├── infrastructure.md
│   ├── inference-stack.md
│   ├── databases.md
│   ├── observability.md
│   ├── automation.md
│   ├── creative-stack.md
│   ├── media-stack.md
│   └── models.md
│
├── .claude\                     ← Custom commands
│   └── commands\
│       └── phase1-deploy.md
│
└── PRPs\                        ← Planning templates
    └── TEMPLATE.md
```

### Quick Check Command

Run this in PowerShell to verify:

```powershell
dir
```

You should see `CLAUDE.md` listed. If not, the files aren't in the right place.

---

## STEP 5: Set Up SSH Access

Claude Code needs to SSH to your servers. You need SSH keys set up.

### Check If You Have SSH Keys

```powershell
dir ~/.ssh/
```

If you see `id_rsa` or `id_ed25519`, you have keys.

### If You DON'T Have Keys

```powershell
ssh-keygen -t ed25519 -C "hydra-claude"
```

Press Enter for all prompts (default location, no passphrase).

### Copy Your Key to Each Server

Run each command and enter your password when prompted:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh typhon@192.168.1.250 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh typhon@192.168.1.203 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@192.168.1.244 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### Test SSH Access (No Password Should Be Needed)

```powershell
ssh typhon@192.168.1.250 "hostname"
```

Should print: `hydra-ai`

```powershell
ssh typhon@192.168.1.203 "hostname"
```

Should print: `hydra-compute`

```powershell
ssh root@192.168.1.244 "hostname"
```

Should print: `Tower` (or your Unraid hostname)

---

## STEP 6: Set GPU Power Limits (Important!)

Your UPS can't handle full GPU power. Set limits now:

```powershell
ssh typhon@192.168.1.250 "sudo nvidia-smi -pl 450 -i 0 && sudo nvidia-smi -pl 300 -i 1"
```

You should see confirmation for both GPUs.

---

## STEP 7: Start Claude Code

Make sure you're in your project folder:

```powershell
cd ~/projects/hydra
```

Start Claude Code:

```powershell
claude
```

You should see Claude Code start up. It automatically reads CLAUDE.md.

---

## STEP 8: Test It Works

In the Claude Code prompt, type:

```
Check the status of hydra-ai. SSH in and run nvidia-smi, then report the GPU status.
```

Claude Code should:
1. SSH to 192.168.1.250
2. Run nvidia-smi
3. Show you the GPU status

If this works, you're ready!

---

## STEP 9: Deploy Phase 1 (When Ready)

When you want to deploy the foundation layer (databases, monitoring, etc.), type:

```
Deploy Phase 1 foundation layer to hydra-storage. Create all required directories, docker-compose.yml, and config files. Deploy PostgreSQL, Redis, Qdrant, Prometheus, Grafana, Uptime Kuma, and LiteLLM. Verify each service is healthy. Report final status.
```

Claude Code will:
1. SSH to hydra-storage
2. Create all directories
3. Create docker-compose.yml with all services
4. Create config files (prometheus.yml, etc.)
5. Run `docker-compose up -d`
6. Check health of each service
7. Report what worked and what didn't

---

## Troubleshooting

### "claude is not recognized"

Node.js isn't in your PATH. Close PowerShell, reopen, try again. Or reinstall Node.js.

### "Permission denied" on SSH

Your SSH key isn't copied to the server. Redo Step 5.

### "CLAUDE.md not found"

You're not in the right directory. Run:
```powershell
cd ~/projects/hydra
dir
```
Make sure CLAUDE.md is listed.

### Claude Code seems confused about the project

Make sure CLAUDE.md is in the ROOT of your project folder, not in a subfolder.

---

## Quick Reference

| What | Command |
|------|---------|
| Start Claude Code | `cd ~/projects/hydra && claude` |
| Check GPU status | Ask: "Check GPU status on hydra-ai" |
| Deploy Phase 1 | Ask: "Deploy Phase 1 foundation layer" |
| See running containers | Ask: "Show running containers on hydra-storage" |
| Exit Claude Code | Type `exit` or press Ctrl+C |

---

## What's In Each Phase

| Phase | Services | Days |
|-------|----------|------|
| **Phase 1** | PostgreSQL, Redis, Qdrant, Prometheus, Grafana, LiteLLM | 1-3 |
| **Phase 2** | n8n, SearXNG, Firecrawl, Miniflux | 4-7 |
| **Phase 3** | ComfyUI, SillyTavern, TTS | 8-10 |
| **Phase 4** | VPN, qBittorrent, *Arr stack | 11-14 |
| **Phase 5** | Home Assistant, AdGuard | 15-17 |
| **Phase 6** | Agent frameworks, MCP | 18-21+ |

---

## Need Help?

If something doesn't work, tell Claude Code:

```
Something went wrong with [describe issue]. Check the logs and help me fix it.
```

Or come back to this Claude.ai conversation and ask me!
