"""Async embedding service with llama.cpp, Ollama, and OpenAI-compatible adapters."""

import os

import httpx

from src.core.config import EmbeddingSettings

BATCH_SIZE = 10
# HTTP timeout for embedding-server calls (llama.cpp/Ollama/TEI can be slow on
# cold start or large batches).
HTTP_TIMEOUT_S = 60.0


class EmbeddingService:
    """Embeds text via the configured provider (llama.cpp, Ollama, or OpenAI-compatible).

    EmbeddingGemma (the default model) is asymmetric: a query and the documents it
    searches over are embedded with different prompt prefixes. Callers therefore pick
    `embed_query` or `embed_documents` rather than embedding both the same way.
    """

    def __init__(self, settings: EmbeddingSettings):
        self.settings = settings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query, applying the configured query prompt prefix."""
        vectors = await self._embed([text], self.settings.query_prefix)
        return vectors[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed stored chunks/documents, applying the configured document prompt prefix."""
        return await self._embed(texts, self.settings.document_prefix)

    async def _embed(self, texts: list[str], prefix: str) -> list[list[float]]:
        """Prefix each text, then embed in batches via the configured provider."""
        prefixed = [f"{prefix}{text}" for text in texts]
        results: list[list[float]] = []
        for i in range(0, len(prefixed), BATCH_SIZE):
            batch = prefixed[i : i + BATCH_SIZE]
            if self.settings.provider == "ollama":
                results.extend(await self._embed_ollama(batch))
            elif self.settings.provider == "huggingface":
                results.extend(await self._embed_hf(batch))
            elif self.settings.provider == "llamacpp":
                # llama-server exposes an OpenAI-compatible endpoint under /v1.
                base_url = f"{self.settings.llamacpp_url}/v1"
                results.extend(await self._embed_openai_compatible(batch, base_url))
            else:
                api_key = os.getenv(self.settings.openai_key_env, "")
                results.extend(
                    await self._embed_openai_compatible(batch, self.settings.openai_url, api_key)
                )
        return results

    async def _embed_hf(self, texts: list[str]) -> list[list[float]]:
        """POST to Text Embeddings Inference's native ``/embed`` endpoint.

        TEI exposes an OpenAI-compatible route for embeddings but NOT for
        reranking (text-embeddings-inference#683), so the ``huggingface``
        provider speaks TEI's native dialect — ``/embed`` here, ``/rerank`` for
        the reranker — rather than mixing two API shapes. Unlike the OpenAI
        format, the request key is ``inputs`` and the response is a bare list of
        float arrays (one per input), not ``{"data": [{"embedding": ...}]}``.
        """
        url = f"{self.settings.huggingface_url}/embed"
        # truncate guards against inputs longer than the model's context window
        # (queries are built from recent messages and can run long).
        payload = {"inputs": texts, "normalize": True, "truncate": True}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=HTTP_TIMEOUT_S)
            response.raise_for_status()
            return response.json()

    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        """POST to Ollama's native /api/embed endpoint."""
        url = f"{self.settings.ollama_url}/api/embed"
        payload = {"model": self.settings.model, "input": texts}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=HTTP_TIMEOUT_S)
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]

    async def _embed_openai_compatible(
        self, texts: list[str], base_url: str, api_key: str = ""
    ) -> list[list[float]]:
        """POST to an OpenAI-compatible /embeddings endpoint (OpenAI, vLLM, llama.cpp)."""
        url = f"{base_url}/embeddings"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        payload = {"model": self.settings.model, "input": texts}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=HTTP_TIMEOUT_S)
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
