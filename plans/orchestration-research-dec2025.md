# HYDRA ORCHESTRATION RESEARCH
## Strategic Assessment: December 2025

---

## CURRENT STATE

Hydra uses Docker Compose on Unraid with 63 containers across 3 nodes:
- **hydra-storage (Unraid):** 63 containers via Docker
- **hydra-ai (NixOS):** TabbyAPI via systemd
- **hydra-compute (NixOS):** Ollama via systemd, 5 Docker containers

---

## KUBERNETES VS DOCKER COMPOSE

### Research Summary

| Factor | Docker Compose | Kubernetes |
|--------|----------------|------------|
| Complexity | Low | High (steep learning curve) |
| Overhead | Minimal | Significant |
| Scaling | Single node | Multi-node native |
| Learning Value | Moderate | High (enterprise skills) |
| AI/ML Support | Good | Excellent (GPU scheduling) |
| Home Lab Fit | Excellent | Overkill unless learning |

### Key Findings

1. **Docker Compose is optimal for Hydra's current scale**
   - "If you're using the Docker Engine alongside Docker Compose on a resource-constrained single node, there is no better solution"
   - "There is little to no overhead, no additional running processes, or dependencies"

2. **Kubernetes benefits are mainly for learning or scaling**
   - "The most important benefit for Kubernetes in a HomeLab environment is learning about production-grade enterprise solutions"
   - K3s, MicroK8s, Talos make Kubernetes more accessible

3. **Progressive path recommended:**
   - Single Docker → Docker Swarm → Kubernetes
   - "You don't have to jump to Kubernetes first"

### Recommendation for Hydra

**STAY WITH DOCKER COMPOSE** for now because:
- 63 containers on single Unraid host is well within capacity
- EPYC 7663 (56 cores) handles orchestration natively
- No distributed container scheduling needed (AI GPUs are on dedicated nodes)
- Complexity cost of Kubernetes doesn't provide proportional benefit

**CONSIDER K3s LATER** if:
- Scaling to 100+ agents
- Need cross-node container scheduling
- Want GPU time-sharing across nodes

---

## OPENHANDS ASSESSMENT

### What It Is
OpenHands (formerly OpenDevin) is a $18.8M-funded open-source platform for AI coding agents.

### Architecture (V1 SDK)
- **Event-sourced state model** - Reproducible, deterministic execution
- **Sandboxed execution** - Every agent runs in isolated Docker container
- **Modular SDK** - Composable agent, tool, and workspace packages
- **Remote interfaces** - VS Code, VNC, browser integration

### Performance
- **72% SWE-Bench Verified** with Claude Sonnet 4.5
- **67.9% GAIA accuracy** for multi-step reasoning
- Scales from 1 to 1000s of agents

### Relevance to Hydra

| Hydra Feature | OpenHands Equivalent | Assessment |
|---------------|---------------------|------------|
| Self-improvement | Agent SDK | OpenHands is more mature |
| Sandbox execution | Docker sandbox | Similar approach |
| Constitutional safety | Not built-in | Hydra has advantage |
| Memory architecture | Not built-in | Hydra has MIRIX |
| Tool integration | Native (GitHub, Slack, etc.) | OpenHands has more |

### Recommendation

**CONSIDER INTEGRATING OpenHands SDK** for coding-specific tasks:
1. Use OpenHands for code modification tasks
2. Keep Hydra's constitutional safety layer
3. Route through Hydra's memory architecture
4. Benefit from OpenHands' battle-tested execution

**Implementation Path:**
```python
# Example integration
from openhands.core.sdk import AgentController
from hydra_tools.constitution import ConstitutionalEnforcer

class HydraOpenHandsAgent:
    def __init__(self):
        self.openhands = AgentController(model="tabbyapi/midnight-miqu-70b")
        self.constitution = ConstitutionalEnforcer()

    async def execute_coding_task(self, task: str):
        # Constitutional check
        if not await self.constitution.check(task):
            return {"blocked": True, "reason": "Constitutional violation"}

        # Execute via OpenHands
        return await self.openhands.run(task)
```

---

## UNRAID GPU BEST PRACTICES

### Current Setup (Optimal)
- **Arc A380** → Dedicated to Plex transcoding (via Quick Sync Video)
- **RTX 5090 + 4090** → hydra-ai (not on Unraid)
- **2x RTX 5070 Ti** → hydra-compute (not on Unraid)

### Why This Is Correct
1. **GPU passthrough to Docker uses host drivers** - No VFIO binding
2. **Separate compute nodes avoid contention** - AI inference isolated
3. **Arc A380 is perfect for transcoding** - Efficient, low power
4. **EPYC 7663 freed for orchestration** - 56 cores available

### If Adding GPUs to Unraid
If you wanted to add a GPU to Unraid for AI (not recommended currently):
1. Install Nvidia-Driver plugin
2. Get GPU UUID (`nvidia-smi -L`)
3. Add to container: `--runtime=nvidia`, `NVIDIA_VISIBLE_DEVICES=<UUID>`
4. Cannot share GPU between VM and Docker (different driver models)

### Recommendation
**KEEP CURRENT ARCHITECTURE** - AI GPUs on dedicated NixOS nodes is optimal:
- No driver conflicts
- Full VRAM available to inference
- Unraid focuses on storage + orchestration

---

## STRATEGIC RECOMMENDATIONS

### Short Term (Keep)
1. **Docker Compose on Unraid** - Working well, no change needed
2. **Dedicated AI nodes** - NixOS for hydra-ai and hydra-compute
3. **Arc A380 for transcoding** - Optimal use of hardware

### Medium Term (Consider)
1. **OpenHands SDK integration** - For coding agent tasks
2. **Letta for agent memory** - Already deployed, expand usage
3. **Agent scheduler** - AIOS-style (implementing now)

### Long Term (Evaluate)
1. **K3s** - Only if scaling to 100+ agents
2. **NVIDIA GPU Operator** - For Kubernetes GPU scheduling
3. **Temporal** - For durable workflow orchestration

---

## SOURCES

- [Kubernetes vs Docker Compose](https://thenewstack.io/kubernetes-vs-docker-compose/)
- [Docker Compose vs Kubernetes](https://spacelift.io/blog/docker-compose-vs-kubernetes)
- [OpenHands GitHub](https://github.com/OpenHands/OpenHands)
- [OpenHands SDK Paper](https://arxiv.org/html/2511.03690v1)
- [OpenHands Series A](https://www.businesswire.com/news/home/20251118768131/en/)
- [Unraid GPU Docker Guide](https://serverlabs.com.au/blogs/guides/how-to-use-a-gpu-with-unraid-and-docker)
- [Unraid 7.1 Release Notes](https://docs.unraid.net/unraid-os/release-notes/7.1.0/)

---

*Research Date: December 16, 2025*
*Status: Assessment Complete*
