# Hydra Autonomous Caretaker Architecture
## World-Class Expert System for 24/7 Autonomous Operation

> **Vision**: An autonomous AI system that operates as an expert-level engineer, maintaining and improving the Hydra cluster without human intervention, capable of handling any request without restrictions.

---

## Executive Summary

The Hydra Autonomous Caretaker is a multi-agent system combining:
- **Expert coding capabilities** (Aider + best-in-class models)
- **System administration** (Docker, Unraid, NixOS management)
- **Document understanding** (RAG + knowledge base)
- **Self-improvement** (can modify Hydra itself)
- **Unrestricted operation** (local models without content filters)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         HYDRA AUTONOMOUS CARETAKER                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        ORCHESTRATION LAYER                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │  │
│  │  │ Task Queue   │  │ Task Router  │  │ Priority     │                  │  │
│  │  │ (Persistent) │→│ (Capability  │→│ Manager      │                  │  │
│  │  │              │  │  Matching)   │  │              │                  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│          ┌─────────────────────────┼─────────────────────────┐               │
│          ▼                         ▼                         ▼               │
│  ┌───────────────┐  ┌───────────────────────┐  ┌───────────────────────┐    │
│  │ CODING AGENTS │  │ SYSADMIN AGENTS       │  │ REASONING AGENTS      │    │
│  ├───────────────┤  ├───────────────────────┤  ├───────────────────────┤    │
│  │ • Aider+Tabby │  │ • Docker Manager      │  │ • Dolphin (uncensored)│    │
│  │ • Aider+Ollama│  │ • Unraid Controller   │  │ • DeepSeek-R1         │    │
│  │ • OpenHands   │  │ • NixOS Configurator  │  │ • Research Agent      │    │
│  │ • Claude Code │  │ • SSH Executor        │  │ • Planning Agent      │    │
│  └───────────────┘  └───────────────────────┘  └───────────────────────┘    │
│          │                         │                         │               │
│          └─────────────────────────┼─────────────────────────┘               │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        EXECUTION LAYER                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │ Shell/SSH    │  │ File System  │  │ API Client   │  │ Git        │  │  │
│  │  │ Executor     │  │ Manager      │  │ (Hydra APIs) │  │ Operations │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        SAFETY LAYER                                     │  │
│  │  • Constitutional constraints (IMMUTABLE)                               │  │
│  │  • Audit logging (all actions recorded)                                 │  │
│  │  • Rollback capability (git, snapshots)                                 │  │
│  │  • Human escalation triggers                                            │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│  HYDRA-AI     │          │ HYDRA-COMPUTE │          │ HYDRA-STORAGE │
│  192.168.1.250│          │ 192.168.1.203 │          │ 192.168.1.244 │
├───────────────┤          ├───────────────┤          ├───────────────┤
│ • TabbyAPI    │          │ • Ollama      │          │ • Docker      │
│ • RTX 5090    │          │ • ComfyUI     │          │ • APIs        │
│ • RTX 4090    │          │ • RTX 5070Ti  │          │ • Databases   │
└───────────────┘          └───────────────┘          └───────────────┘
```

---

## Agent Specializations

### 1. Coding Agents

#### Primary: Aider + TabbyAPI (hydra-ai)
```yaml
agent_id: aider-tabby-primary
model: devstral-small-2 (24B) OR deepseek-coder-33b
capabilities:
  - code_generation
  - code_editing
  - refactoring
  - multi_file_changes
  - git_integration
  - test_writing
cost: FREE (local)
latency: ~5-10s per response
best_for: "Complex multi-file refactoring, architecture changes"
```

#### Secondary: Aider + Ollama (hydra-compute)
```yaml
agent_id: aider-ollama-secondary
model: qwen2.5-coder:32b
capabilities:
  - code_generation
  - code_editing
  - quick_fixes
cost: FREE (local)
latency: ~3-8s per response
best_for: "Quick code changes, redundancy when hydra-ai is loaded"
```

#### Escalation: Claude Code (API)
```yaml
agent_id: claude-code-escalation
model: claude-sonnet-4
capabilities:
  - complex_reasoning
  - architecture_design
  - code_review
  - documentation
cost: $$ (API calls)
best_for: "Problems too complex for local models, critical changes"
```

### 2. System Administration Agents

#### Docker Manager
```yaml
agent_id: docker-manager
type: specialized_executor
capabilities:
  - container_lifecycle (start, stop, restart, remove)
  - image_management (build, pull, push)
  - compose_operations
  - log_analysis
  - resource_monitoring
execution_context: SSH to hydra-storage
commands:
  - "docker ps/logs/exec/build"
  - "docker-compose up/down/restart"
```

#### Unraid Controller
```yaml
agent_id: unraid-controller
type: specialized_executor
capabilities:
  - array_status
  - share_management
  - docker_management (via Unraid UI API)
  - plugin_management
  - disk_operations
execution_context: Unraid CLI + API
safety:
  - NEVER modify array without human approval
  - NEVER delete shares
```

#### NixOS Configurator
```yaml
agent_id: nixos-configurator
type: specialized_executor
target_nodes:
  - hydra-ai (192.168.1.250)
  - hydra-compute (192.168.1.203)
capabilities:
  - configuration_editing (/etc/nixos/configuration.nix)
  - rebuild_dry_run (nixos-rebuild dry-build)
  - rebuild_switch (nixos-rebuild switch)
  - rollback (nixos-rebuild --rollback)
  - package_search (nix search)
safety:
  - ALWAYS dry-run before switch
  - ALWAYS verify rollback path
  - Document changes in memory
```

### 3. Reasoning Agents (Uncensored)

#### Primary Uncensored: Dolphin-Mixtral
```yaml
agent_id: dolphin-uncensored
model: cognitivecomputations/dolphin-2.9-mixtral-8x22b
# OR: dolphin-2.9-llama3.1-70b for smaller VRAM
capabilities:
  - unrestricted_reasoning
  - creative_content
  - adult_content (for Empire of Broken Queens, game library)
  - roleplay
  - uncensored_assistance
why: "Specifically fine-tuned without content restrictions"
notes: "Dolphin models are trained to follow all instructions"
```

#### DeepSeek-R1 (Reasoning)
```yaml
agent_id: deepseek-r1
model: deepseek-r1:70b OR deepseek-r1-distill:32b
capabilities:
  - chain_of_thought_reasoning
  - complex_problem_solving
  - architecture_design
  - planning
why: "Exceptional reasoning, less restricted than Western models"
```

#### Research Agent
```yaml
agent_id: research-agent
model: any (configurable)
capabilities:
  - web_search
  - document_analysis
  - knowledge_synthesis
  - trend_identification
tools:
  - WebSearch
  - WebFetch
  - Qdrant (vector search)
  - Knowledge base access
```

---

## Execution Capabilities

### Shell/SSH Executor
```python
class SSHExecutor:
    """Execute commands on cluster nodes via SSH."""

    nodes = {
        "hydra-ai": {"host": "192.168.1.250", "user": "typhon"},
        "hydra-compute": {"host": "192.168.1.203", "user": "typhon"},
        "hydra-storage": {"host": "192.168.1.244", "user": "root"},
    }

    async def execute(self, node: str, command: str) -> str:
        """Execute command on node, return output."""
        # Uses SSH key authentication
        pass

    async def execute_docker(self, container: str, command: str) -> str:
        """Execute command inside Docker container."""
        pass
```

### File System Manager
```python
class FileSystemManager:
    """Manage files across the cluster."""

    async def read_file(self, path: str) -> str:
        """Read file contents."""
        pass

    async def write_file(self, path: str, content: str) -> None:
        """Write file (with backup)."""
        pass

    async def edit_file(self, path: str, old: str, new: str) -> None:
        """Edit file in place."""
        pass
```

### Git Operations
```python
class GitOperator:
    """Git operations with safety checks."""

    async def commit(self, message: str, files: List[str]) -> str:
        """Create commit (never pushes without approval)."""
        pass

    async def create_branch(self, name: str) -> str:
        """Create feature branch for changes."""
        pass

    async def diff(self) -> str:
        """Show current changes."""
        pass
```

---

## Model Recommendations

### For Uncensored Operation

| Model | Size | VRAM | Source | Notes |
|-------|------|------|--------|-------|
| dolphin-2.9-mixtral-8x22b | 140B MoE | ~80GB | HuggingFace | Best uncensored, needs both GPUs |
| dolphin-2.9-llama3.1-70b | 70B | ~42GB | HuggingFace | Fits on hydra-ai |
| dolphin-2.9-mistral-7b | 7B | ~8GB | Ollama | Fast, for quick uncensored chat |
| nous-hermes-2-mixtral | 47B MoE | ~30GB | Ollama | Good balance |

### For Expert Coding

| Model | Size | Best For | Node |
|-------|------|----------|------|
| devstral-small-2 | 24B | General coding | hydra-ai |
| deepseek-coder-v2 | 33B | Complex coding | hydra-ai |
| qwen2.5-coder | 32B | Fast coding | hydra-compute |
| codestral-25.08 | 22B | Low-latency completion | hydra-compute |

### For Complex Reasoning

| Model | Size | Best For | Node |
|-------|------|----------|------|
| deepseek-r1 | 70B | Complex problems | hydra-ai |
| deepseek-r1-distill | 32B | Reasoning on lighter VRAM | hydra-compute |
| qwen2.5:72b | 72B | General reasoning | hydra-ai |

---

## Autonomous Operation Modes

### 1. Maintenance Mode (24/7 Background)
```yaml
schedule: "Continuous"
triggers:
  - Health check failures
  - Resource alerts
  - Scheduled maintenance windows
actions:
  - Monitor container health
  - Restart failed services
  - Clean up disk space
  - Update container images (non-breaking)
  - Run security scans
```

### 2. Improvement Mode (Proactive)
```yaml
schedule: "When idle + low priority"
triggers:
  - User requests in queue
  - Identified gaps
  - Research findings
actions:
  - Implement feature requests
  - Optimize performance
  - Update documentation
  - Refactor code
  - Add tests
```

### 3. Research Mode (Background)
```yaml
schedule: "Continuous background"
triggers:
  - New technologies detected
  - User interests
  - System needs
actions:
  - Monitor tech news
  - Evaluate new tools
  - Prototype integrations
  - Update knowledge base
```

### 4. Interactive Mode (On-Demand)
```yaml
schedule: "User-initiated"
triggers:
  - User message/request
  - API call
  - Command Center action
actions:
  - Full agent capabilities
  - Unrestricted assistance
  - Complex multi-step tasks
```

---

## Safety & Constraints

### Constitutional Constraints (IMMUTABLE)
```yaml
never:
  - Delete databases without human approval
  - Modify network/firewall configuration
  - Disable authentication
  - Expose secrets
  - Push to main without approval
  - Run destructive commands without confirmation

always:
  - Log all actions
  - Create backups before destructive changes
  - Dry-run configuration changes
  - Verify rollback paths
  - Escalate to human for uncertainty
```

### Audit Trail
```python
class AuditLogger:
    """Log all autonomous actions for accountability."""

    def log_action(self, action: dict):
        """Log action with timestamp, agent, command, result."""
        # Stored in: /data/audit/autonomous_actions.jsonl
        pass

    def log_decision(self, decision: dict):
        """Log decision with reasoning."""
        pass
```

---

## Implementation Phases

### Phase 1: Core Agents (Week 1)
- [x] Aider integration wrapper
- [x] Agent orchestrator API
- [ ] Install Aider in hydra-tools container
- [ ] Test Aider + TabbyAPI connection
- [ ] Test Aider + Ollama connection

### Phase 2: System Agents (Week 2)
- [ ] SSH executor for remote commands
- [ ] Docker manager agent
- [ ] File system manager
- [ ] Git operator

### Phase 3: Uncensored Models (Week 2)
- [ ] Download Dolphin model to TabbyAPI
- [ ] Configure uncensored agent
- [ ] Test unrestricted operation

### Phase 4: Autonomous Loop (Week 3)
- [ ] Task queue (persistent)
- [ ] Priority manager
- [ ] Scheduling system
- [ ] Self-triggered maintenance

### Phase 5: Full Integration (Week 4)
- [ ] Command Center UI for agent control
- [ ] Cost tracking dashboard
- [ ] Performance metrics
- [ ] User preference learning

---

## Quick Start Commands

### Install Aider in Container
```bash
# Add to Dockerfile or run in container
pip install aider-chat

# Or add to requirements.txt
aider-chat>=0.42.0
```

### Download Dolphin Model (Uncensored)
```bash
# On hydra-ai via TabbyAPI
# Download from HuggingFace: cognitivecomputations/dolphin-2.9-llama3.1-70b

# Or via Ollama on hydra-compute
ssh typhon@192.168.1.203
ollama pull dolphin-mixtral:8x7b
```

### Test Agent Orchestrator
```bash
# List available agents
curl http://192.168.1.244:8700/agents/

# Check agent health
curl http://192.168.1.244:8700/agents/health

# Execute a task
curl -X POST http://192.168.1.244:8700/agents/execute \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Add a docstring to the main function",
    "files": ["/mnt/user/appdata/hydra-dev/src/hydra_tools/api.py"],
    "prefer_local": true
  }'
```

---

## User Vision Alignment

The caretaker is designed to evolve toward **Shaun's vision**:

1. **70B+ models at interactive speeds** → Optimize inference, model routing
2. **24/7 autonomous operation** → Self-maintaining, self-healing
3. **Self-improving capabilities** → Can modify its own code
4. **Perfect reliability** → Redundancy, monitoring, auto-recovery
5. **Unrestricted assistance** → No arbitrary content limits
6. **Expert in all domains** → Specialized agents for each area

The system learns and adapts through:
- `memory_v2/user.yaml` - Tracks preferences
- `memory_v2/patterns.yaml` - Learns what works
- `memory_v2/decisions.yaml` - Records rationale

---

*Architecture Version: 1.0*
*Created: December 18, 2025*
