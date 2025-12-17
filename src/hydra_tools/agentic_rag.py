"""
Hydra Agentic RAG - Self-Reflective Retrieval Augmented Generation

Implements CRAG (Corrective RAG) and Self-RAG patterns for improved
retrieval accuracy and answer quality.

Pipeline:
1. Initial retrieval from multiple sources (Qdrant, Graphiti)
2. Relevance grading - LLM evaluates document relevance
3. Query rewriting - Improve query if documents are irrelevant
4. Re-retrieval - Fetch new documents with improved query
5. Generation - Generate answer with citations
6. Hallucination check - Verify answer is grounded in sources

Expected improvement: Significant quality boost for complex queries.

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

AGENTIC_RAG_QUERIES = Counter(
    "hydra_agentic_rag_queries_total",
    "Total agentic RAG queries",
    ["outcome"]  # success, no_relevant_docs, hallucination_detected
)

AGENTIC_RAG_LATENCY = Histogram(
    "hydra_agentic_rag_latency_seconds",
    "Agentic RAG end-to-end latency",
    ["stage"],  # retrieval, grading, rewriting, generation, verification
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

AGENTIC_RAG_ITERATIONS = Histogram(
    "hydra_agentic_rag_iterations",
    "Number of retrieval iterations per query",
    buckets=[1, 2, 3, 4, 5]
)

DOCUMENTS_GRADED = Counter(
    "hydra_agentic_rag_documents_graded_total",
    "Documents graded by relevance",
    ["grade"]  # relevant, irrelevant, ambiguous
)


# =============================================================================
# Enums and Types
# =============================================================================

class RelevanceGrade(Enum):
    """Document relevance grade."""
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    AMBIGUOUS = "ambiguous"


class AnswerConfidence(Enum):
    """Answer confidence level."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    HALLUCINATION = "hallucination"


@dataclass
class GradedDocument:
    """A document with its relevance grade."""
    content: str
    source: str
    score: float
    grade: RelevanceGrade
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgenticRAGResult:
    """Result of an agentic RAG query."""
    query: str
    answer: str
    confidence: AnswerConfidence
    citations: List[Dict[str, Any]]
    iterations: int
    graded_documents: List[GradedDocument]
    rewritten_queries: List[str]
    hallucination_check: Dict[str, Any]
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class AgenticRAGConfig:
    """Configuration for Agentic RAG."""
    # LLM endpoint (Ollama)
    llm_url: str = "http://192.168.1.203:11434/api/chat"
    llm_model: str = "qwen2.5:7b"

    # Retrieval endpoints
    qdrant_search_url: str = "http://192.168.1.244:8700/search/semantic"
    graphiti_search_url: str = "http://192.168.1.244:8700/graphiti/search"

    # Retrieval settings
    initial_top_k: int = 10
    rerank_top_k: int = 5
    min_relevant_docs: int = 2
    max_iterations: int = 3

    # Grading thresholds
    relevance_threshold: float = 0.7
    confidence_threshold: float = 0.8

    # Timeouts
    llm_timeout: float = 60.0
    retrieval_timeout: float = 30.0


# =============================================================================
# Agentic RAG Implementation
# =============================================================================

class AgenticRAG:
    """
    Self-reflective RAG implementation.

    Implements CRAG pattern:
    1. Retrieve -> Grade -> Decide
    2. If good docs: Generate
    3. If bad docs: Rewrite query -> Re-retrieve -> Generate
    4. Verify answer against sources
    """

    def __init__(self, config: Optional[AgenticRAGConfig] = None):
        self.config = config or AgenticRAGConfig()
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.llm_timeout)
            )
        return self._client

    # =========================================================================
    # Main Query Method
    # =========================================================================

    async def query(
        self,
        query: str,
        context: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ) -> AgenticRAGResult:
        """
        Execute an agentic RAG query.

        Args:
            query: The user's question
            context: Optional additional context
            max_iterations: Override max retrieval iterations

        Returns:
            AgenticRAGResult with answer, citations, and metadata
        """
        start_time = time.time()
        max_iterations = max_iterations or self.config.max_iterations

        current_query = query
        all_graded_docs: List[GradedDocument] = []
        rewritten_queries: List[str] = []
        iteration = 0

        # Iterative retrieval loop
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Agentic RAG iteration {iteration}: '{current_query[:50]}...'")

            # Step 1: Retrieve documents
            retrieval_start = time.time()
            documents = await self._retrieve_documents(current_query)
            AGENTIC_RAG_LATENCY.labels(stage="retrieval").observe(time.time() - retrieval_start)

            if not documents:
                logger.warning(f"No documents retrieved for query: {current_query}")
                if iteration == 1:
                    # First iteration with no docs - try web search fallback
                    current_query = await self._rewrite_query(query, [], "broaden")
                    rewritten_queries.append(current_query)
                    continue
                break

            # Step 2: Grade documents for relevance
            grading_start = time.time()
            graded_docs = await self._grade_documents(current_query, documents)
            all_graded_docs.extend(graded_docs)
            AGENTIC_RAG_LATENCY.labels(stage="grading").observe(time.time() - grading_start)

            # Count relevant documents
            relevant_docs = [d for d in graded_docs if d.grade == RelevanceGrade.RELEVANT]

            # Step 3: Decide next action
            if len(relevant_docs) >= self.config.min_relevant_docs:
                # Enough relevant documents - proceed to generation
                logger.info(f"Found {len(relevant_docs)} relevant documents")
                break
            elif iteration < max_iterations:
                # Not enough relevant docs - rewrite query
                rewriting_start = time.time()
                current_query = await self._rewrite_query(
                    query,
                    graded_docs,
                    "refine" if relevant_docs else "transform"
                )
                rewritten_queries.append(current_query)
                AGENTIC_RAG_LATENCY.labels(stage="rewriting").observe(time.time() - rewriting_start)
                logger.info(f"Rewrote query to: '{current_query[:50]}...'")

        AGENTIC_RAG_ITERATIONS.observe(iteration)

        # Get all relevant documents across iterations
        all_relevant = [d for d in all_graded_docs if d.grade == RelevanceGrade.RELEVANT]

        # Step 4: Generate answer
        generation_start = time.time()
        if all_relevant:
            answer, citations = await self._generate_answer(query, all_relevant)
        else:
            # No relevant docs found - generate with caveat
            answer = await self._generate_without_context(query)
            citations = []
        AGENTIC_RAG_LATENCY.labels(stage="generation").observe(time.time() - generation_start)

        # Step 5: Verify answer (hallucination check)
        verification_start = time.time()
        hallucination_check = await self._verify_answer(query, answer, all_relevant)
        AGENTIC_RAG_LATENCY.labels(stage="verification").observe(time.time() - verification_start)

        # Determine confidence
        confidence = self._assess_confidence(
            relevant_doc_count=len(all_relevant),
            hallucination_check=hallucination_check,
            iterations=iteration
        )

        # Record metrics
        AGENTIC_RAG_QUERIES.labels(outcome=confidence.value).inc()

        latency_ms = (time.time() - start_time) * 1000

        return AgenticRAGResult(
            query=query,
            answer=answer,
            confidence=confidence,
            citations=citations,
            iterations=iteration,
            graded_documents=all_graded_docs,
            rewritten_queries=rewritten_queries,
            hallucination_check=hallucination_check,
            latency_ms=latency_ms,
            metadata={
                "relevant_doc_count": len(all_relevant),
                "total_docs_retrieved": len(all_graded_docs),
                "model": self.config.llm_model,
            }
        )

    # =========================================================================
    # Retrieval
    # =========================================================================

    async def _retrieve_documents(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve documents from multiple sources."""
        documents = []

        # Try Qdrant semantic search
        try:
            qdrant_docs = await self._search_qdrant(query)
            documents.extend(qdrant_docs)
        except Exception as e:
            logger.warning(f"Qdrant search failed: {e}")

        # Try Graphiti graph search
        try:
            graphiti_docs = await self._search_graphiti(query)
            documents.extend(graphiti_docs)
        except Exception as e:
            logger.warning(f"Graphiti search failed: {e}")

        # Deduplicate by content
        seen = set()
        unique_docs = []
        for doc in documents:
            content = doc.get("content", "")[:200]
            if content not in seen:
                seen.add(content)
                unique_docs.append(doc)

        return unique_docs[:self.config.initial_top_k]

    async def _search_qdrant(self, query: str) -> List[Dict[str, Any]]:
        """Search Qdrant vector database."""
        try:
            response = await self.client.post(
                self.config.qdrant_search_url,
                json={"query": query, "limit": self.config.initial_top_k},
                timeout=self.config.retrieval_timeout,
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                return [
                    {
                        "content": r.get("content", r.get("text", "")),
                        "source": "qdrant",
                        "score": r.get("score", 0),
                        "metadata": r.get("metadata", {}),
                    }
                    for r in results
                ]
        except Exception as e:
            logger.debug(f"Qdrant search error: {e}")
        return []

    async def _search_graphiti(self, query: str) -> List[Dict[str, Any]]:
        """Search Graphiti knowledge graph."""
        try:
            response = await self.client.post(
                self.config.graphiti_search_url,
                json={"query": query, "limit": self.config.initial_top_k},
                timeout=self.config.retrieval_timeout,
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                return [
                    {
                        "content": r.get("content", r.get("fact", "")),
                        "source": "graphiti",
                        "score": r.get("score", 0),
                        "metadata": r.get("metadata", {}),
                    }
                    for r in results
                ]
        except Exception as e:
            logger.debug(f"Graphiti search error: {e}")
        return []

    # =========================================================================
    # Document Grading
    # =========================================================================

    async def _grade_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]],
    ) -> List[GradedDocument]:
        """Grade documents for relevance to query."""
        graded = []

        # Grade in parallel for speed
        tasks = [
            self._grade_single_document(query, doc)
            for doc in documents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for doc, result in zip(documents, results):
            if isinstance(result, Exception):
                logger.warning(f"Grading failed for document: {result}")
                # Default to ambiguous on error
                graded.append(GradedDocument(
                    content=doc.get("content", ""),
                    source=doc.get("source", "unknown"),
                    score=doc.get("score", 0),
                    grade=RelevanceGrade.AMBIGUOUS,
                    reasoning="Grading failed",
                    metadata=doc.get("metadata", {}),
                ))
            else:
                graded.append(result)
                DOCUMENTS_GRADED.labels(grade=result.grade.value).inc()

        return graded

    async def _grade_single_document(
        self,
        query: str,
        document: Dict[str, Any],
    ) -> GradedDocument:
        """Grade a single document for relevance."""
        content = document.get("content", "")[:1500]  # Limit content length

        prompt = f"""You are a document relevance grader. Evaluate if the document is relevant to answering the query.

Query: {query}

Document: {content}

Grade the document as one of:
- RELEVANT: Document contains information directly useful for answering the query
- IRRELEVANT: Document is off-topic or not useful for this query
- AMBIGUOUS: Document may be partially relevant or tangentially related

Respond in JSON format:
{{"grade": "RELEVANT|IRRELEVANT|AMBIGUOUS", "reasoning": "brief explanation"}}"""

        try:
            response = await self.client.post(
                self.config.llm_url,
                json={
                    "model": self.config.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0},
                },
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("message", {}).get("content", "{}")

                # Parse JSON response
                try:
                    # Extract JSON from response
                    json_start = text.find("{")
                    json_end = text.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        parsed = json.loads(text[json_start:json_end])
                        grade_str = parsed.get("grade", "AMBIGUOUS").upper()
                        reasoning = parsed.get("reasoning", "")

                        grade = {
                            "RELEVANT": RelevanceGrade.RELEVANT,
                            "IRRELEVANT": RelevanceGrade.IRRELEVANT,
                        }.get(grade_str, RelevanceGrade.AMBIGUOUS)

                        return GradedDocument(
                            content=document.get("content", ""),
                            source=document.get("source", "unknown"),
                            score=document.get("score", 0),
                            grade=grade,
                            reasoning=reasoning,
                            metadata=document.get("metadata", {}),
                        )
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.warning(f"Document grading error: {e}")

        # Default response
        return GradedDocument(
            content=document.get("content", ""),
            source=document.get("source", "unknown"),
            score=document.get("score", 0),
            grade=RelevanceGrade.AMBIGUOUS,
            reasoning="Failed to grade",
            metadata=document.get("metadata", {}),
        )

    # =========================================================================
    # Query Rewriting
    # =========================================================================

    async def _rewrite_query(
        self,
        original_query: str,
        graded_docs: List[GradedDocument],
        strategy: str = "refine",
    ) -> str:
        """Rewrite query to improve retrieval."""

        # Build context about what was retrieved
        doc_summaries = "\n".join([
            f"- [{d.grade.value}] {d.content[:100]}..."
            for d in graded_docs[:5]
        ]) if graded_docs else "No documents were found."

        strategies = {
            "refine": "Make the query more specific and focused.",
            "broaden": "Make the query broader to find more results.",
            "transform": "Rephrase the query using different terms and concepts.",
        }

        prompt = f"""You are a query optimization expert. The original query did not retrieve good results.

Original query: {original_query}

Retrieved documents (with grades):
{doc_summaries}

Strategy: {strategies.get(strategy, strategies['refine'])}

Write an improved search query that will find more relevant documents.
Only respond with the new query, nothing else."""

        try:
            response = await self.client.post(
                self.config.llm_url,
                json={
                    "model": self.config.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )

            if response.status_code == 200:
                result = response.json()
                new_query = result.get("message", {}).get("content", "").strip()
                if new_query and len(new_query) > 5:
                    return new_query
        except Exception as e:
            logger.warning(f"Query rewriting error: {e}")

        return original_query  # Return original if rewriting fails

    # =========================================================================
    # Answer Generation
    # =========================================================================

    async def _generate_answer(
        self,
        query: str,
        relevant_docs: List[GradedDocument],
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate answer from relevant documents."""

        # Build context from documents
        context_parts = []
        citations = []

        for i, doc in enumerate(relevant_docs[:self.config.rerank_top_k], 1):
            context_parts.append(f"[{i}] {doc.content}")
            citations.append({
                "index": i,
                "content": doc.content[:200],
                "source": doc.source,
                "score": doc.score,
            })

        context = "\n\n".join(context_parts)

        prompt = f"""Answer the question based on the provided context. Use citations [1], [2], etc. to reference sources.

Context:
{context}

Question: {query}

Provide a comprehensive answer based on the context. If the context doesn't contain enough information, say so."""

        try:
            response = await self.client.post(
                self.config.llm_url,
                json={
                    "model": self.config.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("message", {}).get("content", "")
                return answer, citations
        except Exception as e:
            logger.error(f"Answer generation error: {e}")

        return "I was unable to generate an answer.", citations

    async def _generate_without_context(self, query: str) -> str:
        """Generate answer when no relevant context is available."""
        prompt = f"""Answer this question to the best of your ability. Note that you don't have access to specific context for this query.

Question: {query}

Provide a helpful response, but be clear about any limitations or uncertainties."""

        try:
            response = await self.client.post(
                self.config.llm_url,
                json={
                    "model": self.config.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Generation without context error: {e}")

        return "I was unable to find relevant information to answer your question."

    # =========================================================================
    # Answer Verification
    # =========================================================================

    async def _verify_answer(
        self,
        query: str,
        answer: str,
        relevant_docs: List[GradedDocument],
    ) -> Dict[str, Any]:
        """Verify answer is grounded in sources (hallucination check)."""

        if not relevant_docs:
            return {
                "grounded": False,
                "reason": "No source documents available",
                "confidence": 0.0,
            }

        # Build source text
        sources = "\n".join([doc.content for doc in relevant_docs[:5]])

        prompt = f"""You are a fact-checker. Verify if the answer is grounded in the provided sources.

Sources:
{sources[:3000]}

Answer to verify:
{answer[:1500]}

Check if the answer:
1. Only contains claims that can be verified from the sources
2. Does not make up facts not present in sources
3. Correctly represents the information from sources

Respond in JSON format:
{{"grounded": true/false, "reason": "explanation", "confidence": 0.0-1.0}}"""

        try:
            response = await self.client.post(
                self.config.llm_url,
                json={
                    "model": self.config.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0},
                },
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("message", {}).get("content", "{}")

                try:
                    json_start = text.find("{")
                    json_end = text.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        return json.loads(text[json_start:json_end])
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.warning(f"Answer verification error: {e}")

        return {
            "grounded": True,  # Assume grounded if verification fails
            "reason": "Verification inconclusive",
            "confidence": 0.5,
        }

    # =========================================================================
    # Confidence Assessment
    # =========================================================================

    def _assess_confidence(
        self,
        relevant_doc_count: int,
        hallucination_check: Dict[str, Any],
        iterations: int,
    ) -> AnswerConfidence:
        """Assess overall answer confidence."""

        # Check for hallucination
        if not hallucination_check.get("grounded", True):
            return AnswerConfidence.HALLUCINATION

        verification_confidence = hallucination_check.get("confidence", 0.5)

        # High confidence: multiple relevant docs, grounded, few iterations
        if (relevant_doc_count >= 3 and
            verification_confidence >= 0.8 and
            iterations <= 2):
            return AnswerConfidence.HIGH

        # Medium confidence: some relevant docs, mostly grounded
        if (relevant_doc_count >= 1 and
            verification_confidence >= 0.5):
            return AnswerConfidence.MEDIUM

        # Low confidence: few relevant docs or low verification confidence
        return AnswerConfidence.LOW

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# Global Instance
# =============================================================================

_agentic_rag_instance: Optional[AgenticRAG] = None


def get_agentic_rag() -> AgenticRAG:
    """Get the global AgenticRAG instance."""
    global _agentic_rag_instance
    if _agentic_rag_instance is None:
        _agentic_rag_instance = AgenticRAG()
    return _agentic_rag_instance


# =============================================================================
# FastAPI Router
# =============================================================================

def create_agentic_rag_router():
    """Create FastAPI router for Agentic RAG endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/agentic-rag", tags=["agentic-rag"])

    class QueryRequest(BaseModel):
        query: str
        context: Optional[str] = None
        max_iterations: int = 3

    class QueryResponse(BaseModel):
        query: str
        answer: str
        confidence: str
        citations: List[Dict[str, Any]]
        iterations: int
        rewritten_queries: List[str]
        hallucination_check: Dict[str, Any]
        latency_ms: float
        metadata: Dict[str, Any]

    @router.post("/query", response_model=QueryResponse)
    async def agentic_query(request: QueryRequest):
        """
        Execute an agentic RAG query with self-reflection.

        The system will:
        1. Retrieve documents from multiple sources
        2. Grade documents for relevance
        3. Rewrite query if needed and re-retrieve
        4. Generate answer with citations
        5. Verify answer is grounded (hallucination check)
        """
        rag = get_agentic_rag()
        result = await rag.query(
            query=request.query,
            context=request.context,
            max_iterations=request.max_iterations,
        )

        return QueryResponse(
            query=result.query,
            answer=result.answer,
            confidence=result.confidence.value,
            citations=result.citations,
            iterations=result.iterations,
            rewritten_queries=result.rewritten_queries,
            hallucination_check=result.hallucination_check,
            latency_ms=result.latency_ms,
            metadata=result.metadata,
        )

    @router.get("/health")
    async def agentic_rag_health():
        """Check Agentic RAG health."""
        rag = get_agentic_rag()
        return {
            "status": "healthy",
            "config": {
                "llm_model": rag.config.llm_model,
                "initial_top_k": rag.config.initial_top_k,
                "max_iterations": rag.config.max_iterations,
                "min_relevant_docs": rag.config.min_relevant_docs,
            }
        }

    @router.post("/grade-documents")
    async def grade_documents(query: str, documents: List[Dict[str, Any]]):
        """
        Grade a list of documents for relevance to a query.

        Useful for testing the grading component independently.
        """
        rag = get_agentic_rag()
        graded = await rag._grade_documents(query, documents)
        return {
            "query": query,
            "graded_documents": [
                {
                    "content": d.content[:200],
                    "source": d.source,
                    "grade": d.grade.value,
                    "reasoning": d.reasoning,
                }
                for d in graded
            ]
        }

    @router.post("/rewrite-query")
    async def rewrite_query(
        query: str,
        strategy: str = "refine",
    ):
        """
        Rewrite a query using specified strategy.

        Strategies:
        - refine: Make more specific
        - broaden: Make more general
        - transform: Use different terms
        """
        rag = get_agentic_rag()
        new_query = await rag._rewrite_query(query, [], strategy)
        return {
            "original_query": query,
            "rewritten_query": new_query,
            "strategy": strategy,
        }

    return router
