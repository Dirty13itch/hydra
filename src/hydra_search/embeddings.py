"""
Embedding Generation for Hybrid Search

Supports multiple embedding providers:
- Ollama (default, local)
- OpenAI-compatible APIs
- Sentence Transformers (local)
"""

import asyncio
import logging
from typing import List, Optional, Union

import httpx

from .config import EmbeddingConfig

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    Embedding client with support for multiple providers.

    Default: Ollama with nomic-embed-text model on hydra-compute.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._model_loaded = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text.

        Args:
            text: Single text or list of texts to embed

        Returns:
            Single embedding vector or list of embedding vectors
        """
        if isinstance(text, str):
            return await self._embed_single(text)

        # Batch embedding
        return await self._embed_batch(text)

    async def _embed_single(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        if self.config.provider == "ollama":
            return await self._embed_ollama(text)
        elif self.config.provider == "openai":
            return await self._embed_openai(text)
        else:
            raise ValueError(f"Unknown embedding provider: {self.config.provider}")

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if self.config.provider == "ollama":
            # Ollama doesn't support batch embedding, process sequentially
            # but with some concurrency
            results = []
            for i in range(0, len(texts), self.config.batch_size):
                batch = texts[i : i + self.config.batch_size]
                batch_results = await asyncio.gather(
                    *[self._embed_ollama(t) for t in batch]
                )
                results.extend(batch_results)
            return results
        elif self.config.provider == "openai":
            return await self._embed_openai_batch(texts)
        else:
            raise ValueError(f"Unknown embedding provider: {self.config.provider}")

    async def _embed_ollama(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.config.ollama_url}/api/embeddings",
                json={
                    "model": self.config.model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding", [])

            if not embedding:
                logger.warning(f"Empty embedding returned for text: {text[:50]}...")
                return [0.0] * self.config.dimensions

            return embedding

        except httpx.HTTPError as e:
            logger.error(f"Ollama embedding error: {e}")
            raise

    async def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI-compatible API."""
        client = await self._get_client()

        # Use LiteLLM or direct OpenAI endpoint
        api_base = self.config.ollama_url.replace(":11434", ":4000")  # Default to LiteLLM

        try:
            response = await client.post(
                f"{api_base}/v1/embeddings",
                json={
                    "model": self.config.model,
                    "input": text,
                },
                headers={
                    "Authorization": "Bearer sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7",  # LiteLLM key
                },
            )
            response.raise_for_status()
            data = response.json()

            return data["data"][0]["embedding"]

        except httpx.HTTPError as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    async def _embed_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch using OpenAI-compatible API."""
        client = await self._get_client()

        api_base = self.config.ollama_url.replace(":11434", ":4000")

        try:
            response = await client.post(
                f"{api_base}/v1/embeddings",
                json={
                    "model": self.config.model,
                    "input": texts,
                },
                headers={
                    "Authorization": "Bearer sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7",
                },
            )
            response.raise_for_status()
            data = response.json()

            # Sort by index to maintain order
            embeddings_data = sorted(data["data"], key=lambda x: x["index"])
            return [e["embedding"] for e in embeddings_data]

        except httpx.HTTPError as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            raise

    async def ensure_model_loaded(self) -> bool:
        """
        Ensure embedding model is loaded (Ollama-specific).

        Returns True if model is ready, False otherwise.
        """
        if self._model_loaded:
            return True

        if self.config.provider != "ollama":
            self._model_loaded = True
            return True

        client = await self._get_client()

        try:
            # Check if model exists
            response = await client.get(f"{self.config.ollama_url}/api/tags")
            response.raise_for_status()
            data = response.json()

            models = [m["name"] for m in data.get("models", [])]

            if self.config.model not in models and f"{self.config.model}:latest" not in models:
                logger.info(f"Pulling embedding model: {self.config.model}")
                # Pull model
                pull_response = await client.post(
                    f"{self.config.ollama_url}/api/pull",
                    json={"name": self.config.model},
                    timeout=600.0,  # 10 minutes for model download
                )
                pull_response.raise_for_status()

            self._model_loaded = True
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to load embedding model: {e}")
            return False

    def get_dimensions(self) -> int:
        """Get embedding dimensions for current model."""
        # Common models and their dimensions
        dimensions_map = {
            "nomic-embed-text": 768,
            "all-minilm": 384,
            "mxbai-embed-large": 1024,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        model_name = self.config.model.split(":")[0]  # Remove tag if present
        return dimensions_map.get(model_name, self.config.dimensions)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Synchronous wrapper
class EmbeddingClientSync:
    """Synchronous wrapper for EmbeddingClient."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self._async_client = EmbeddingClient(config)

    def embed(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        return asyncio.run(self._async_client.embed(text))

    def ensure_model_loaded(self) -> bool:
        return asyncio.run(self._async_client.ensure_model_loaded())

    def get_dimensions(self) -> int:
        return self._async_client.get_dimensions()

    def close(self):
        asyncio.run(self._async_client.close())
