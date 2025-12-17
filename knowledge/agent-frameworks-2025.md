# Agent Frameworks Landscape 2025

## Executive Summary

The agent framework ecosystem is **fragmenting**. Monolithic frameworks like LangChain are declining in relative popularity as developers shift to:
1. Native SDKs (OpenAI, Anthropic, Ollama)
2. Specialized components (Mem0, Browser-Use, Dify)
3. Lightweight alternatives (Agno, PydanticAI)

## Key Data Points (Ant Open Source Research)

- **Agent Frameworks declining** - LangChain, LlamaIndex, AutoGen losing community investment
- **135 projects** across 19 technical domains in 2025
- **62%** of LLM ecosystem projects born after October 2022
- **Python** dominates infrastructure, **TypeScript** dominates applications

## Framework Comparison

### LangChain/LangGraph
- **Status:** Still largest community (80K+ GitHub stars) but relative decline
- **Pros:** Comprehensive toolset, checkpointing, human-in-the-loop
- **Cons:**
  - API instability ("breaks monthly")
  - Over-abstraction (5+ layers to debug)
  - Memory bloat (2GB for basic tasks reported)
  - Documentation fragmentation

### Agno (Rising Star)
- **Performance:** 529x faster instantiation, 50x less memory than LangGraph
- **Agent creation:** ~2 microseconds
- **Philosophy:** "Memory usage directly affects production costs"
- **Features:** Built-in memory, MCP support, 100+ toolkits

### OpenAI Agents SDK (March 2025)
- **Status:** ~10K GitHub stars in months
- **Approach:** Minimal abstractions, 4 core primitives
- **Key:** Provider-agnostic (100+ LLMs supported)
- **Evolution:** Production-ready successor to Swarm

### Google ADK (Cloud NEXT 2025)
- **Status:** Powers Google Agentspace
- **Features:** Bidirectional audio/video, rich tool ecosystem
- **Best for:** GCP deployments

### PydanticAI
- **Background:** From team behind Pydantic (validation layer for most AI SDKs)
- **Approach:** Type-safe, schema-driven
- **Best for:** Production applications requiring data reliability

## Developer Consensus 2025

> "If you are building a simple Retrieve → Stuff context → Generate loop, stick to Vanilla Python + Pydantic."

> "Don't feel pressured to use a framework just because it's popular."

> "40% performance improvement when switching to native SDKs"

## Hydra Recommendation

**DON'T adopt LangGraph for Hydra.** Instead:

1. **Keep AIOS-style scheduler** - Works, no API churn, you control it
2. **Consider Agno** for new agent work requiring high concurrency
3. **Use native SDKs** (Ollama, TabbyAPI) directly
4. **constitution.py already handles** human approval gates (LangGraph interrupts redundant)

## Specialized Component Alternatives

Instead of monolithic frameworks, consider purpose-built tools:

| Need | Tool | Notes |
|------|------|-------|
| Memory | Mem0 | If MIRIX becomes insufficient |
| Tool Use | Browser-Use | Web automation |
| Workflows | Dify | Visual workflow builder |
| Validation | PydanticAI | Type-safe interactions |

## Sources

- [Ant Open Source: LLM Development Landscape 2.0](https://medium.com/@ant-oss/open-source-llm-development-landscape-2-0-2025-revisited-d18cbf0a49c2)
- [ZenML: LangGraph Alternatives](https://www.zenml.io/blog/langgraph-alternatives)
- [LangWatch: Best AI Agent Frameworks 2025](https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more)
- [Agno Performance Benchmarks](https://docs.agno.com/get-started/performance)
- [State of AI Agent Frameworks](https://medium.com/@roberto.g.infante/the-state-of-ai-agent-frameworks-comparing-langgraph-openai-agent-sdk-google-adk-and-aws-d3e52a497720)

---
*Last Updated: 2025-12-17*
*Source: ULTRATHINK analysis of user-provided research*
