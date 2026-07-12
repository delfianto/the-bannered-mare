"""Async data access layer for Embedding entities (vector queries)"""

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging.logger_config import get_logger
from src.core.persistence import AsyncBaseRepository
from src.rag.models import Embedding

logger = get_logger(__name__)


class AsyncEmbeddingRepository(AsyncBaseRepository[Embedding]):
    """Async repository for Embedding data access with vector search"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Embedding)

    async def _apply_vchordrq_tuning(
        self, epsilon: float | None, max_scan_tuples: int | None
    ) -> None:
        """Apply VectorChord vchordrq search GUCs for this transaction, best-effort.

        Each `SET LOCAL` runs inside its own savepoint so that a missing GUC (e.g.
        an older VectorChord, or SQLite in tests where this path is never hit on
        real PG) can never abort the surrounding retrieval transaction — it is
        skipped and the index falls back to its defaults. Values are typed
        (float/int) at the call site, so string interpolation here is safe.
        """
        for name, value in (
            ("vchordrq.epsilon", epsilon),
            ("vchordrq.max_scan_tuples", max_scan_tuples),
        ):
            if value is None:
                continue
            try:
                async with self.db.begin_nested():
                    await self.db.execute(text(f"SET LOCAL {name} = {value}"))
            except Exception:
                logger.debug("vchordrq_tuning_skipped", guc=name, exc_info=True)

    async def exists_by_hash(self, content_hash: int, source_type: str) -> bool:
        """Check if an embedding with this hash + source type already exists."""
        stmt = select(Embedding.id).where(
            Embedding.content_hash == content_hash,
            Embedding.source_type == source_type,
        )
        result = await self.db.execute(stmt)
        return result.first() is not None

    async def delete_by_source(self, source_type: str, source_id: str) -> None:
        """Delete all embeddings for a given source."""
        stmt = delete(Embedding).where(
            Embedding.source_type == source_type,
            Embedding.source_id == source_id,
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def search_similar(
        self,
        query_embedding: list[float],
        source_types: list[str],
        source_ids: list[str],
        limit: int,
        threshold: float,
        epsilon: float | None = None,
        max_scan_tuples: int | None = None,
    ) -> list[dict]:
        """Semantic similarity search over the VectorChord vchordrq cosine index.

        Ranks by the `<=>` cosine distance (`ORDER BY ... LIMIT`), the shape the
        vchordrq index accelerates, and keeps only hits at or above `threshold`.

        Args:
            query_embedding: The query vector.
            source_types: List of source types to filter on.
            source_ids: List of source IDs to filter on.
            limit: Maximum number of results.
            threshold: Minimum similarity score (0-1).
            epsilon: Optional vchordrq RaBitQ recall bound (SET LOCAL).
            max_scan_tuples: Optional vchordrq pre-filter scan cap (SET LOCAL).

        Returns:
            List of dicts with id, content, source_type, source_id, chunk_index, score.
        """
        await self._apply_vchordrq_tuning(epsilon, max_scan_tuples)

        query_vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        stmt = text("""
            SELECT id, content, source_type, source_id, chunk_index,
                   1 - (embedding <=> :query_vec) as score
            FROM embeddings
            WHERE source_type = ANY(:source_types)
            AND source_id = ANY(:source_ids)
            AND 1 - (embedding <=> :query_vec) >= :threshold
            ORDER BY embedding <=> :query_vec
            LIMIT :limit
        """)

        result = await self.db.execute(
            stmt,
            {
                "query_vec": query_vec_str,
                "source_types": source_types,
                "source_ids": source_ids,
                "threshold": threshold,
                "limit": limit,
            },
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
