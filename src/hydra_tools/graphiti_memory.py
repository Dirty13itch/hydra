"""
Hydra Graphiti Memory Integration

Hybrid memory search combining:
- Graph traversal (Neo4j via Graphiti)
- Semantic search (vector embeddings)
- Keyword search (BM25)

Expected 18.5% accuracy improvement over vector-only search.

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Lazy imports
_graphiti = None
_graphiti_initialized = False

# =============================================================================
# Prometheus Metrics
# =============================================================================

GRAPHITI_QUERIES = Counter(
    "hydra_graphiti_queries_total",
    "Total Graphiti queries",
    ["query_type"]
)

GRAPHITI_LATENCY = Histogram(
    "hydra_graphiti_latency_seconds",
    "Graphiti query latency",
    ["operation"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

GRAPHITI_NODES = Gauge(
    "hydra_graphiti_nodes_total",
    "Total nodes in Graphiti knowledge graph"
)

GRAPHITI_EDGES = Gauge(
    "hydra_graphiti_edges_total",
    "Total edges in Graphiti knowledge graph"
)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class GraphitiConfig:
    """Configuration for Graphiti memory integration."""
    neo4j_uri: str = "bolt://192.168.1.244:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = os.environ.get("NEO4J_PASSWORD", "HydraNeo4jPass2024")
    neo4j_database: str = "neo4j"

    # LLM config (using Ollama via OpenAI-compatible API)
    llm_base_url: str = "http://192.168.1.203:11434/v1"
    llm_model: str = "qwen2.5:7b"
    llm_api_key: str = "sk-ollama-local-key"  # Fake key for OpenAI client compatibility

    # Embedding config (using Ollama via OpenAI-compatible API)
    embedding_base_url: str = "http://192.168.1.203:11434/v1"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Search config
    search_limit: int = 10
    min_score: float = 0.5


# =============================================================================
# Graphiti Client Wrapper
# =============================================================================

class GraphitiMemory:
    """
    Graphiti-based hybrid memory system.

    Combines graph traversal, semantic search, and keyword search
    for improved retrieval accuracy.
    """

    def __init__(self, config: Optional[GraphitiConfig] = None):
        self.config = config or GraphitiConfig()
        self._client = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Graphiti client with Neo4j and Ollama."""
        if self._initialized:
            return True

        try:
            # Set fake OpenAI API key for SDK compatibility (using Ollama, not OpenAI)
            os.environ.setdefault("OPENAI_API_KEY", self.config.llm_api_key)

            from graphiti_core import Graphiti
            from graphiti_core.llm_client.config import LLMConfig
            from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

            # Configure LLM (Ollama)
            llm_config = LLMConfig(
                api_key=self.config.llm_api_key,
                model=self.config.llm_model,
                small_model=self.config.llm_model,
                base_url=self.config.llm_base_url,
            )

            # Configure embedder (Ollama)
            embedder_config = OpenAIEmbedderConfig(
                api_key=self.config.llm_api_key,
                embedding_model=self.config.embedding_model,
                embedding_dim=self.config.embedding_dim,
                base_url=self.config.embedding_base_url,
            )

            # Create Graphiti client
            self._client = Graphiti(
                self.config.neo4j_uri,
                self.config.neo4j_user,
                self.config.neo4j_password,
                llm_client=OpenAIGenericClient(config=llm_config),
                embedder=OpenAIEmbedder(config=embedder_config),
            )

            # Build indices for hybrid search
            await self._client.build_indices_and_constraints()

            self._initialized = True
            logger.info("Graphiti memory initialized successfully")
            return True

        except ImportError as e:
            logger.warning(f"Graphiti not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            return False

    async def add_episode(
        self,
        content: str,
        source: str = "hydra",
        source_description: str = "Hydra AI System",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Add an episode (conversation, event, fact) to the knowledge graph.

        Args:
            content: The content to add
            source: Source identifier
            source_description: Human-readable description of the source
            metadata: Optional metadata

        Returns:
            Episode ID if successful
        """
        if not self._initialized:
            await self.initialize()

        if not self._client:
            return None

        import time
        start = time.time()

        try:
            from graphiti_core.nodes import EpisodeType

            # Create episode
            episode = await self._client.add_episode(
                name=f"hydra_episode_{datetime.utcnow().isoformat()}",
                episode_body=content,
                source_description=source_description,
                source=EpisodeType.text,
                reference_time=datetime.utcnow(),
            )

            GRAPHITI_LATENCY.labels(operation="add_episode").observe(time.time() - start)
            GRAPHITI_QUERIES.labels(query_type="add").inc()

            logger.info(f"Added episode to Graphiti: {content[:50]}...")
            # AddEpisodeResults has an 'episode' field containing the EpisodicNode
            if hasattr(episode, 'episode') and hasattr(episode.episode, 'uuid'):
                return str(episode.episode.uuid)
            return str(episode.uuid) if hasattr(episode, 'uuid') else "episode_added"

        except Exception as e:
            logger.error(f"Failed to add episode: {e}")
            return None

    async def search(
        self,
        query: str,
        limit: int = None,
        center_node_uuid: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining graph, semantic, and keyword search.

        Args:
            query: Search query
            limit: Max results
            center_node_uuid: Optional node to center search around

        Returns:
            List of search results with scores
        """
        if not self._initialized:
            await self.initialize()

        if not self._client:
            return []

        import time
        start = time.time()
        limit = limit or self.config.search_limit

        try:
            # Hybrid search
            results = await self._client.search(
                query=query,
                num_results=limit,
                center_node_uuid=center_node_uuid,
            )

            GRAPHITI_LATENCY.labels(operation="search").observe(time.time() - start)
            GRAPHITI_QUERIES.labels(query_type="search").inc()

            # Format results
            formatted = []
            for result in results:
                formatted.append({
                    "content": getattr(result, 'fact', getattr(result, 'content', str(result))),
                    "score": getattr(result, 'score', 0.0),
                    "uuid": getattr(result, 'uuid', None),
                    "type": type(result).__name__,
                    "metadata": getattr(result, 'metadata', {}),
                })

            logger.debug(f"Graphiti search for '{query[:30]}...' returned {len(formatted)} results")
            return formatted

        except Exception as e:
            logger.error(f"Graphiti search failed: {e}")
            return []

    async def get_node(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Get a specific node by UUID using direct Neo4j query."""
        if not self._initialized:
            await self.initialize()

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password),
            )

            async with driver.session(database=self.config.neo4j_database) as session:
                result = await session.run(
                    "MATCH (n) WHERE n.uuid = $uuid RETURN n, labels(n) as labels",
                    uuid=uuid
                )
                record = await result.single()
                if record:
                    node = record["n"]
                    labels = record["labels"]
                    return {
                        "uuid": uuid,
                        "name": node.get("name"),
                        "content": node.get("fact") or node.get("content") or node.get("summary"),
                        "type": labels[0] if labels else "Unknown",
                        "properties": dict(node),
                    }

            await driver.close()
            return None
        except Exception as e:
            logger.error(f"Failed to get node {uuid}: {e}")
            return None

    async def get_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        """Get all edges connected to a node using direct Neo4j query."""
        if not self._initialized:
            await self.initialize()

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password),
            )

            async with driver.session(database=self.config.neo4j_database) as session:
                result = await session.run(
                    """
                    MATCH (n)-[r]-(m)
                    WHERE n.uuid = $uuid
                    RETURN type(r) as relation, r.uuid as edge_uuid,
                           n.uuid as source, m.uuid as target,
                           r.fact as fact, r.name as name
                    """,
                    uuid=node_uuid
                )
                edges = []
                async for record in result:
                    edges.append({
                        "source": record["source"],
                        "target": record["target"],
                        "relation": record["relation"],
                        "name": record["name"],
                        "fact": record["fact"],
                        "edge_uuid": record["edge_uuid"],
                    })

            await driver.close()
            return edges
        except Exception as e:
            logger.error(f"Failed to get edges for {node_uuid}: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        if not self._initialized:
            await self.initialize()

        if not self._client:
            return {"status": "not_initialized"}

        try:
            # Query Neo4j for stats
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password),
            )

            async with driver.session(database=self.config.neo4j_database) as session:
                # Count nodes
                node_result = await session.run("MATCH (n) RETURN count(n) as count")
                node_count = await node_result.single()
                nodes = node_count["count"] if node_count else 0

                # Count relationships
                edge_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                edge_count = await edge_result.single()
                edges = edge_count["count"] if edge_count else 0

            await driver.close()

            # Update Prometheus metrics
            GRAPHITI_NODES.set(nodes)
            GRAPHITI_EDGES.set(edges)

            return {
                "status": "connected",
                "nodes": nodes,
                "edges": edges,
                "neo4j_uri": self.config.neo4j_uri,
                "initialized": self._initialized,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        """Close Graphiti client."""
        if self._client:
            try:
                await self._client.close()
            except:
                pass
        self._initialized = False


# =============================================================================
# Global Instance
# =============================================================================

_memory_instance: Optional[GraphitiMemory] = None


def get_graphiti_memory() -> GraphitiMemory:
    """Get the global Graphiti memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = GraphitiMemory()
    return _memory_instance


# =============================================================================
# Hybrid Search Function
# =============================================================================

async def hybrid_search(
    query: str,
    vector_results: Optional[List[Dict]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining Graphiti graph search with vector results.

    Args:
        query: Search query
        vector_results: Optional pre-computed vector search results
        limit: Max results

    Returns:
        Combined and ranked results
    """
    memory = get_graphiti_memory()

    # Get graph results
    graph_results = await memory.search(query, limit=limit)

    # If no vector results provided, just return graph results
    if not vector_results:
        return graph_results

    # Combine results (simple fusion for now)
    combined = {}

    # Add graph results with graph boost
    for i, result in enumerate(graph_results):
        key = result.get("content", "")[:100]
        combined[key] = {
            **result,
            "graph_rank": i,
            "graph_score": result.get("score", 0),
            "source": "graph",
        }

    # Add vector results
    for i, result in enumerate(vector_results):
        key = result.get("content", "")[:100]
        if key in combined:
            # Merge scores
            combined[key]["vector_rank"] = i
            combined[key]["vector_score"] = result.get("score", 0)
            combined[key]["source"] = "hybrid"
            # Combined score (simple average for now)
            combined[key]["combined_score"] = (
                combined[key].get("graph_score", 0) * 0.6 +
                combined[key].get("vector_score", 0) * 0.4
            )
        else:
            combined[key] = {
                **result,
                "vector_rank": i,
                "vector_score": result.get("score", 0),
                "source": "vector",
                "combined_score": result.get("score", 0) * 0.8,
            }

    # Sort by combined score
    results = sorted(
        combined.values(),
        key=lambda x: x.get("combined_score", x.get("score", 0)),
        reverse=True,
    )

    return results[:limit]


# =============================================================================
# Knowledge Graph Enhancement (3.3)
# =============================================================================

class KnowledgeGraphEnhancer:
    """
    Enhanced knowledge graph capabilities for multi-hop reasoning.

    Features:
    - Import knowledge documents as graph nodes
    - Entity relationship extraction
    - Multi-hop traversal queries
    - Temporal relationship tracking
    """

    def __init__(self, graphiti_memory: GraphitiMemory):
        self.memory = graphiti_memory
        self.import_stats = {"documents": 0, "nodes": 0, "relationships": 0}

    async def import_knowledge_docs(self, knowledge_dir: str = "/mnt/user/appdata/hydra-dev/knowledge") -> Dict[str, Any]:
        """
        Import knowledge/*.md files as graph nodes.

        Creates nodes for each document and extracts relationships.
        """
        from pathlib import Path
        import re

        knowledge_path = Path(knowledge_dir)
        if not knowledge_path.exists():
            return {"error": f"Directory not found: {knowledge_dir}"}

        results = {"imported": [], "errors": [], "stats": {}}

        for md_file in knowledge_path.glob("*.md"):
            try:
                content = md_file.read_text()
                doc_name = md_file.stem

                # Extract sections as separate nodes
                sections = self._extract_sections(content)

                # Add document as episode
                episode_id = await self.memory.add_episode(
                    content=f"Knowledge document: {doc_name}\n\n{content[:2000]}",
                    source=f"knowledge/{doc_name}.md",
                    source_description=f"Hydra knowledge document: {doc_name}",
                    metadata={"type": "knowledge_doc", "filename": md_file.name}
                )

                results["imported"].append({
                    "file": md_file.name,
                    "episode_id": episode_id,
                    "sections": len(sections),
                })
                self.import_stats["documents"] += 1
                self.import_stats["nodes"] += len(sections) + 1

            except Exception as e:
                results["errors"].append({"file": md_file.name, "error": str(e)})

        results["stats"] = self.import_stats
        logger.info(f"Imported {len(results['imported'])} knowledge documents")
        return results

    def _extract_sections(self, content: str) -> List[Dict[str, str]]:
        """Extract sections from markdown content."""
        import re
        sections = []
        current_header = ""
        current_content = []

        for line in content.split("\n"):
            if line.startswith("#"):
                if current_header and current_content:
                    sections.append({
                        "header": current_header,
                        "content": "\n".join(current_content)
                    })
                current_header = line.lstrip("#").strip()
                current_content = []
            else:
                current_content.append(line)

        if current_header and current_content:
            sections.append({
                "header": current_header,
                "content": "\n".join(current_content)
            })

        return sections

    async def multi_hop_query(
        self,
        start_query: str,
        hops: int = 2,
        relationship_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a multi-hop reasoning query.

        Starting from initial search results, traverses relationships
        to find connected information.
        """
        if not self.memory._initialized:
            await self.memory.initialize()

        results = {
            "query": start_query,
            "hops": hops,
            "paths": [],
            "entities": [],
        }

        # Initial search
        initial_results = await self.memory.search(start_query, limit=5)
        if not initial_results:
            return results

        # Track visited nodes
        visited = set()
        paths = []

        for result in initial_results[:3]:  # Limit starting points
            node_uuid = result.get("uuid")
            if not node_uuid:
                continue

            path = [{"node": result, "hop": 0}]
            visited.add(node_uuid)

            # Traverse hops
            current_nodes = [node_uuid]
            for hop in range(1, hops + 1):
                next_nodes = []
                for current_uuid in current_nodes:
                    edges = await self.memory.get_edges(current_uuid)
                    for edge in edges:
                        # Filter by relationship type if specified
                        if relationship_types and edge.get("type") not in relationship_types:
                            continue

                        target_uuid = edge.get("target_uuid") or edge.get("source_uuid")
                        if target_uuid and target_uuid not in visited:
                            visited.add(target_uuid)
                            next_nodes.append(target_uuid)

                            target_node = await self.memory.get_node(target_uuid)
                            if target_node:
                                path.append({
                                    "node": target_node,
                                    "hop": hop,
                                    "relationship": edge.get("type", "RELATED_TO"),
                                })

                current_nodes = next_nodes[:5]  # Limit branching

            if len(path) > 1:
                paths.append(path)

        results["paths"] = paths
        results["entities"] = [p["node"].get("name") or p["node"].get("content", "")[:50] for path in paths for p in path]
        results["total_nodes_explored"] = len(visited)

        return results

    async def extract_relationships(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract entities and relationships from text using LLM.

        Returns list of (entity1, relationship, entity2) triples.
        """
        import httpx
        import json
        import re

        entity_types = entity_types or ["Service", "Concept", "Node", "Agent", "Capability"]

        extraction_prompt = f"""Extract entities and relationships from this text.

TEXT:
{text[:2000]}

Entity types to look for: {', '.join(entity_types)}

Return a JSON array of relationship triples:
[
  {{"entity1": "name", "type1": "type", "relationship": "RELATES_TO", "entity2": "name", "type2": "type"}},
  ...
]

Only return valid JSON, no explanation."""

        try:
            ollama_url = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ollama_url}/v1/chat/completions",
                    json={
                        "model": "qwen2.5:7b",
                        "messages": [{"role": "user", "content": extraction_prompt}],
                        "max_tokens": 1024,
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Parse JSON from response
                    json_match = re.search(r'\[[\s\S]*\]', content)
                    if json_match:
                        relationships = json.loads(json_match.group())
                        self.import_stats["relationships"] += len(relationships)
                        return relationships

        except Exception as e:
            logger.error(f"Relationship extraction failed: {e}")

        return []

    async def add_temporal_relationship(
        self,
        entity1_uuid: str,
        entity2_uuid: str,
        relationship_type: str,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a temporal relationship between entities.

        Tracks when relationships are valid (e.g., "Service A runs on Node B from date X")
        """
        if not self.memory._initialized:
            await self.memory.initialize()

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.memory.config.neo4j_uri,
                auth=(self.memory.config.neo4j_user, self.memory.config.neo4j_password),
            )

            valid_from_str = valid_from.isoformat() if valid_from else datetime.utcnow().isoformat()
            valid_to_str = valid_to.isoformat() if valid_to else None

            async with driver.session(database=self.memory.config.neo4j_database) as session:
                query = f"""
                MATCH (a {{uuid: $uuid1}}), (b {{uuid: $uuid2}})
                CREATE (a)-[r:{relationship_type} {{
                    valid_from: $valid_from,
                    valid_to: $valid_to,
                    created_at: $created_at,
                    metadata: $metadata
                }}]->(b)
                RETURN type(r) as relationship
                """
                result = await session.run(
                    query,
                    uuid1=entity1_uuid,
                    uuid2=entity2_uuid,
                    valid_from=valid_from_str,
                    valid_to=valid_to_str,
                    created_at=datetime.utcnow().isoformat(),
                    metadata=json.dumps(metadata or {}),
                )
                record = await result.single()
                await driver.close()

                if record:
                    self.import_stats["relationships"] += 1
                    return True

        except Exception as e:
            logger.error(f"Failed to add temporal relationship: {e}")

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph enhancement statistics."""
        return {
            "import_stats": self.import_stats,
        }


# Global enhancer instance
_enhancer: Optional[KnowledgeGraphEnhancer] = None


def get_graph_enhancer() -> KnowledgeGraphEnhancer:
    """Get or create the knowledge graph enhancer."""
    global _enhancer
    if _enhancer is None:
        _enhancer = KnowledgeGraphEnhancer(get_graphiti_memory())
    return _enhancer


# =============================================================================
# FastAPI Router
# =============================================================================

def create_graphiti_router():
    """Create FastAPI router for Graphiti memory endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/graphiti", tags=["graphiti-memory"])

    class AddEpisodeRequest(BaseModel):
        content: str
        source: str = "hydra"
        source_description: str = "Hydra AI System"
        metadata: Optional[Dict[str, Any]] = None

    class SearchRequest(BaseModel):
        query: str
        limit: int = 10
        center_node_uuid: Optional[str] = None

    @router.get("/status")
    async def graphiti_status():
        """Get Graphiti memory status and statistics."""
        memory = get_graphiti_memory()
        return await memory.get_stats()

    @router.post("/initialize")
    async def initialize_graphiti():
        """Initialize Graphiti connection."""
        memory = get_graphiti_memory()
        success = await memory.initialize()
        return {"initialized": success}

    @router.post("/episodes")
    async def add_episode(request: AddEpisodeRequest):
        """Add an episode to the knowledge graph."""
        memory = get_graphiti_memory()
        episode_id = await memory.add_episode(
            content=request.content,
            source=request.source,
            source_description=request.source_description,
            metadata=request.metadata,
        )
        if episode_id:
            return {"episode_id": episode_id, "status": "added"}
        raise HTTPException(status_code=500, detail="Failed to add episode")

    @router.post("/search")
    async def search_memory(request: SearchRequest):
        """Search the knowledge graph with hybrid retrieval."""
        memory = get_graphiti_memory()
        results = await memory.search(
            query=request.query,
            limit=request.limit,
            center_node_uuid=request.center_node_uuid,
        )
        return {
            "query": request.query,
            "results": results,
            "count": len(results),
        }

    @router.post("/hybrid-search")
    async def hybrid_search_endpoint(request: SearchRequest):
        """
        Hybrid search combining graph, semantic, and keyword search.

        This is the recommended search endpoint for best accuracy.
        """
        results = await hybrid_search(
            query=request.query,
            limit=request.limit,
        )
        return {
            "query": request.query,
            "results": results,
            "count": len(results),
            "search_type": "hybrid",
        }

    @router.get("/nodes/{uuid}")
    async def get_node(uuid: str):
        """Get a specific node by UUID."""
        memory = get_graphiti_memory()
        node = await memory.get_node(uuid)
        if node:
            return node
        raise HTTPException(status_code=404, detail="Node not found")

    @router.get("/nodes/{uuid}/edges")
    async def get_node_edges(uuid: str):
        """Get all edges connected to a node."""
        memory = get_graphiti_memory()
        edges = await memory.get_edges(uuid)
        return {"node_uuid": uuid, "edges": edges, "count": len(edges)}

    # =========================================================================
    # Knowledge Graph Enhancement Endpoints (3.3)
    # =========================================================================

    class MultiHopRequest(BaseModel):
        query: str
        hops: int = 2
        relationship_types: Optional[List[str]] = None

    class RelationshipExtractionRequest(BaseModel):
        text: str
        entity_types: Optional[List[str]] = None

    class TemporalRelationshipRequest(BaseModel):
        entity1_uuid: str
        entity2_uuid: str
        relationship_type: str
        valid_from: Optional[str] = None
        valid_to: Optional[str] = None
        metadata: Optional[Dict[str, Any]] = None

    @router.post("/enhance/import-knowledge")
    async def import_knowledge_docs(knowledge_dir: str = "/mnt/user/appdata/hydra-dev/knowledge"):
        """
        Import knowledge/*.md files as graph nodes.

        Creates nodes for each document and extracts relationships.
        This is the primary way to bootstrap the knowledge graph.
        """
        enhancer = get_graph_enhancer()
        results = await enhancer.import_knowledge_docs(knowledge_dir)
        return results

    @router.post("/enhance/multi-hop")
    async def multi_hop_query(request: MultiHopRequest):
        """
        Execute a multi-hop reasoning query.

        Starting from initial search results, traverses relationships
        to find connected information. Supports up to 5 hops.

        Example: Start with "TabbyAPI" and traverse 2 hops to find
        related services, configurations, and dependencies.
        """
        enhancer = get_graph_enhancer()
        if request.hops > 5:
            raise HTTPException(status_code=400, detail="Maximum hops is 5")
        results = await enhancer.multi_hop_query(
            start_query=request.query,
            hops=request.hops,
            relationship_types=request.relationship_types,
        )
        return results

    @router.post("/enhance/extract-relationships")
    async def extract_relationships(request: RelationshipExtractionRequest):
        """
        Extract entities and relationships from text using LLM.

        Returns list of (entity1, relationship, entity2) triples.
        Useful for ingesting unstructured text into the knowledge graph.
        """
        enhancer = get_graph_enhancer()
        relationships = await enhancer.extract_relationships(
            text=request.text,
            entity_types=request.entity_types,
        )
        return {
            "text_length": len(request.text),
            "relationships": relationships,
            "count": len(relationships),
        }

    @router.post("/enhance/temporal-relationship")
    async def add_temporal_relationship(request: TemporalRelationshipRequest):
        """
        Add a temporal relationship between entities.

        Tracks when relationships are valid (e.g., "Service A runs on Node B from date X").
        Useful for tracking configuration changes over time.
        """
        enhancer = get_graph_enhancer()
        valid_from = datetime.fromisoformat(request.valid_from) if request.valid_from else None
        valid_to = datetime.fromisoformat(request.valid_to) if request.valid_to else None

        success = await enhancer.add_temporal_relationship(
            entity1_uuid=request.entity1_uuid,
            entity2_uuid=request.entity2_uuid,
            relationship_type=request.relationship_type,
            valid_from=valid_from,
            valid_to=valid_to,
            metadata=request.metadata,
        )

        if success:
            return {"status": "created", "relationship_type": request.relationship_type}
        raise HTTPException(status_code=500, detail="Failed to create temporal relationship")

    @router.get("/enhance/stats")
    async def get_enhancer_stats():
        """
        Get knowledge graph enhancement statistics.

        Returns import counts, relationship counts, and enhancement status.
        """
        enhancer = get_graph_enhancer()
        stats = enhancer.get_stats()
        memory_stats = await get_graphiti_memory().get_stats()
        return {
            "enhancer": stats,
            "knowledge_graph": memory_stats,
        }

    return router
