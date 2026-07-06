"""Async data access layer for Embedding entities (vector queries)"""

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.persistence import AsyncBaseRepository
from src.rag.models import Embedding


class AsyncEmbeddingRepository(AsyncBaseRepository[Embedding]):
    """Async repository for Embedding data access with vector search"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Embedding)

    async def exists_by_hash(self, content_hash: int, source_type: str) -> bool:
        """Check if an embedding with this hash + source type already exists."""
        stmt = select(Embedding.id).where(
            Embedding.content_hash == content_hash,
            Embedding.source_type == source_type,
        )
        result = await self.db.execute(stmt)
        return result.first() is not None

    async def find_by_source(self, source_type: str, source_id: str) -> list[Embedding]:
        """Find all embeddings for a given source."""
        stmt = (
            select(Embedding)
            .where(Embedding.source_type == source_type, Embedding.source_id == source_id)
            .order_by(Embedding.chunk_index)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
    ) -> list[dict]:
        """Semantic similarity search using pgvector cosine distance.

        Args:
            query_embedding: The query vector.
            source_types: List of source types to filter on.
            source_ids: List of source IDs to filter on.
            limit: Maximum number of results.
            threshold: Minimum similarity score (0-1).

        Returns:
            List of dicts with id, content, source_type, source_id, chunk_index, score.
        """
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
