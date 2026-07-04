"""In-process TTL cache for auto-detected provider model lists.

Process-local and in-memory by design (no Redis in this stack — mirrors
OpenWebUI's own in-memory model-list cache). Lost on restart, which is fine:
the next request just does a live fetch and repopulates it.
"""

from dataclasses import dataclass
from datetime import datetime

from src.core.persistence.base_model import utc_now
from src.provider.schemas import DiscoveredModel


@dataclass
class _CacheEntry:
    fetched_at: datetime
    models: list[DiscoveredModel]


class ModelListCache:
    """Keyed by provider_id. Not thread-safe beyond CPython's GIL guarantees,
    which is sufficient here since entries are replaced wholesale, never mutated."""

    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}

    def get(self, provider_id: str, ttl_seconds: int) -> list[DiscoveredModel] | None:
        entry = self._entries.get(provider_id)
        if entry is None:
            return None
        if (utc_now() - entry.fetched_at).total_seconds() > ttl_seconds:
            return None
        return entry.models

    def set(self, provider_id: str, models: list[DiscoveredModel]) -> None:
        self._entries[provider_id] = _CacheEntry(fetched_at=utc_now(), models=models)

    def invalidate(self, provider_id: str) -> None:
        self._entries.pop(provider_id, None)


_cache = ModelListCache()


def get_model_list_cache() -> ModelListCache:
    """FastAPI dependency returning the process-wide cache singleton."""
    return _cache
