# Automation & Agent Framework - Hydra Cluster

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Automation Layer                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │     n8n      │  │  LangGraph   │  │   CrewAI     │          │
│  │  (Workflows) │  │ (State/DAGs) │  │ (Multi-Agent)│          │
│  │    :5678     │  │   (Python)   │  │   (Python)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └─────────────────┼──────────────────┘                   │
│                           │                                      │
│                    ┌──────▼───────┐                             │
│                    │   LiteLLM    │                             │
│                    │    :4000     │                             │
│                    └──────┬───────┘                             │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                   │
│         ▼                 ▼                 ▼                   │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐               │
│    │TabbyAPI │      │ Ollama  │      │ Ollama  │               │
│    │ (70B)   │      │ (Fast)  │      │ (CPU)   │               │
│    └─────────┘      └─────────┘      └─────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## n8n Workflow Automation

### Overview
n8n is the primary 24/7 automation engine with:
- 545+ integrations
- Visual workflow builder
- AI nodes for LLM operations
- Webhook triggers
- Scheduled execution
- PostgreSQL backend for persistence

### Docker Deployment

```yaml
# In docker-compose.yml
n8n:
  image: n8nio/n8n:latest
  container_name: hydra-n8n
  restart: unless-stopped
  ports:
    - "5678:5678"
  environment:
    - N8N_BASIC_AUTH_ACTIVE=true
    - N8N_BASIC_AUTH_USER=admin
    - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
    - DB_TYPE=postgresdb
    - DB_POSTGRESDB_HOST=postgres
    - DB_POSTGRESDB_PORT=5432
    - DB_POSTGRESDB_DATABASE=n8n
    - DB_POSTGRESDB_USER=hydra
    - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
    - WEBHOOK_URL=http://192.168.1.244:5678/
  volumes:
    - n8n_data:/home/node/.n8n
  depends_on:
    - postgres
```

### Essential Workflows to Create

#### 1. Cluster Health Check (Every 5 minutes)
```
Trigger: Schedule (5 min)
  → HTTP Request: GET prometheus:9090/api/v1/targets
  → IF any target health != "up"
    → Discord Notification: "Service down: {service}"
  → Else: Log "All healthy"
```

#### 2. Daily Research Digest
```
Trigger: Schedule (6 AM daily)
  → Miniflux: Get unread articles (limit 50)
  → Loop: For each article
    → LiteLLM: Summarize in 2-3 sentences
  → Aggregate summaries
  → LiteLLM: Generate digest with key themes
  → Email/Discord: Send digest
  → Miniflux: Mark as read
```

#### 3. Document Ingestion Pipeline
```
Trigger: Webhook (file uploaded)
  → IF file type = PDF
    → Docling: Parse PDF to markdown
  → Split: Recursive text splitter (1000 chars, 200 overlap)
  → Loop: For each chunk
    → Ollama: Generate embedding (nomic-embed-text)
    → Qdrant: Upsert vector
  → Notify: "Document {name} ingested: {chunk_count} chunks"
```

#### 4. Model Performance Monitor
```
Trigger: Schedule (hourly)
  → HTTP Request: TabbyAPI /v1/model
  → HTTP Request: Test completion (short prompt)
  → Calculate: tokens/sec from response
  → IF tokens/sec < 10
    → Alert: "TabbyAPI performance degraded"
  → Prometheus: Push metric
```

#### 5. Backup Reminder
```
Trigger: Schedule (Sunday 2 AM)
  → SSH: Run backup scripts
  → Verify: Check backup file exists
  → Alert: Success or failure
```

---

## LangGraph (Stateful Workflows)

### When to Use LangGraph
- Complex multi-step reasoning
- State that must persist between steps
- Conditional branching based on LLM output
- Human-in-the-loop workflows
- Research tasks with iterative refinement

### Installation
```bash
pip install langgraph langchain-community langchain-openai
```

### Example: Research Agent

```python
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, List

class ResearchState(TypedDict):
    query: str
    search_results: List[str]
    analysis: str
    final_report: str

# Initialize LLM via LiteLLM
llm = ChatOpenAI(
    base_url="http://192.168.1.244:4000/v1",
    api_key="sk-hydra-local",
    model="hydra-70b"
)

def search_step(state: ResearchState) -> ResearchState:
    # Call SearXNG via HTTP
    results = search_web(state["query"])
    state["search_results"] = results
    return state

def analyze_step(state: ResearchState) -> ResearchState:
    prompt = f"Analyze these search results for '{state['query']}':\n{state['search_results']}"
    state["analysis"] = llm.invoke(prompt).content
    return state

def report_step(state: ResearchState) -> ResearchState:
    prompt = f"Write a comprehensive report based on:\nQuery: {state['query']}\nAnalysis: {state['analysis']}"
    state["final_report"] = llm.invoke(prompt).content
    return state

# Build graph
workflow = StateGraph(ResearchState)
workflow.add_node("search", search_step)
workflow.add_node("analyze", analyze_step)
workflow.add_node("report", report_step)

workflow.add_edge("search", "analyze")
workflow.add_edge("analyze", "report")
workflow.add_edge("report", END)

workflow.set_entry_point("search")
app = workflow.compile()

# Run
result = app.invoke({"query": "latest ExLlamaV3 developments"})
print(result["final_report"])
```

### State Persistence with PostgreSQL

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Connect to Hydra PostgreSQL
connection_string = "postgresql://hydra:password@192.168.1.244:5432/hydra"
checkpointer = PostgresSaver.from_conn_string(connection_string)

# Compile with checkpointer
app = workflow.compile(checkpointer=checkpointer)

# Resume from checkpoint
config = {"configurable": {"thread_id": "research-123"}}
result = app.invoke({"query": "..."}, config)
```

---

## CrewAI (Multi-Agent Teams)

**Status:** DEPLOYED (2025-12-10)
**Container:** hydra-crewai
**Location:** /mnt/user/appdata/crewai/

### Deployed Crews

| Crew | Schedule | Purpose |
|------|----------|---------|
| Monitoring Crew | Daily 6 AM | Analyze metrics, logs, generate health report |
| Research Crew | Weekly Mon 2 AM | Web research with synthesis |

### Running Crews
```bash
# Via cron (automatic)
/mnt/user/appdata/hydra-stack/scripts/crew_scheduler.sh monitoring
/mnt/user/appdata/hydra-stack/scripts/crew_scheduler.sh research "topic"

# Direct in container
docker exec hydra-crewai python /app/run_crew.py monitoring
docker exec hydra-crewai python /app/run_crew.py research --topic "AI trends"
```

### When to Use CrewAI
- Tasks requiring multiple specialized perspectives
- Role-based collaboration (researcher, writer, critic)
- Parallel task execution
- Complex projects with defined responsibilities

### Example: Content Creation Crew

```python
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

# LiteLLM connection
llm = ChatOpenAI(
    base_url="http://192.168.1.244:4000/v1",
    api_key="sk-hydra-local",
    model="hydra-70b"
)

# Define agents
researcher = Agent(
    role="Senior Research Analyst",
    goal="Find and synthesize the latest information on AI topics",
    backstory="Expert at finding technical details and summarizing complex topics",
    llm=llm,
    verbose=True
)

writer = Agent(
    role="Technical Writer",
    goal="Create clear, engaging documentation",
    backstory="Skilled at explaining complex topics to technical audiences",
    llm=llm,
    verbose=True
)

critic = Agent(
    role="Technical Reviewer",
    goal="Ensure accuracy and completeness",
    backstory="Detail-oriented expert who catches errors and improves quality",
    llm=llm,
    verbose=True
)

# Define tasks
research_task = Task(
    description="Research the current state of {topic}. Find key developments, best practices, and potential issues.",
    agent=researcher,
    expected_output="Comprehensive research notes with sources"
)

writing_task = Task(
    description="Write a technical guide based on the research. Include examples and best practices.",
    agent=writer,
    expected_output="Well-structured technical document",
    context=[research_task]
)

review_task = Task(
    description="Review the document for accuracy, completeness, and clarity. Suggest improvements.",
    agent=critic,
    expected_output="Reviewed document with corrections",
    context=[writing_task]
)

# Create crew
crew = Crew(
    agents=[researcher, writer, critic],
    tasks=[research_task, writing_task, review_task],
    process=Process.sequential,
    verbose=True
)

# Run
result = crew.kickoff(inputs={"topic": "ExLlamaV2 tensor parallelism"})
print(result)
```

---

## Tool Registry

Agents have access to these tools via function calling:

| Tool | Function | Access |
|------|----------|--------|
| `web_search` | Search via SearXNG | HTTP API |
| `crawl_url` | Extract content via Firecrawl | HTTP API |
| `query_knowledge` | Vector search via Qdrant | HTTP API |
| `execute_code` | Run Python in sandbox | Container |
| `file_read` | Read from hydra_shared | NFS mount |
| `file_write` | Write to hydra_shared | NFS mount |
| `generate_image` | Create via ComfyUI API | HTTP API |
| `ssh_execute` | Run commands on nodes | SSH |

### Tool Implementation Example

```python
from langchain.tools import tool
import requests

@tool
def web_search(query: str) -> str:
    """Search the web using SearXNG. Returns top results."""
    response = requests.get(
        "http://192.168.1.244:8080/search",
        params={"q": query, "format": "json", "categories": "general"}
    )
    results = response.json().get("results", [])[:5]
    return "\n".join([f"- {r['title']}: {r['url']}" for r in results])

@tool
def query_knowledge(query: str, limit: int = 5) -> str:
    """Search the knowledge base using semantic similarity."""
    # Generate embedding
    embed_response = requests.post(
        "http://192.168.1.203:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": query}
    )
    embedding = embed_response.json()["embedding"]
    
    # Search Qdrant
    search_response = requests.post(
        "http://192.168.1.244:6333/collections/documents/points/search",
        json={"vector": embedding, "limit": limit, "with_payload": True}
    )
    results = search_response.json()["result"]
    return "\n---\n".join([r["payload"]["text"] for r in results])
```

---

## n8n + LLM Integration

### AI Node Configuration
In n8n, use the "AI Agent" or "OpenAI" nodes with:

```
Base URL: http://litellm:4000/v1
API Key: sk-hydra-local
Model: hydra-70b
```

### Custom HTTP Request to LiteLLM

```json
{
  "method": "POST",
  "url": "http://litellm:4000/v1/chat/completions",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-hydra-local"
  },
  "body": {
    "model": "hydra-70b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "{{ $json.message }}"}
    ],
    "max_tokens": 1000
  }
}
```

---

## Verification

```bash
# n8n health
curl -s http://192.168.1.244:5678/healthz

# n8n workflows (requires auth)
curl -u admin:password http://192.168.1.244:5678/api/v1/workflows

# Test LangGraph workflow
python -c "from research_agent import app; print(app.invoke({'query': 'test'}))"

# Test CrewAI
python -c "from content_crew import crew; print(crew.kickoff({'topic': 'test'}))"
```

---

*Knowledge file: automation.md*
*Last updated: December 8, 2025*
