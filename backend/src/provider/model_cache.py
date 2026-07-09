"""Persistent cache for auto-detected provider model lists.

An in-memory dict (L1) backed by one JSON file per provider under STORAGE_PATH
(L2). The list is served even when stale, so opening a provider is instant; a
live provider fetch happens only on a cold cache (never fetched) or an explicit
Sync. Surviving restarts is the point — the previous in-memory-only cache with a
short TTL re-fetched (blocking, seconds for large providers like OpenAI) on
every process start and every TTL expiry.
"""

import contextlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.core.config import settings
from src.core.persistence.base_model import utc_now
from src.provider.schemas import DiscoveredModel


@dataclass
class _CacheEntry:
    fetched_at: datetime
    models: list[DiscoveredModel]


class ModelListCache:
    """Keyed by provider_id. Not thread-safe beyond CPython's GIL guarantees,
    which is sufficient here since entries are replaced wholesale, never mutated."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        # cache_dir=None → memory-only (per-instance default, used in tests).
        # The production singleton passes a dir so the list survives restarts.
        self._entries: dict[str, _CacheEntry] = {}
        self._dir = cache_dir

    def _path(self, provider_id: str) -> Path | None:
        return self._dir / f"{provider_id}.json" if self._dir is not None else None

    def get(self, provider_id: str) -> list[DiscoveredModel] | None:
        """Return the cached list (memory, then disk), stale or not.

        Returns None only when the provider has never been fetched, which is the
        sole case that triggers a live blocking fetch. Freshness is refreshed
        explicitly via Sync (force_refresh) or on load/unload/delete invalidation.
        """
        entry = self._entries.get(provider_id)
        if entry is not None:
            return entry.models
        path = self._path(provider_id)
        if path is None:
            return None
        # Disk fallback — hydrate memory so subsequent reads skip the file.
        try:
            raw = json.loads(path.read_text())
            models = [DiscoveredModel(**m) for m in raw["models"]]
        except OSError, ValueError, KeyError:
            return None
        self._entries[provider_id] = _CacheEntry(fetched_at=utc_now(), models=models)
        return models

    def set(self, provider_id: str, models: list[DiscoveredModel]) -> None:
        self._entries[provider_id] = _CacheEntry(fetched_at=utc_now(), models=models)
        path = self._path(provider_id)
        if path is None:
            return
        # A cache-write failure must never break discovery.
        with contextlib.suppress(OSError):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"models": [m.model_dump() for m in models]}))

    def invalidate(self, provider_id: str) -> None:
        self._entries.pop(provider_id, None)
        path = self._path(provider_id)
        if path is not None:
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)


_cache = ModelListCache(Path(settings.storage_path) / "model_cache")


def get_model_list_cache() -> ModelListCache:
    """FastAPI dependency returning the process-wide cache singleton."""
    return _cache
