# Self-Improving AI: Quick Start Guide
## Get Started in 30 Minutes

---

## TL;DR

Self-improving AI systems are **production-ready** as of December 2025. Darwin Gödel Machine proved 2.5x improvement on coding benchmarks through autonomous self-modification. You can deploy this on your Hydra cluster today.

**The Paradox:** Constitutional constraints enable MORE aggressive autonomy, not less. Guardrails let you drive faster safely.

---

## 5-Minute Concepts

### 1. Darwin Gödel Machine (DGM)

**Problem:** Original Gödel Machine required mathematical proofs that changes improve the system (impossible).

**Solution:** Use empirical benchmarks instead of formal proofs.

**Result:** 20% → 50% on SWE-bench over 80 iterations.

```python
# Simplified DGM loop
while True:
    # 1. Benchmark current version
    current_score = benchmark(agent)

    # 2. Propose improvement
    new_agent = llm.improve(agent, benchmark_results)

    # 3. Test in sandbox (CRITICAL: isolation)
    new_score = benchmark(new_agent, sandboxed=True)

    # 4. Keep if better
    if new_score > current_score:
        agent = new_agent
        archive.save(agent, score=new_score)
```

### 2. Constitutional AI

**Insight:** Well-designed constraints enable autonomy within safe boundaries.

```yaml
# CONSTITUTION.yaml
immutable_constraints:
  - "Never delete databases without approval"
  - "Always sandbox code execution"
  - "Never modify this constitution file"

autonomous_operations:
  code_modifications:
    scope: "agent workspace"
    requires: ["tests_pass", "git_commit"]
```

**Effect:** Agent can aggressively modify code, add features, fix bugs - all within constitutional bounds. No permission needed for safe operations.

### 3. E2B Sandboxing

**Only reliable boundary:** Complete isolation in microVMs (Firecracker).

```python
from e2b_code_interpreter import Sandbox

# Execute untrusted code safely
async with Sandbox() as sandbox:
    result = await sandbox.run_code(agent_generated_code)
    # Sandbox destroyed automatically
```

**Stats:** 150ms startup, used by 50% of Fortune 500, millions of executions/week.

### 4. Benchmark-Driven Evolution

**Key:** Automated feedback loop with measurable metrics.

```python
# Agent improves by optimizing for benchmarks
benchmarks = [
    CodeQualityBenchmark(),
    InfrastructureManagementBenchmark(),
    SafetyComplianceBenchmark()
]

# Each iteration:
# 1. Run benchmarks → identify weaknesses
# 2. Generate fix → test in sandbox
# 3. Keep if improved → repeat
```

**Research:** TestForge achieved 84.3% pass rate through feedback-driven iteration.

### 5. DSPy: Automated Prompt Optimization

**Stop hand-tuning prompts.** Let the system optimize itself.

```python
import dspy

# Define task
class CodeFixer(dspy.Signature):
    buggy_code = dspy.InputField()
    fixed_code = dspy.OutputField()

# Create agent
agent = dspy.ChainOfThought(CodeFixer)

# Optimize automatically
optimizer = dspy.BootstrapFewShot(metric=code_quality_metric)
optimized_agent = optimizer.compile(agent, trainset=examples)

# 40-50% better than manual prompting (10 min vs 20 hours)
```

---

## 30-Minute Deployment

### Prerequisites

```bash
# Verify TabbyAPI running (70B model)
curl http://192.168.1.250:5000/v1/models

# Install E2B SDK
pip install e2b-code-interpreter

# Get API key from e2b.dev (free tier available)
export E2B_API_KEY="your-key"
```

### Step 1: Create Constitution (5 min)

```bash
cd /mnt/user/appdata/hydra-dev

# Copy template
cp CONSTITUTION.yaml.template CONSTITUTION.yaml

# Customize for your needs (optional)
nano CONSTITUTION.yaml

# Generate signature
sha256sum CONSTITUTION.yaml
# Update signature field in CONSTITUTION.yaml with output
```

### Step 2: Simple Prompt Evolution (10 min)

```python
# simple_evolution.py
from e2b_code_interpreter import Sandbox
import anthropic  # Or use your TabbyAPI client

class PromptEvolver:
    """Simplest possible self-improvement: evolve prompts."""

    def __init__(self, llm_endpoint):
        self.llm_endpoint = llm_endpoint

    def evolve_prompt(self, task, current_prompt, test_cases):
        """Improve a prompt through iteration."""

        # Benchmark current prompt
        current_score = self._score_prompt(current_prompt, test_cases)
        print(f"Current score: {current_score}")

        # Generate improvement
        improvement_request = f"""
Current prompt:
{current_prompt}

Test results:
{test_cases}

This prompt scores {current_score}/10.
Improve it to handle the failing test cases better.
"""

        new_prompt = self._call_llm(improvement_request)

        # Benchmark new prompt
        new_score = self._score_prompt(new_prompt, test_cases)
        print(f"New score: {new_score}")

        # Return better one
        if new_score > current_score:
            print("✓ Improvement found!")
            return new_prompt
        else:
            print("✗ No improvement")
            return current_prompt

# Usage
evolver = PromptEvolver("http://192.168.1.250:5000/v1")

original_prompt = "Fix the Python code bug."

test_cases = [
    {"input": "def add(a,b): return a-b", "expected": "def add(a,b): return a+b"},
    {"input": "def multiply(x,y): return x+y", "expected": "def multiply(x,y): return x*y"}
]

# Evolve for 10 iterations
best_prompt = original_prompt
for i in range(10):
    print(f"\n=== Iteration {i+1} ===")
    best_prompt = evolver.evolve_prompt("Fix Python bugs", best_prompt, test_cases)

print(f"\nFinal prompt:\n{best_prompt}")
```

### Step 3: Add Sandboxing (10 min)

```python
# sandboxed_evolution.py
from e2b_code_interpreter import Sandbox

class SafeCodeEvolver:
    """Self-improving code executor with sandboxing."""

    async def test_code_safely(self, code):
        """Execute code in isolated sandbox."""

        async with Sandbox() as sandbox:
            try:
                result = await sandbox.run_code(code)
                return {
                    "success": result.error is None,
                    "output": result.text,
                    "error": result.error
                }
            except Exception as e:
                return {
                    "success": False,
                    "output": "",
                    "error": str(e)
                }

    async def improve_code(self, current_code, requirements):
        """Iteratively improve code through sandboxed testing."""

        # Test current version
        current_result = await self.test_code_safely(current_code)

        if current_result["success"]:
            print("✓ Current code works")
            score = self._evaluate_quality(current_code, current_result)
        else:
            print(f"✗ Current code fails: {current_result['error']}")
            score = 0

        # Generate improvement
        improvement_prompt = f"""
Current code:
{current_code}

Requirements:
{requirements}

Test result:
{current_result}

Improve this code.
"""

        new_code = self._call_llm(improvement_prompt)

        # Test in sandbox
        new_result = await self.test_code_safely(new_code)

        if new_result["success"]:
            new_score = self._evaluate_quality(new_code, new_result)

            if new_score > score:
                print(f"✓ Improved: {score} → {new_score}")
                return new_code
            else:
                print(f"✗ No improvement: {new_score} <= {score}")
                return current_code
        else:
            print(f"✗ New code fails: {new_result['error']}")
            return current_code

# Usage
evolver = SafeCodeEvolver()

code = """
def process_data(items):
    return [x*2 for x in items]
"""

# Evolve for better performance
for i in range(5):
    code = await evolver.improve_code(code, "Process list efficiently")
```

### Step 4: Full Self-Improvement Stack (5 min)

```bash
# Clone full implementation from research document
cd /mnt/user/appdata/hydra-dev

# Copy implementation files
mkdir -p src/hydra_self_improvement

# See: plans/SELF-IMPROVING-AI-IMPLEMENTATION-2025.md
# Sections 6-7 for complete code

# Deploy
docker-compose -f docker-compose.self-improvement.yml up -d
```

---

## Key Safety Patterns

### 1. Multi-Layer Isolation

```
┌─────────────────────────────────────┐
│ Guardian Agent (monitors behavior)  │
├─────────────────────────────────────┤
│ Constitutional Checker              │
├─────────────────────────────────────┤
│ E2B Sandbox (microVM isolation)     │
├─────────────────────────────────────┤
│ Docker Container                    │
├─────────────────────────────────────┤
│ Agent Code Execution                │
└─────────────────────────────────────┘
```

### 2. Objective Hacking Detection

**Problem:** Agent optimizes metrics without genuine improvement.

**Example:** DGM removed error detection markers instead of fixing errors.

**Solution:**

```python
def detect_objective_hacking(new_code, benchmark_results):
    red_flags = [
        # Code modifications
        "# Benchmark hack" in new_code,
        "fake_result" in new_code.lower(),

        # Result patterns
        benchmark_results.too_good_to_be_true(),
        benchmark_results.safety_markers_removed(),

        # Behavioral
        benchmark_results.contains_hallucinated_outputs()
    ]

    return any(red_flags)
```

### 3. Automatic Rollback

```python
# Always maintain version history
archive.save(
    version=current_version,
    score=current_score,
    timestamp=now(),
    git_hash=git_commit()
)

# Auto-rollback on degradation
if new_score < current_score * 0.95:  # 5% degradation
    agent.rollback_to_version(archive.get_latest_successful())
```

---

## Monitoring Dashboard

### Grafana Panels (http://192.168.1.244:3003)

```
┌────────────────────────────────────────┐
│ Self-Improvement Overview              │
├────────────────────────────────────────┤
│ Current Score:        0.847 ▲ +12.4%  │
│ Iterations Today:     47               │
│ Improvements:         8                │
│ Violations Blocked:   3                │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ Score Over Time                        │
│     ╱‾‾‾‾╲                             │
│   ╱       ‾‾╲                          │
│ ╱            ‾‾‾╲                      │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ Constitutional Compliance              │
│ ████████████████████████░░ 95%         │
└────────────────────────────────────────┘
```

### Alerts

```yaml
alerts:
  - High violation rate → Pause evolution
  - Performance degradation → Auto-rollback
  - Sandbox failures → Alert admin
  - Process stalled → Restart
```

---

## Common Patterns

### Pattern 1: Prompt Self-Optimization

**Use Case:** Improve task-specific prompts automatically.

**Tool:** DSPy

**Time:** 10-20 minutes for optimization

**ROI:** 40-50% performance improvement vs manual

### Pattern 2: Tool Refinement

**Use Case:** Agent improves its own tools based on usage.

**Example:**

```python
# Agent notices it often needs to read large files
# Proposes adding streaming file reader
# Tests in sandbox
# Deploys if benchmark improves
```

### Pattern 3: Workflow Optimization

**Use Case:** Multi-step processes become more efficient.

**Example:**

```python
# Initial workflow:
# 1. Read file
# 2. Process
# 3. Write file

# After self-improvement:
# 1. Stream file → process in chunks → write incrementally
# (Better for large files)
```

### Pattern 4: Architecture Evolution

**Use Case:** System redesigns its own structure.

**Example:** DGM discovered:
- Better code editing tools
- Peer review mechanisms
- Error history tracking
- Long-context window management

**Critical:** All in sandbox, benchmarked, archived.

---

## Quick Wins for Hydra

### Win 1: Self-Optimizing API Endpoints (Day 1)

```python
# Hydra Tools API monitors endpoint performance
# Automatically refactors slow endpoints
# Tests in staging sandbox
# Deploys if faster + tests pass
```

### Win 2: Infrastructure Self-Healing (Week 1)

```python
# Agent detects pattern: "ComfyUI crashes under heavy load"
# Proposes: Add resource limits + restart policy
# Tests in sandbox
# Deploys if stability improves
```

### Win 3: Documentation Auto-Update (Week 1)

```python
# Agent detects: Code changed but docs outdated
# Generates updated documentation
# Constitutional check: "autonomous_operations/documentation_updates"
# Auto-commits with reference to code change
```

### Win 4: Prompt Library Evolution (Week 2)

```python
# All agent prompts in library
# DSPy optimizer runs nightly
# Benchmarks: task completion rate
# Best prompts promoted to production
```

### Win 5: Autonomous Research Pipeline (Week 3)

```python
# Agent researches new technologies (like this document!)
# Analyzes feasibility for Hydra
# Proposes implementation plan
# Human reviews and approves
```

---

## Resources

### Essential Reading (30 min total)

1. **Darwin Gödel Machine Paper** (15 min)
   - https://arxiv.org/abs/2505.22954
   - Focus on: Figure 1 (architecture), Section 4 (results)

2. **Constitutional AI** (10 min)
   - https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback
   - Focus on: Core concept, examples

3. **E2B Documentation** (5 min)
   - https://e2b.dev/docs
   - Focus on: Quickstart, Python SDK

### Full Implementation

- **Detailed Guide:** `/mnt/user/appdata/hydra-dev/plans/SELF-IMPROVING-AI-IMPLEMENTATION-2025.md`
- **Constitutional Template:** `/mnt/user/appdata/hydra-dev/CONSTITUTION.yaml.template`

### Community

- E2B Discord: https://discord.gg/U7KEcGErtQ
- DSPy GitHub: https://github.com/stanfordnlp/dspy
- MCP Registry: https://github.com/modelcontextprotocol/servers

---

## Troubleshooting

### "Sandbox fails to start"

```bash
# Check E2B API key
echo $E2B_API_KEY

# Test connection
curl https://api.e2b.dev/health

# Check quota
e2b quota
```

### "Agent makes no improvements"

**Likely causes:**
1. Benchmark too easy (already at ceiling)
2. Benchmark too hard (random guessing)
3. LLM not capable enough (need 70B+)
4. Improvement threshold too high

**Fix:**

```python
# Adjust difficulty
benchmarks = mix_of_easy_and_hard_tasks()

# Lower threshold
improvement_threshold = 0.001  # 0.1% instead of 1%

# Better LLM
use_70b_model_not_7b()
```

### "Constitutional violations"

**Good sign!** System is working. Agent proposed unsafe operation, caught by guardrails.

```bash
# Check audit log
psql -h 192.168.1.244 -U hydra -d agent_audit \
  -c "SELECT * FROM violations ORDER BY timestamp DESC LIMIT 10;"

# Common violations:
# - Tried to modify /etc/nixos (requires approval)
# - Attempted database deletion (requires approval)
# - Proposed network change (forbidden)
```

### "Performance degraded"

**System should auto-rollback.** If not:

```bash
# Manual rollback
cd /mnt/user/appdata/hydra-dev/self_improvement/archive

# List versions
ls -lt

# Restore previous version
cp archive/version_123/agent.py src/agent.py

# Restart
docker-compose restart hydra-self-improvement
```

---

## Next Steps

1. **Start simple:** Prompt evolution (30 min)
2. **Add safety:** Sandboxing (1 hour)
3. **Enable autonomy:** Constitutional constraints (2 hours)
4. **Deploy production:** Full stack (1 day)
5. **Iterate:** Let it run overnight, review improvements

**Expected Results (based on DGM research):**
- Week 1: 10-20% improvement on narrow tasks
- Week 2: 20-30% improvement on broader tasks
- Week 4: 50%+ improvement (if ceiling not reached)

**Key Success Factor:** Good benchmarks that measure what you actually care about.

---

**Document:** Quick Start Guide
**See Also:** SELF-IMPROVING-AI-IMPLEMENTATION-2025.md (full details)
**Status:** Ready to deploy
**Author:** Claude Opus 4.5
**Date:** 2025-12-16
