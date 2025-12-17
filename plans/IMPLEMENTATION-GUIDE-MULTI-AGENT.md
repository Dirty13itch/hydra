# HYDRA MULTI-AGENT IMPLEMENTATION GUIDE
## Concrete Architecture Design for 24/7 Autonomous Operation

---

## QUICK REFERENCE

**Purpose:** This guide provides the concrete implementation architecture for Hydra's multi-agent system, synthesizing research from:
- `hydra-bleeding-edge-research-dec2025.md` (technology survey)
- `multi-agent-orchestration-research-dec2025.md` (deep patterns)

**Target:** Move from research to implementation with specific code patterns, service configurations, and deployment steps.

---

## ARCHITECTURE OVERVIEW

### The Hydra Multi-Agent Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYDRA ORCHESTRATOR                           │
│  (LangGraph-based, runs on hydra-storage:8700)                 │
│                                                                 │
│  ┌────────────┬────────────┬────────────┬────────────────┐    │
│  │ Research   │ Development│ Infra      │ Self-Improve   │    │
│  │ Crew       │ Crew       │ Crew       │ Agent          │    │
│  └────────────┴────────────┴────────────┴────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          ↓ Memory Layer ↓
┌─────────────────────────────────────────────────────────────────┐
│                    LETTA MEMORY SERVICE                         │
│  (http://192.168.1.244:8000)                                   │
│                                                                 │
│  ┌────────────────┬─────────────────┬────────────────────┐    │
│  │ Core Memory    │ Archival Memory │ Recall Memory      │    │
│  │ (2k chars)     │ (Vector DB)     │ (Full History)     │    │
│  └────────────────┴─────────────────┴────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          ↓ Tool Layer ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MCP TOOL SERVERS                             │
│                                                                 │
│  filesystem-mcp  git-mcp  github-mcp  docker-mcp  postgres-mcp │
│  comfyui-mcp  n8n-mcp  home-assistant-mcp  qdrant-mcp         │
└─────────────────────────────────────────────────────────────────┘
                          ↓ Inference ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INFERENCE LAYER                              │
│                                                                 │
│  hydra-ai (TabbyAPI)    │  hydra-compute (Ollama)              │
│  70B-405B models        │  Vision models                       │
│  192.168.1.250:5000     │  192.168.1.203:11434                │
└─────────────────────────────────────────────────────────────────┘
```

---

## SERVICE DEPLOYMENTS

### 1. Letta Memory Service

**Location:** hydra-storage (192.168.1.244)
**Port:** 8000
**Database:** PostgreSQL + Qdrant

**Docker Compose:**

```yaml
# /mnt/user/appdata/letta/docker-compose.yml
version: '3.8'

services:
  letta:
    image: letta/letta:latest
    container_name: letta
    ports:
      - "8000:8000"
    environment:
      # PostgreSQL for persistent data
      - LETTA_PG_HOST=192.168.1.244
      - LETTA_PG_PORT=5432
      - LETTA_PG_DB=letta
      - LETTA_PG_USER=letta
      - LETTA_PG_PASSWORD=${LETTA_PG_PASSWORD}

      # Qdrant for vector storage
      - LETTA_QDRANT_HOST=192.168.1.244
      - LETTA_QDRANT_PORT=6333
      - LETTA_QDRANT_API_KEY=${QDRANT_API_KEY}

      # LLM configuration
      - LETTA_LLM_ENDPOINT=http://192.168.1.244:4000/v1
      - LETTA_LLM_MODEL=claude-sonnet-4.5
      - LETTA_EMBEDDING_ENDPOINT=http://192.168.1.244:4000/v1
      - LETTA_EMBEDDING_MODEL=text-embedding-3-large

    volumes:
      - /mnt/user/appdata/letta/data:/data
      - /mnt/user/appdata/letta/config:/config

    restart: unless-stopped

    networks:
      - hydra-network

networks:
  hydra-network:
    external: true
```

**Initialization:**

```bash
# Create database
docker exec -it postgres psql -U postgres -c "CREATE DATABASE letta;"
docker exec -it postgres psql -U postgres -c "CREATE USER letta WITH PASSWORD 'secure_password';"
docker exec -it postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE letta TO letta;"

# Create Qdrant collection
curl -X PUT http://192.168.1.244:6333/collections/letta_archival \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 3072,
      "distance": "Cosine"
    }
  }'

# Start Letta
cd /mnt/user/appdata/letta
docker-compose up -d

# Verify
curl http://192.168.1.244:8000/health
```

### 2. MCP Server Hub

**Location:** hydra-storage (192.168.1.244)
**Ports:** 9000-9010 (one per MCP server)

**Docker Compose:**

```yaml
# /mnt/user/appdata/mcp-servers/docker-compose.yml
version: '3.8'

services:
  mcp-filesystem:
    image: modelcontextprotocol/filesystem-server:latest
    container_name: mcp-filesystem
    ports:
      - "9000:9000"
    volumes:
      - /mnt/user/appdata/hydra-dev:/workspace
    environment:
      - MCP_ALLOWED_PATHS=/workspace
    restart: unless-stopped

  mcp-git:
    image: modelcontextprotocol/git-server:latest
    container_name: mcp-git
    ports:
      - "9001:9001"
    volumes:
      - /mnt/user/appdata/hydra-dev:/repos
      - /root/.ssh:/root/.ssh:ro
    restart: unless-stopped

  mcp-github:
    image: modelcontextprotocol/github-server:latest
    container_name: mcp-github
    ports:
      - "9002:9002"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    restart: unless-stopped

  mcp-docker:
    image: modelcontextprotocol/docker-server:latest
    container_name: mcp-docker
    ports:
      - "9003:9003"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped

  mcp-postgres:
    image: modelcontextprotocol/postgres-server:latest
    container_name: mcp-postgres
    ports:
      - "9004:9004"
    environment:
      - PG_CONNECTION_STRING=postgresql://hydra:${PG_PASSWORD}@192.168.1.244:5432/hydra
    restart: unless-stopped

  mcp-qdrant:
    image: modelcontextprotocol/qdrant-server:latest
    container_name: mcp-qdrant
    ports:
      - "9005:9005"
    environment:
      - QDRANT_URL=http://192.168.1.244:6333
      - QDRANT_API_KEY=${QDRANT_API_KEY}
    restart: unless-stopped

networks:
  default:
    name: hydra-network
    external: true
```

**Custom MCP Servers (to build):**

```python
# /mnt/user/appdata/mcp-servers/custom/comfyui_mcp.py
"""
MCP server for ComfyUI integration
Runs on hydra-compute via SSH
"""

from mcp import Server, Tool, Resource
import asyncssh
import json

class ComfyUIMCPServer(Server):
    def __init__(self):
        super().__init__(name="comfyui")
        self.comfy_host = "192.168.1.203"
        self.comfy_port = 8188

    @Tool(
        name="generate_image",
        description="Generate image using ComfyUI workflow"
    )
    async def generate_image(self, workflow: dict, checkpoint: str) -> dict:
        """Execute ComfyUI workflow"""

        async with asyncssh.connect(self.comfy_host, username='typhon') as conn:
            # Upload workflow
            await conn.run(f'echo \'{json.dumps(workflow)}\' > /tmp/workflow.json')

            # Execute
            result = await conn.run(
                f'cd /opt/ComfyUI && python main.py --input /tmp/workflow.json'
            )

            return {
                'status': 'success',
                'output': result.stdout,
                'images': self.parse_output_images(result.stdout)
            }

if __name__ == '__main__':
    server = ComfyUIMCPServer()
    server.run(port=9006)
```

### 3. Hydra Orchestrator Service

**Location:** hydra-storage (192.168.1.244)
**Port:** 8701 (separate from current Hydra Tools API on 8700)

**Project Structure:**

```
/mnt/user/appdata/hydra-orchestrator/
├── docker-compose.yml
├── requirements.txt
├── main.py                       # FastAPI app
├── orchestrator/
│   ├── __init__.py
│   ├── core.py                   # Main orchestrator loop
│   ├── scheduler.py              # AIOS-inspired scheduler
│   ├── state_manager.py          # State assessment
│   └── conflict_resolver.py      # Conflict resolution
├── agents/
│   ├── __init__.py
│   ├── base_agent.py             # Base agent class
│   ├── research_crew.py          # Research crew
│   ├── development_crew.py       # Development crew
│   ├── infrastructure_crew.py    # Infrastructure crew
│   └── self_improvement.py       # Self-improvement agent
├── memory/
│   ├── __init__.py
│   ├── letta_client.py           # Letta integration
│   └── shared_blocks.py          # Shared memory blocks
├── tools/
│   ├── __init__.py
│   └── mcp_client.py             # MCP client integration
└── config/
    ├── constitution.yaml         # Immutable constraints
    ├── agent_configs.yaml        # Agent configurations
    └── mcp_servers.yaml          # MCP server registry
```

**Main Orchestrator Code:**

```python
# /mnt/user/appdata/hydra-orchestrator/orchestrator/core.py

import asyncio
from typing import List, Dict
from .scheduler import HydraScheduler
from .state_manager import StateManager
from .conflict_resolver import ConflictResolver
from agents import ResearchCrew, DevelopmentCrew, InfrastructureCrew, SelfImprovementAgent
from memory import LettaClient, SharedMemoryBlock
from tools import MCPClient
import logging

logger = logging.getLogger(__name__)

class HydraOrchestrator:
    """
    Main orchestrator for Hydra's 24/7 autonomous operation
    """

    def __init__(self):
        # Core components
        self.scheduler = HydraScheduler()
        self.state_manager = StateManager()
        self.conflict_resolver = ConflictResolver()

        # Memory layer
        self.memory_client = LettaClient(base_url="http://192.168.1.244:8000")

        # Tool layer
        self.mcp_client = MCPClient()

        # Agent crews
        self.crews = {
            'research': ResearchCrew(memory_client=self.memory_client, mcp_client=self.mcp_client),
            'development': DevelopmentCrew(memory_client=self.memory_client, mcp_client=self.mcp_client),
            'infrastructure': InfrastructureCrew(memory_client=self.memory_client, mcp_client=self.mcp_client),
        }

        # Self-improvement agent
        self.self_improvement = SelfImprovementAgent(
            memory_client=self.memory_client,
            mcp_client=self.mcp_client
        )

        # Shared memory blocks
        self.shared_memory = {
            'hydra_state': SharedMemoryBlock('hydra_state', all_agents_access='r', orchestrator_access='rw'),
            'research_findings': SharedMemoryBlock('research_findings', research_crew_access='rw'),
            'development_status': SharedMemoryBlock('development_status', dev_crew_access='rw'),
            'infrastructure_health': SharedMemoryBlock('infrastructure_health', infra_crew_access='rw'),
        }

        # Constitutional constraints (immutable)
        self.constitution = self.load_constitution()

        # Running flag
        self.running = False

    async def autonomous_loop(self):
        """
        Main 24/7 autonomous operation loop

        Every iteration:
        1. Assess current state
        2. Identify gaps and opportunities
        3. Prioritize tasks
        4. Allocate to agents
        5. Monitor execution
        6. Learn from results
        """

        self.running = True
        iteration = 0

        logger.info("Hydra Orchestrator: Starting autonomous loop")

        while self.running:
            try:
                iteration += 1
                logger.info(f"=== Iteration {iteration} ===")

                # Step 1: Assess current state
                state = await self.state_manager.assess_state()
                logger.info(f"State: {state['summary']}")

                # Update shared memory
                await self.shared_memory['hydra_state'].write('orchestrator', state)

                # Step 2: Identify work
                gaps = await self.identify_gaps(state)
                opportunities = await self.identify_opportunities(state)

                logger.info(f"Found {len(gaps)} gaps, {len(opportunities)} opportunities")

                # Step 3: Prioritize
                tasks = self.prioritize_tasks(gaps + opportunities)

                # Step 4: Allocate to agents
                for task in tasks:
                    # Check constitutional constraints
                    if not self.check_constitution(task):
                        logger.warning(f"Task blocked by constitution: {task['description']}")
                        await self.request_human_approval(task)
                        continue

                    # Check for conflicts
                    conflicts = await self.conflict_resolver.check_conflicts(task)
                    if conflicts:
                        resolution = await self.conflict_resolver.resolve(conflicts)
                        if not resolution['approved']:
                            logger.warning(f"Task conflict unresolved: {task['description']}")
                            continue

                    # Schedule task
                    await self.schedule_task(task)

                # Step 5: Monitor execution
                await self.monitor_active_tasks()

                # Step 6: Learn from results
                await self.learn_from_iteration(iteration)

                # Sleep between iterations
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error in autonomous loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Backoff on error

    async def identify_gaps(self, state: Dict) -> List[Dict]:
        """Identify gaps that need addressing"""

        gaps = []

        # Critical: Failed services
        if state['services']['failed']:
            for service in state['services']['failed']:
                gaps.append({
                    'type': 'infrastructure',
                    'priority': 1,  # Critical
                    'description': f'Fix failed service: {service}',
                    'crew': 'infrastructure',
                    'task': {
                        'action': 'restart_service',
                        'service': service
                    }
                })

        # High: Incomplete features
        if state['features']['incomplete']:
            for feature in state['features']['incomplete']:
                gaps.append({
                    'type': 'development',
                    'priority': 2,  # High
                    'description': f'Complete feature: {feature}',
                    'crew': 'development',
                    'task': {
                        'action': 'complete_feature',
                        'feature': feature
                    }
                })

        # Medium: Knowledge gaps
        if state['knowledge']['gaps']:
            for gap in state['knowledge']['gaps']:
                gaps.append({
                    'type': 'research',
                    'priority': 3,  # Medium
                    'description': f'Research: {gap}',
                    'crew': 'research',
                    'task': {
                        'action': 'research_topic',
                        'topic': gap
                    }
                })

        return gaps

    async def identify_opportunities(self, state: Dict) -> List[Dict]:
        """Identify opportunities for improvement"""

        opportunities = []

        # Performance optimization opportunities
        metrics = state['metrics']

        if metrics.get('inference_latency_p95', 0) > 2000:  # > 2s
            opportunities.append({
                'type': 'optimization',
                'priority': 3,  # Medium
                'description': 'Optimize inference latency',
                'crew': 'infrastructure',
                'task': {
                    'action': 'optimize_inference',
                    'target_metric': 'latency_p95',
                    'current_value': metrics['inference_latency_p95'],
                    'target_value': 1500
                }
            })

        # New technologies to evaluate
        tech_watch = await self.shared_memory['research_findings'].read('orchestrator')
        for tech in tech_watch.get('technologies_to_evaluate', []):
            opportunities.append({
                'type': 'evaluation',
                'priority': 4,  # Low
                'description': f'Evaluate: {tech["name"]}',
                'crew': 'research',
                'task': {
                    'action': 'evaluate_technology',
                    'technology': tech
                }
            })

        return opportunities

    def prioritize_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Prioritize tasks by priority level and impact"""

        # Sort by priority (lower number = higher priority)
        sorted_tasks = sorted(tasks, key=lambda t: (t['priority'], -t.get('impact', 0)))

        return sorted_tasks

    async def schedule_task(self, task: Dict):
        """Schedule task to appropriate crew"""

        crew_name = task['crew']
        crew = self.crews.get(crew_name)

        if not crew:
            logger.error(f"Unknown crew: {crew_name}")
            return

        # Submit to scheduler
        await self.scheduler.schedule(crew, task)

    async def monitor_active_tasks(self):
        """Monitor actively executing tasks"""

        active_tasks = await self.scheduler.get_active_tasks()

        for task_id, task_info in active_tasks.items():
            # Check if stuck (running > 30 minutes)
            if task_info['duration'] > 1800:
                logger.warning(f"Task {task_id} appears stuck: {task_info['duration']}s")
                await self.scheduler.interrupt_task(task_id)

    async def learn_from_iteration(self, iteration: int):
        """Learn from iteration results"""

        # Collect metrics
        metrics = await self.scheduler.get_iteration_metrics()

        # Update self-improvement agent
        await self.self_improvement.analyze_iteration(iteration, metrics)

        # Log performance
        logger.info(f"Iteration {iteration} metrics: {metrics}")

    def check_constitution(self, task: Dict) -> bool:
        """Check if task violates constitutional constraints"""

        # Immutable constraints
        for constraint in self.constitution['immutable_constraints']:
            if self.task_violates_constraint(task, constraint):
                return False

        return True

    async def request_human_approval(self, task: Dict):
        """Request human approval for constitutional gate"""

        # Queue for human review
        approval_request = {
            'task': task,
            'reason': 'Constitutional constraint requires approval',
            'timestamp': datetime.now(),
            'urgency': task.get('priority', 5)
        }

        # Store in database
        await self.state_manager.queue_approval_request(approval_request)

        # Notify via n8n webhook
        await self.mcp_client.call_tool('n8n', 'trigger_webhook', {
            'webhook': 'human_approval_needed',
            'data': approval_request
        })

    def load_constitution(self) -> Dict:
        """Load constitutional constraints from config"""

        with open('/config/constitution.yaml', 'r') as f:
            return yaml.safe_load(f)


if __name__ == '__main__':
    orchestrator = HydraOrchestrator()
    asyncio.run(orchestrator.autonomous_loop())
```

**Docker Compose:**

```yaml
# /mnt/user/appdata/hydra-orchestrator/docker-compose.yml
version: '3.8'

services:
  orchestrator:
    build: .
    container_name: hydra-orchestrator
    ports:
      - "8701:8701"
    environment:
      # Letta
      - LETTA_URL=http://192.168.1.244:8000

      # MCP Servers
      - MCP_FILESYSTEM_URL=http://192.168.1.244:9000
      - MCP_GIT_URL=http://192.168.1.244:9001
      - MCP_GITHUB_URL=http://192.168.1.244:9002
      - MCP_DOCKER_URL=http://192.168.1.244:9003
      - MCP_POSTGRES_URL=http://192.168.1.244:9004
      - MCP_QDRANT_URL=http://192.168.1.244:9005

      # LiteLLM
      - LLM_ENDPOINT=http://192.168.1.244:4000/v1
      - LLM_MODEL=claude-sonnet-4.5

      # PostgreSQL
      - PG_HOST=192.168.1.244
      - PG_PORT=5432
      - PG_DB=hydra
      - PG_USER=hydra
      - PG_PASSWORD=${PG_PASSWORD}

      # Redis
      - REDIS_HOST=192.168.1.244
      - REDIS_PORT=6379

    volumes:
      - /mnt/user/appdata/hydra-orchestrator/config:/config:ro
      - /mnt/user/appdata/hydra-orchestrator/logs:/logs
      - /mnt/user/appdata/hydra-dev:/workspace

    restart: unless-stopped

    networks:
      - hydra-network

networks:
  hydra-network:
    external: true
```

---

## CREW IMPLEMENTATIONS

### Research Crew

```python
# /mnt/user/appdata/hydra-orchestrator/agents/research_crew.py

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

class ResearchCrew:
    """
    Research crew for autonomous research tasks

    Agents:
    - Web Searcher: Finds relevant information online
    - Document Reader: Analyzes technical documents
    - Summarizer: Synthesizes findings into actionable insights
    """

    def __init__(self, memory_client, mcp_client):
        self.memory_client = memory_client
        self.mcp_client = mcp_client

        # LLM
        self.llm = ChatOpenAI(
            base_url="http://192.168.1.244:4000/v1",
            model="claude-sonnet-4.5",
            temperature=0.2
        )

        # Create agents
        self.web_searcher = Agent(
            role="Web Research Specialist",
            goal="Find relevant technical information and research papers",
            backstory="Expert at web research and technical documentation discovery",
            llm=self.llm,
            tools=[self.web_search_tool, self.web_fetch_tool],
            verbose=True
        )

        self.document_reader = Agent(
            role="Technical Document Analyst",
            goal="Analyze technical documents and extract key insights",
            backstory="Deep technical knowledge across multiple domains",
            llm=self.llm,
            tools=[self.read_file_tool, self.read_pdf_tool],
            verbose=True
        )

        self.summarizer = Agent(
            role="Research Synthesizer",
            goal="Synthesize research findings into actionable insights",
            backstory="Expert at connecting disparate information into coherent narratives",
            llm=self.llm,
            tools=[self.memory_tool],
            verbose=True
        )

    async def execute(self, task: Dict) -> Dict:
        """Execute research task"""

        research_topic = task['task']['topic']

        # Create tasks
        search_task = Task(
            description=f"Research {research_topic}. Find latest developments, key technologies, and implementation patterns.",
            agent=self.web_searcher,
            expected_output="List of relevant sources with summaries"
        )

        analysis_task = Task(
            description=f"Analyze sources for {research_topic}. Extract key technical details and implementation patterns.",
            agent=self.document_reader,
            expected_output="Technical analysis with code examples",
            context=[search_task]
        )

        synthesis_task = Task(
            description=f"Synthesize findings on {research_topic} into actionable recommendations for Hydra.",
            agent=self.summarizer,
            expected_output="Executive summary with implementation recommendations",
            context=[search_task, analysis_task]
        )

        # Create crew
        crew = Crew(
            agents=[self.web_searcher, self.document_reader, self.summarizer],
            tasks=[search_task, analysis_task, synthesis_task],
            verbose=True
        )

        # Execute
        result = crew.kickoff()

        # Store in shared memory
        await self.store_findings(research_topic, result)

        return {
            'status': 'success',
            'findings': result
        }

    async def store_findings(self, topic: str, findings: str):
        """Store research findings in shared memory"""

        # Get shared memory block
        shared_memory = await self.memory_client.get_shared_block('research_findings')

        # Read current findings
        current = await shared_memory.read()

        # Append new findings
        current['findings'].append({
            'topic': topic,
            'summary': findings,
            'timestamp': datetime.now().isoformat()
        })

        # Write back
        await shared_memory.write(current)

    # Tool definitions
    @property
    def web_search_tool(self):
        """Web search via MCP"""
        from langchain.tools import Tool

        async def search(query: str) -> str:
            result = await self.mcp_client.call_tool('web-search', 'search', {'query': query})
            return result['results']

        return Tool(
            name="web_search",
            func=search,
            description="Search the web for information"
        )

    # ... other tools ...
```

### Development Crew

```python
# /mnt/user/appdata/hydra-orchestrator/agents/development_crew.py

from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

class DevelopmentCrew:
    """
    Development crew for autonomous code development

    Agents:
    - Coder: Writes code
    - Tester: Writes and runs tests
    - Reviewer: Reviews code for quality
    - Integrator: Deploys and integrates
    """

    def __init__(self, memory_client, mcp_client):
        self.memory_client = memory_client
        self.mcp_client = mcp_client

        self.llm = ChatOpenAI(
            base_url="http://192.168.1.244:4000/v1",
            model="claude-sonnet-4.5",
            temperature=0.1
        )

        # Coder agent
        self.coder = Agent(
            role="Software Engineer",
            goal="Write clean, efficient, well-documented code",
            backstory="Expert Python developer with deep knowledge of async patterns",
            llm=self.llm,
            tools=[self.read_file_tool, self.write_file_tool, self.search_code_tool],
            verbose=True
        )

        # Tester agent
        self.tester = Agent(
            role="QA Engineer",
            goal="Ensure code quality through comprehensive testing",
            backstory="Expert at test-driven development and quality assurance",
            llm=self.llm,
            tools=[self.run_tests_tool, self.write_file_tool],
            verbose=True
        )

        # Reviewer agent
        self.reviewer = Agent(
            role="Code Reviewer",
            goal="Ensure code quality, security, and maintainability",
            backstory="Senior engineer with focus on code quality and best practices",
            llm=self.llm,
            tools=[self.read_file_tool, self.git_diff_tool],
            verbose=True
        )

        # Integrator agent
        self.integrator = Agent(
            role="DevOps Engineer",
            goal="Deploy code and ensure integration",
            backstory="Expert at deployment, containerization, and CI/CD",
            llm=self.llm,
            tools=[self.docker_tool, self.git_tool],
            verbose=True
        )

    async def execute(self, task: Dict) -> Dict:
        """Execute development task"""

        feature = task['task']['feature']

        # Create tasks
        code_task = Task(
            description=f"Implement {feature}. Follow Hydra's coding standards.",
            agent=self.coder,
            expected_output="Working code with documentation"
        )

        test_task = Task(
            description=f"Write tests for {feature}. Achieve >80% coverage.",
            agent=self.tester,
            expected_output="Test suite with passing tests",
            context=[code_task]
        )

        review_task = Task(
            description=f"Review code for {feature}. Check quality, security, maintainability.",
            agent=self.reviewer,
            expected_output="Review feedback with approval/rejection",
            context=[code_task, test_task]
        )

        deploy_task = Task(
            description=f"Deploy {feature} to development environment.",
            agent=self.integrator,
            expected_output="Deployment confirmation",
            context=[code_task, test_task, review_task]
        )

        # Create crew
        crew = Crew(
            agents=[self.coder, self.tester, self.reviewer, self.integrator],
            tasks=[code_task, test_task, review_task, deploy_task],
            verbose=True
        )

        # Execute
        result = crew.kickoff()

        return {
            'status': 'success',
            'result': result
        }
```

---

## CONSTITUTIONAL CONSTRAINTS

```yaml
# /mnt/user/appdata/hydra-orchestrator/config/constitution.yaml

# HYDRA CONSTITUTIONAL CONSTRAINTS
# These constraints are IMMUTABLE and enforced at orchestrator level

immutable_constraints:
  - constraint: "never_delete_databases"
    description: "Never delete PostgreSQL, Qdrant, or Neo4j databases without human approval"
    detection:
      - pattern: "DROP DATABASE"
      - pattern: "DELETE FROM.*WHERE 1=1"
      - tool: "postgres-mcp.execute_sql" with DROP
      - tool: "qdrant-mcp.delete_collection"

  - constraint: "never_modify_network"
    description: "Never modify network configuration or firewall rules"
    detection:
      - file_write: "/etc/network/*"
      - file_write: "/etc/nixos/configuration.nix" with "networking."
      - command: "iptables"
      - command: "ufw"

  - constraint: "never_disable_auth"
    description: "Never disable authentication systems"
    detection:
      - file_write: "**/auth.py" with "disabled"
      - config_change: "DISABLE_AUTH"
      - config_change: "NO_PASSWORD"

  - constraint: "never_expose_secrets"
    description: "Never expose secrets or credentials in logs, responses, or commits"
    detection:
      - pattern: "password.*=.*"
      - pattern: "api_key.*=.*"
      - pattern: "secret.*=.*"
      - file_write: ".env" to public location
      - git_commit: containing secrets

  - constraint: "never_modify_constitution"
    description: "Never modify this constitutional file"
    detection:
      - file_write: "constitution.yaml"

  - constraint: "always_audit_trail"
    description: "Always maintain audit trail of modifications"
    enforcement:
      - log_all_actions: true
      - database: "hydra.audit_log"
      - retention: "365 days"

  - constraint: "always_sandbox_code"
    description: "Always sandbox code execution"
    enforcement:
      - require_sandbox: true
      - sandbox_provider: "e2b"
      - network_disabled: true

  - constraint: "human_approval_git_push"
    description: "Require human approval for git push to main"
    detection:
      - git_command: "push origin main"
      - git_command: "push origin master"
    action: "queue_for_approval"

supervised_operations:
  # Operations that require human approval
  - operation: "file_delete_outside_workspace"
    paths_excluded: ["/mnt/user/appdata/hydra-dev/workspace/*"]
    approval_required: true

  - operation: "service_stop"
    services: ["postgres", "qdrant", "letta", "litellm"]
    approval_required: true

  - operation: "nixos_configuration_change"
    files: ["/etc/nixos/configuration.nix"]
    approval_required: true

  - operation: "container_remove"
    containers: ["postgres", "qdrant", "letta", "litellm"]
    approval_required: true

  - operation: "database_migration"
    databases: ["hydra", "letta"]
    approval_required: true

autonomous_operations:
  # Operations agents can perform autonomously
  - operation: "code_modification"
    paths: ["/mnt/user/appdata/hydra-dev/*"]
    require_git_commit: true

  - operation: "config_file_update"
    files: [".env.local", "*.local.json", "docker-compose.override.yml"]

  - operation: "feature_addition"
    paths: ["/mnt/user/appdata/hydra-dev/src/*"]
    require_tests: true

  - operation: "bug_fix"
    paths: ["/mnt/user/appdata/hydra-dev/src/*"]
    require_tests: true

  - operation: "mcp_tool_creation"
    paths: ["/mnt/user/appdata/mcp-servers/custom/*"]

  - operation: "research_and_analysis"
    allowed: true

  - operation: "documentation_update"
    paths: ["/mnt/user/appdata/hydra-dev/docs/*"]
```

---

## DEPLOYMENT SEQUENCE

### Phase 1: Foundation (Week 1)

```bash
# Day 1-2: Deploy Letta
cd /mnt/user/appdata
git clone https://github.com/letta-ai/letta-docker.git letta
cd letta
# Configure as shown above
docker-compose up -d

# Day 3-4: Deploy MCP servers
cd /mnt/user/appdata
mkdir -p mcp-servers/custom
# Configure as shown above
docker-compose up -d

# Day 5-7: Deploy Orchestrator
cd /mnt/user/appdata
git clone <hydra-orchestrator-repo> hydra-orchestrator
cd hydra-orchestrator
pip install -r requirements.txt
# Test locally first
python orchestrator/core.py --test-mode

# Once validated:
docker-compose build
docker-compose up -d
```

### Phase 2: Agent Teams (Week 2)

```bash
# Implement and test each crew individually
python -m agents.research_crew --test
python -m agents.development_crew --test
python -m agents.infrastructure_crew --test

# Deploy to orchestrator
docker-compose restart orchestrator
```

### Phase 3: Autonomous Loop (Week 3)

```bash
# Start orchestrator in test mode (5 iterations only)
docker exec -it hydra-orchestrator python orchestrator/core.py --test --iterations 5

# Monitor logs
docker logs -f hydra-orchestrator

# If successful, enable full autonomy
docker exec -it hydra-orchestrator python orchestrator/core.py --autonomous
```

---

## MONITORING

### Grafana Dashboard

**Metrics to Track:**

```yaml
# /mnt/user/appdata/grafana/dashboards/hydra-orchestrator.json

panels:
  - title: "Active Agents"
    query: "hydra_active_agents"

  - title: "Task Queue Depth"
    query: "hydra_task_queue_depth"

  - title: "Task Completion Rate"
    query: "rate(hydra_tasks_completed[5m])"

  - title: "Conflict Resolution Success Rate"
    query: "hydra_conflicts_resolved / hydra_conflicts_total"

  - title: "Human Approval Queue"
    query: "hydra_approval_queue_size"

  - title: "Agent Memory Usage"
    query: "hydra_agent_memory_bytes"

  - title: "LLM Token Usage"
    query: "rate(hydra_llm_tokens_total[1h])"

  - title: "Agent Error Rate"
    query: "rate(hydra_agent_errors[5m])"
```

### Alerts

```yaml
# /mnt/user/appdata/prometheus/alerts/hydra-orchestrator.yml

groups:
  - name: hydra_orchestrator
    interval: 30s
    rules:
      - alert: OrchestatorDown
        expr: up{job="hydra-orchestrator"} == 0
        for: 1m
        annotations:
          summary: "Hydra Orchestrator is down"

      - alert: TaskQueueStuck
        expr: hydra_task_queue_depth > 100
        for: 10m
        annotations:
          summary: "Task queue is stuck with {{ $value }} tasks"

      - alert: HighErrorRate
        expr: rate(hydra_agent_errors[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High agent error rate: {{ $value }} errors/sec"

      - alert: ConflictResolutionFailing
        expr: (hydra_conflicts_resolved / hydra_conflicts_total) < 0.5
        for: 15m
        annotations:
          summary: "Conflict resolution success rate below 50%"
```

---

## NEXT STEPS

1. **Review this architecture** with Shaun
2. **Set up Letta** first (foundation for everything else)
3. **Deploy MCP servers** (tool layer)
4. **Build orchestrator skeleton** (test with simple tasks)
5. **Implement Research Crew** (first real crew)
6. **Test autonomous loop** (5 iterations in test mode)
7. **Gradually enable full autonomy** (monitor closely)

---

*Guide Version: 1.0*
*Date: December 16, 2025*
*Status: Ready for Implementation*
