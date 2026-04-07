"""Async embedding service with Ollama and OpenAI-compatible adapters."""

import os

import httpx

from src.core.config import EmbeddingSettings

BATCH_SIZE = 10


class EmbeddingService:
    """Embeds text using a configured provider (Ollama or OpenAI-compatible)."""

    def __init__(self, settings: EmbeddingSettings):
        self.settings = settings

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using configured provider. Handles batching."""
        results: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            if self.settings.provider == "ollama":
                batch_results = await self._embed_ollama(batch)
            else:
                batch_results = await self._embed_openai(batch)
            results.extend(batch_results)
        return results

    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        """POST to Ollama /api/embed endpoint."""
        url = f"{self.settings.ollama_url}/api/embed"
        payload = {"model": self.settings.model, "input": texts}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """POST to OpenAI-compatible /v1/embeddings endpoint."""
        api_key = os.getenv(self.settings.openai_key_env, "")
        url = f"{self.settings.openai_url}/embeddings"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"model": self.settings.model, "input": texts}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
