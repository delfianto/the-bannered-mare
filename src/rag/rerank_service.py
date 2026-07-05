"""Async cross-encoder reranker over HF Text Embeddings Inference (TEI)."""

import httpx

from src.core.config import RerankSettings


class RerankService:
    """Reorders candidate passages by relevance via a TEI cross-encoder.

    TEI's rerank endpoint is native-only — there is no OpenAI-compatible route
    (text-embeddings-inference#683) — so this posts ``{"query", "texts"}`` to
    ``/rerank`` and reads back ``[{"index", "score"}, ...]`` sorted best-first.
    """

    def __init__(self, settings: RerankSettings):
        self.settings = settings

    async def rerank(self, query: str, texts: list[str], top_n: int) -> list[tuple[int, float]]:
        """Rank `texts` against `query`, returning (index, score) pairs best-first.

        Args:
            query: The search query.
            texts: Candidate passages to score.
            top_n: Maximum number of pairs to return.

        Returns:
            (index_into_texts, score) pairs, most-relevant first (length <= top_n).
            Scores are TEI's normalized relevance in [0, 1].
        """
        if not texts or top_n <= 0:
            return []

        url = f"{self.settings.huggingface_url}/rerank"
        payload = {"query": query, "texts": texts}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            ranked = response.json()  # [{"index": i, "score": s}, ...] sorted desc

        return [(item["index"], item["score"]) for item in ranked[:top_n]]
