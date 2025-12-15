"""
Hydra Agent Tools Library

Provides tools for LangChain, LangGraph, and CrewAI agents to interact
with the Hydra cluster services.

Available tools (require langchain - install with: pip install hydra-cluster[agents]):
- web_search: Search the web using SearXNG
- query_knowledge: Semantic search in Qdrant vector database
- crawl_url: Scrape web pages using Firecrawl
- generate_embedding: Create embeddings using Ollama
- chat_completion: Get LLM responses via LiteLLM
- execute_ssh: Run commands on cluster nodes
- read_file: Read files from shared storage
- write_file: Write files to shared storage
- generate_image: Create images using ComfyUI

Self-Improvement Tools (Phase 11) - always available:
- RouteClassifier: Intelligent model routing based on prompt complexity
- PreferenceLearner: User preference tracking and model recommendations
- SelfDiagnosisEngine: Failure analysis and pattern detection
- ResourceOptimizer: GPU/CPU/RAM utilization analysis
- KnowledgeOptimizer: Knowledge lifecycle management
- CapabilityTracker: Feature gap tracking and prioritization
- LettaMemoryManager: Enhanced memory for Letta agents (model perf, preferences, learnings)

Monitoring Tools (for CrewAI integration):
- PrometheusQueryTool: Query Prometheus metrics
- DockerStatusTool: Check container status on Unraid
- GPUStatusTool: GPU health and VRAM monitoring
- DiskStatusTool: Disk usage monitoring
- HealthCheckTool: Service health verification

Maintenance Tools (for CrewAI integration):
- ServiceDependencyTool: Service dependency graph
- MaintenanceWindowTool: Maintenance window scheduling
- DockerComposeTool: Docker Compose service control
- SystemctlTool: NixOS systemd service control
- BackupTool: Database backup operations

Web Research Tools (for CrewAI integration):
- SearXNGTool: Privacy-respecting metasearch
- FirecrawlTool: Web page crawling and extraction
- WebResearchTool: Combined research capabilities

Usage:
    # Self-improvement tools (always available)
    from hydra_tools import RouteClassifier, SelfDiagnosisEngine

    classifier = RouteClassifier()
    model = classifier.route("Explain quantum computing")

    # Agent tools (require langchain)
    from hydra_tools import web_search, query_knowledge

    results = web_search("ExLlamaV3 tensor parallelism")
    docs = query_knowledge("How to configure TabbyAPI?")
"""

# Optional imports for LangChain agent tools (require langchain extra)
try:
    from .search import web_search, crawl_url
    from .knowledge import query_knowledge, generate_embedding, hybrid_search
    from .inference import chat_completion, generate_image
    from .storage import read_file, write_file
    from .cluster import execute_ssh, get_cluster_status
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    # LangChain not installed - agent tools not available
    _LANGCHAIN_AVAILABLE = False
    web_search = None
    crawl_url = None
    query_knowledge = None
    generate_embedding = None
    hybrid_search = None
    chat_completion = None
    generate_image = None
    read_file = None
    write_file = None
    execute_ssh = None
    get_cluster_status = None

# Phase 11: Self-Improvement Tools (always available - no langchain dependency)
from .routellm import (
    RouteClassifier,
    RoutingDecision,
    ModelTier,
    classify_prompt,
)

from .preference_learning import (
    PreferenceLearner,
    FeedbackType,
    TaskType,
    ModelStats,
    UserPreferences,
    Interaction,
)

from .self_diagnosis import (
    SelfDiagnosisEngine,
    FailureCategory,
    Severity,
    FailureEvent,
    FailurePattern,
    DiagnosticReport,
    create_diagnosis_router,
)

from .resource_optimization import (
    ResourceOptimizer,
    ResourceType,
    OptimizationPriority,
    ResourceSnapshot,
    UtilizationPattern,
    OptimizationSuggestion,
    create_optimization_router,
)

from .knowledge_optimization import (
    KnowledgeOptimizer,
    KnowledgeSource,
    KnowledgeCategory,
    KnowledgeEntry,
    ConsolidationSuggestion,
    PruningSuggestion,
    KnowledgeMetrics,
    create_knowledge_router,
)

from .capability_expansion import (
    CapabilityTracker,
    CapabilityGap,
    CapabilityCategory,
    Priority as GapPriority,
    Status as GapStatus,
    create_capability_api as create_capabilities_router,
)

from .letta_memory import (
    LettaMemoryManager,
    MemoryBlockType,
    ModelPerformance,
    UserPreference,
    SystemLearning,
    create_memory_manager,
)

from .monitoring import (
    PrometheusQueryTool,
    DockerStatusTool,
    GPUStatusTool,
    DiskStatusTool,
    HealthCheckTool,
    MetricResult,
    ContainerStatus,
    GPUStatus,
)

from .maintenance import (
    ServiceDependencyTool,
    MaintenanceWindowTool,
    DockerComposeTool,
    SystemctlTool,
    BackupTool,
    ServiceDependency,
    MaintenanceWindow,
    BackupResult,
)

from .web_tools import (
    SearXNGTool,
    FirecrawlTool,
    WebResearchTool,
    SearchResult,
    CrawlResult,
)

__all__ = [
    # Core agent tools
    "web_search",
    "crawl_url",
    "query_knowledge",
    "generate_embedding",
    "hybrid_search",
    "chat_completion",
    "generate_image",
    "read_file",
    "write_file",
    "execute_ssh",
    "get_cluster_status",
    # RouteLLM
    "RouteClassifier",
    "RoutingDecision",
    "ModelTier",
    "classify_prompt",
    # Preference Learning
    "PreferenceLearner",
    "FeedbackType",
    "TaskType",
    "ModelStats",
    "UserPreferences",
    "Interaction",
    # Self Diagnosis
    "SelfDiagnosisEngine",
    "FailureCategory",
    "Severity",
    "FailureEvent",
    "FailurePattern",
    "DiagnosticReport",
    "create_diagnosis_router",
    # Resource Optimization
    "ResourceOptimizer",
    "ResourceType",
    "OptimizationPriority",
    "ResourceSnapshot",
    "UtilizationPattern",
    "OptimizationSuggestion",
    "create_optimization_router",
    # Knowledge Optimization
    "KnowledgeOptimizer",
    "KnowledgeSource",
    "KnowledgeCategory",
    "KnowledgeEntry",
    "ConsolidationSuggestion",
    "PruningSuggestion",
    "KnowledgeMetrics",
    "create_knowledge_router",
    # Capability Expansion
    "CapabilityTracker",
    "CapabilityGap",
    "GapPriority",
    "GapStatus",
    "create_capabilities_router",
    # Letta Memory Enhancement
    "LettaMemoryManager",
    "MemoryBlockType",
    "ModelPerformance",
    "UserPreference",
    "SystemLearning",
    "create_memory_manager",
    # Monitoring Tools
    "PrometheusQueryTool",
    "DockerStatusTool",
    "GPUStatusTool",
    "DiskStatusTool",
    "HealthCheckTool",
    "MetricResult",
    "ContainerStatus",
    "GPUStatus",
    # Maintenance Tools
    "ServiceDependencyTool",
    "MaintenanceWindowTool",
    "DockerComposeTool",
    "SystemctlTool",
    "BackupTool",
    "ServiceDependency",
    "MaintenanceWindow",
    "BackupResult",
    # Web Research Tools
    "SearXNGTool",
    "FirecrawlTool",
    "WebResearchTool",
    "SearchResult",
    "CrawlResult",
]

__version__ = "1.5.0"
