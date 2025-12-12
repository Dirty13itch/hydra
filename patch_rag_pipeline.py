#!/usr/bin/env python3
"""Patch script to add full RAG pipeline capabilities to MCP server.

This adds:
- Document ingestion endpoint
- RAG query endpoint (search + LLM completion)
- Collection management endpoints
- Document deletion
"""

import re

RAG_PIPELINE_CODE = '''
# =============================================================================
# RAG Pipeline (Retrieval-Augmented Generation)
# =============================================================================

from pydantic import BaseModel
from typing import List, Optional
import hashlib

class DocumentIngest(BaseModel):
    text: str
    metadata: Optional[dict] = None
    collection: str = "hydra_knowledge"

class RAGQuery(BaseModel):
    query: str
    collection: str = "hydra_knowledge"
    top_k: int = 5
    model: str = "hydra-70b"
    max_tokens: int = 1000
    system_prompt: Optional[str] = None

# Embedding service URL (Ollama with nomic-embed-text)
EMBED_URL = "http://192.168.1.203:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text:latest"

async def get_embedding(text: str) -> List[float]:
    """Get embedding vector for text using Ollama"""
    try:
        r = await client.post(
            EMBED_URL,
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30.0
        )
        if r.status_code == 200:
            return r.json().get("embedding", [])
        return []
    except Exception:
        return []


@app.get("/rag/collections")
async def list_rag_collections():
    """List all Qdrant collections with stats"""
    try:
        r = await client.get(f"{QDRANT_URL}/collections")
        if r.status_code != 200:
            return {"error": "Failed to list collections"}

        collections = r.json().get("result", {}).get("collections", [])
        result = []

        for col in collections:
            name = col.get("name")
            # Get collection info
            info_r = await client.get(f"{QDRANT_URL}/collections/{name}")
            if info_r.status_code == 200:
                info = info_r.json().get("result", {})
                result.append({
                    "name": name,
                    "vectors_count": info.get("vectors_count", 0),
                    "points_count": info.get("points_count", 0),
                    "status": info.get("status", "unknown")
                })
            else:
                result.append({"name": name, "error": "Failed to get info"})

        return {"collections": result}
    except Exception as e:
        return {"error": str(e)}


@app.post("/rag/collections/{collection_name}")
async def create_rag_collection(collection_name: str, vector_size: int = 768):
    """Create a new Qdrant collection for RAG"""
    try:
        payload = {
            "vectors": {
                "size": vector_size,
                "distance": "Cosine"
            }
        }
        r = await client.put(
            f"{QDRANT_URL}/collections/{collection_name}",
            json=payload
        )
        if r.status_code in (200, 201):
            add_audit_entry("rag", {"action": "create_collection", "name": collection_name}, "success", "system")
            return {"status": "created", "collection": collection_name}
        return {"error": f"Failed to create: {r.status_code}", "detail": r.text}
    except Exception as e:
        return {"error": str(e)}


@app.post("/rag/ingest")
async def ingest_document(doc: DocumentIngest, request: Request = None):
    """Ingest a document into Qdrant for RAG"""
    ip = request.client.host if request and request.client else "unknown"

    try:
        # Generate embedding
        embedding = await get_embedding(doc.text)
        if not embedding:
            return {"error": "Failed to generate embedding"}

        # Generate unique ID from content hash
        doc_id = int(hashlib.md5(doc.text.encode()).hexdigest()[:8], 16)

        # Prepare payload
        payload = {
            "text": doc.text,
            "ingested_at": datetime.now().isoformat(),
            **(doc.metadata or {})
        }

        # Upsert to Qdrant
        r = await client.put(
            f"{QDRANT_URL}/collections/{doc.collection}/points",
            json={
                "points": [{
                    "id": doc_id,
                    "vector": embedding,
                    "payload": payload
                }]
            }
        )

        if r.status_code in (200, 201):
            add_audit_entry("rag", {
                "action": "ingest",
                "collection": doc.collection,
                "text_length": len(doc.text),
                "doc_id": doc_id
            }, "success", ip)
            return {"status": "ingested", "doc_id": doc_id, "collection": doc.collection}

        return {"error": f"Failed to ingest: {r.status_code}"}
    except Exception as e:
        add_audit_entry("rag", {"action": "ingest", "error": str(e)}, "error", ip)
        return {"error": str(e)}


@app.post("/rag/ingest/batch")
async def ingest_documents_batch(documents: List[DocumentIngest], request: Request = None):
    """Batch ingest multiple documents"""
    ip = request.client.host if request and request.client else "unknown"
    results = []

    for doc in documents:
        try:
            embedding = await get_embedding(doc.text)
            if not embedding:
                results.append({"status": "error", "error": "embedding failed"})
                continue

            doc_id = int(hashlib.md5(doc.text.encode()).hexdigest()[:8], 16)
            payload = {
                "text": doc.text,
                "ingested_at": datetime.now().isoformat(),
                **(doc.metadata or {})
            }

            r = await client.put(
                f"{QDRANT_URL}/collections/{doc.collection}/points",
                json={"points": [{"id": doc_id, "vector": embedding, "payload": payload}]}
            )

            if r.status_code in (200, 201):
                results.append({"status": "ok", "doc_id": doc_id})
            else:
                results.append({"status": "error", "error": f"qdrant: {r.status_code}"})
        except Exception as e:
            results.append({"status": "error", "error": str(e)})

    success_count = sum(1 for r in results if r.get("status") == "ok")
    add_audit_entry("rag", {
        "action": "batch_ingest",
        "total": len(documents),
        "success": success_count
    }, "success" if success_count > 0 else "error", ip)

    return {"results": results, "success_count": success_count, "total": len(documents)}


@app.post("/rag/query")
async def rag_query(query: RAGQuery, request: Request = None):
    """RAG query: retrieve relevant documents and generate response"""
    ip = request.client.host if request and request.client else "unknown"
    start_time = time.time()

    try:
        # Step 1: Get query embedding
        query_embedding = await get_embedding(query.query)
        if not query_embedding:
            return {"error": "Failed to generate query embedding"}

        # Step 2: Search Qdrant for relevant documents
        search_r = await client.post(
            f"{QDRANT_URL}/collections/{query.collection}/points/search",
            json={
                "vector": query_embedding,
                "limit": query.top_k,
                "with_payload": True
            }
        )

        if search_r.status_code != 200:
            return {"error": f"Search failed: {search_r.status_code}"}

        results = search_r.json().get("result", [])

        if not results:
            return {
                "answer": "I couldn't find any relevant information in the knowledge base.",
                "sources": [],
                "latency_seconds": round(time.time() - start_time, 3)
            }

        # Step 3: Build context from retrieved documents
        context_parts = []
        sources = []
        for i, r in enumerate(results, 1):
            text = r.get("payload", {}).get("text", "")
            score = r.get("score", 0)
            if text:
                context_parts.append(f"[Source {i}]: {text}")
                sources.append({
                    "text": text[:200] + "..." if len(text) > 200 else text,
                    "score": round(score, 4),
                    "metadata": {k: v for k, v in r.get("payload", {}).items() if k != "text"}
                })

        context = "\\n\\n".join(context_parts)

        # Step 4: Generate response using LLM
        system_prompt = query.system_prompt or """You are a helpful AI assistant with access to a knowledge base.
Answer the user's question based on the provided context. If the context doesn't contain
relevant information, say so. Always be accurate and cite your sources when possible."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Context from knowledge base:
{context}

Question: {query.query}

Please answer based on the context provided."""}
        ]

        headers = {
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json"
        }

        llm_r = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers=headers,
            json={
                "model": query.model,
                "messages": messages,
                "max_tokens": query.max_tokens,
                "temperature": 0.7
            },
            timeout=120.0
        )

        latency = time.time() - start_time

        if llm_r.status_code != 200:
            return {
                "error": f"LLM request failed: {llm_r.status_code}",
                "sources": sources,
                "latency_seconds": round(latency, 3)
            }

        llm_result = llm_r.json()
        answer = llm_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = llm_result.get("usage", {})

        add_audit_entry("rag", {
            "action": "query",
            "collection": query.collection,
            "query_length": len(query.query),
            "sources_found": len(sources),
            "model": query.model,
            "latency_seconds": round(latency, 3)
        }, "success", ip)

        return {
            "answer": answer,
            "sources": sources,
            "model": query.model,
            "usage": usage,
            "latency_seconds": round(latency, 3)
        }

    except Exception as e:
        add_audit_entry("rag", {"action": "query", "error": str(e)}, "error", ip)
        return {"error": str(e)}


@app.delete("/rag/documents/{collection}/{doc_id}")
async def delete_document(collection: str, doc_id: int, request: Request = None):
    """Delete a document from RAG collection"""
    ip = request.client.host if request and request.client else "unknown"

    try:
        r = await client.post(
            f"{QDRANT_URL}/collections/{collection}/points/delete",
            json={"points": [doc_id]}
        )

        if r.status_code in (200, 201):
            add_audit_entry("rag", {
                "action": "delete",
                "collection": collection,
                "doc_id": doc_id
            }, "success", ip)
            return {"status": "deleted", "doc_id": doc_id}

        return {"error": f"Delete failed: {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/rag/search")
async def enhanced_search(
    query: str,
    collection: str = "hydra_knowledge",
    limit: int = 10,
    score_threshold: float = 0.5
):
    """Enhanced semantic search with score filtering"""
    try:
        embedding = await get_embedding(query)
        if not embedding:
            return {"error": "Failed to generate embedding"}

        r = await client.post(
            f"{QDRANT_URL}/collections/{collection}/points/search",
            json={
                "vector": embedding,
                "limit": limit,
                "with_payload": True,
                "score_threshold": score_threshold
            }
        )

        if r.status_code != 200:
            return {"error": f"Search failed: {r.status_code}"}

        results = r.json().get("result", [])
        return {
            "results": [{
                "id": r.get("id"),
                "score": round(r.get("score", 0), 4),
                "text": r.get("payload", {}).get("text", ""),
                "metadata": {k: v for k, v in r.get("payload", {}).items() if k != "text"}
            } for r in results],
            "total": len(results),
            "collection": collection
        }
    except Exception as e:
        return {"error": str(e)}
'''

# Read the current server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "/rag/query" in content:
    print("RAG pipeline already exists - no patch needed")
    exit(0)

# Find insertion point - before WebSocket section or main
insert_markers = [
    "# =============================================================================\n# WebSocket",
    '# =============================================================================\n# Inference',
    'if __name__ == "__main__":'
]

inserted = False
for marker in insert_markers:
    pos = content.find(marker)
    if pos > 0:
        content = content[:pos] + RAG_PIPELINE_CODE + "\n\n" + content[pos:]
        print(f"Inserted RAG pipeline before: {marker[:40]}...")
        inserted = True
        break

if not inserted:
    # Append before main
    main_pos = content.find('if __name__')
    if main_pos > 0:
        content = content[:main_pos] + RAG_PIPELINE_CODE + "\n\n" + content[main_pos:]
        print("Inserted RAG pipeline before __main__")
        inserted = True

if not inserted:
    print("Could not find insertion point for RAG pipeline")
    exit(1)

# Write the updated file
with open("/app/mcp_server.py", "w") as f:
    f.write(content)

print("RAG pipeline patch applied successfully")
print(f"File size: {len(content)} bytes")
