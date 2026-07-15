"""Provider model discovery, caching, and runtime actions.

Split out of ``ProviderService``: provider *entity* CRUD stays there; this
service owns everything about a provider's model *catalog* — discovery + the
persistent list cache, search/allow-list filtering, and the local-provider
load/unload/delete runtime actions. The pure filter rules live in
``discovery_filters.py``.
"""

from typing import Literal

import httpx

from src.core.base_service import get_or_404
from src.core.config import settings
from src.core.exceptions import ProviderException, ValidationError
from src.core.logging import get_logger
from src.core.persistence import UnitOfWork
from src.core.persistence.base_model import utc_now
from src.provider.discovery import get_discovery_client
from src.provider.discovery_filters import (
    apply_allow_list,
    dedupe_preserving_order,
    filter_blacklisted,
)
from src.provider.model_cache import ModelListCache
from src.provider.models import Provider, ProviderType
from src.provider.repository import ProviderRepository
from src.provider.schemas import (
    AvailableModelsResponse,
    DiscoveredModel,
    ModelActionResponse,
    ModelSearchResponse,
)

logger = get_logger(__name__)

# Cap search hits so a broad query (e.g. against OpenRouter's ~300 models)
# returns a UI-friendly slice rather than the whole catalog.
_SEARCH_RESULT_LIMIT = 50

# Local providers (Ollama / LM Studio) expose a live "loaded" state that flips
# whenever a model is loaded/unloaded in the provider's own UI — outside this
# app, so the discovery cache can't be invalidated for it. Their catalogs are
# small and on the LAN, so we always fetch them fresh rather than serving a
# stale cached state (falling back to the cache only if the box is unreachable).
_LOCAL_PROVIDER_TYPES = frozenset({ProviderType.OLLAMA, ProviderType.LMSTUDIO})


class ProviderModelService:
    """Discovery, caching, filtering, and runtime actions for a provider's models."""

    def __init__(
        self,
        provider_repo: ProviderRepository,
        model_cache: ModelListCache,
        uow: UnitOfWork | None = None,
    ):
        # Fallback keeps direct construction (tests) valid; the DI factory relies
        # on it too (same request-scoped session as the repo).
        self.repo = provider_repo
        self.model_cache = model_cache
        self.uow = uow or UnitOfWork(provider_repo.db)

    def _get_provider(self, provider_id: str) -> Provider:
        return get_or_404(self.repo, provider_id, "Provider")

    def list_available_models(
        self, provider_id: str, *, force_refresh: bool = False
    ) -> AvailableModelsResponse:
        """List a provider's models, narrowed by its curated allow-list.

        Serves from the persistent cache (memory + disk on STORAGE_PATH) even
        when stale, so this is near-instant; a live provider fetch happens only
        on a cold cache or when force_refresh (Sync) is set, which also updates
        last_synced_at. When ``allowed_models`` is non-empty, only those
        identifiers are returned; otherwise the full discovered list is.
        """
        provider = self._get_provider(provider_id)
        models, from_cache = self._fetch_discovered_models(provider, force_refresh=force_refresh)
        return AvailableModelsResponse(
            provider_id=provider_id,
            models=apply_allow_list(provider.allowed_models, models),
            last_synced_at=provider.last_synced_at,
            from_cache=from_cache,
        )

    def sync_models(self, provider_id: str) -> AvailableModelsResponse:
        """Force a live refresh of a provider's model list, bypassing the cache."""
        return self.list_available_models(provider_id, force_refresh=True)

    def search_models(self, provider_id: str, query: str) -> ModelSearchResponse:
        """Search the provider's full live list by substring (identifier or name).

        Deliberately ignores the allow-list: this feeds the picker used to
        *build* that filter, so every candidate must be visible. Results are
        capped to keep the response and the UI dropdown manageable.
        """
        provider = self._get_provider(provider_id)
        models, _ = self._fetch_discovered_models(provider, force_refresh=False)

        needle = query.strip().lower()
        if needle:
            models = [
                m
                for m in models
                if needle in m.identifier.lower() or needle in m.display_name.lower()
            ]
        models = sorted(models, key=lambda m: m.identifier)[:_SEARCH_RESULT_LIMIT]
        return ModelSearchResponse(provider_id=provider_id, query=query, models=models)

    def set_allowed_models(
        self, provider_id: str, allowed_models: list[str]
    ) -> AvailableModelsResponse:
        """Persist the curated allow-list and return the newly-filtered list."""
        provider = self._get_provider(provider_id)
        provider.allowed_models = dedupe_preserving_order(allowed_models)
        self.repo.update(provider)
        self.uow.commit()

        # Reuse the cache — changing the filter never needs a fresh provider call.
        models, from_cache = self._fetch_discovered_models(provider, force_refresh=False)
        return AvailableModelsResponse(
            provider_id=provider_id,
            models=apply_allow_list(provider.allowed_models, models),
            last_synced_at=provider.last_synced_at,
            from_cache=from_cache,
        )

    def _fetch_discovered_models(
        self, provider: Provider, *, force_refresh: bool
    ) -> tuple[list[DiscoveredModel], bool]:
        """Return the full (blacklist-filtered) discovered list and a cache flag.

        Shared by the available/sync/search/filter paths. For cloud providers,
        reads serve the cached list (stale included) and hit the API only on a
        cold cache or force_refresh. Local providers (Ollama/LM Studio) are always
        fetched fresh so their live "loaded" state is accurate even when a model
        was (un)loaded outside the app; the cache is used only as a fallback when
        the local box is unreachable.
        """
        client = get_discovery_client(provider.provider_type)
        if client is None:
            raise ValidationError(
                f"{provider.provider_type.value} does not support model auto-detection"
            )

        is_local = provider.provider_type in _LOCAL_PROVIDER_TYPES

        if not force_refresh and not is_local and settings.discovery_cache.enabled:
            cached = self.model_cache.get(provider.id)
            if cached is not None:
                return filter_blacklisted(cached), True

        try:
            api_key = provider.get_api_key()
            models = client.list_models(provider.get_base_url(), api_key=api_key)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
            # A briefly-unreachable local box shouldn't blank the picker — serve
            # the last-known list if we have one.
            if is_local and settings.discovery_cache.enabled:
                cached = self.model_cache.get(provider.id)
                if cached is not None:
                    return filter_blacklisted(cached), True
            raise self._unreachable(provider, e) from e

        provider.last_synced_at = utc_now()
        self.repo.update(provider)
        self.uow.commit()

        # Cache the raw discovered list; the blacklist is applied on the way out
        # so editing settings.model_blacklist takes effect without a re-sync.
        if settings.discovery_cache.enabled:
            self.model_cache.set(provider.id, models)

        return filter_blacklisted(models), False

    def _unreachable(self, provider: Provider, error: Exception) -> ProviderException:
        """502 for an unreachable provider. Logs the upstream detail server-side;
        the client message stays generic (the raw error can carry the
        base_url/credentials and aids SSRF recon)."""
        logger.warning("provider_unreachable", provider=provider.name, error=str(error))
        return ProviderException(f"Could not reach provider '{provider.name}'.")

    def _run_model_action(
        self,
        provider_id: str,
        model_identifier: str,
        *,
        method: str,
        verb: Literal["loaded", "unloaded", "deleted"],
        unsupported_noun: str,
    ) -> ModelActionResponse:
        """Run a load/unload/delete runtime action against a local provider's
        discovery client (they share the same resolve → guard → call → invalidate
        flow). ``method`` is the client method, ``verb`` the response action."""
        provider = self._get_provider(provider_id)
        client = get_discovery_client(provider.provider_type)
        if client is None:
            raise ValidationError(
                f"{provider.provider_type.value} does not support model {unsupported_noun}"
            )

        try:
            getattr(client, method)(provider.get_base_url(), model_identifier)
        except NotImplementedError as e:
            raise ValidationError(str(e)) from e
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
            raise self._unreachable(provider, e) from e

        self.model_cache.invalidate(provider_id)
        return ModelActionResponse(model_identifier=model_identifier, action=verb)

    def load_model(self, provider_id: str, model_identifier: str) -> ModelActionResponse:
        """Load a model into memory on a local provider."""
        return self._run_model_action(
            provider_id,
            model_identifier,
            method="load_model",
            verb="loaded",
            unsupported_noun="loading",
        )

    def unload_model(self, provider_id: str, model_identifier: str) -> ModelActionResponse:
        """Unload a model from memory on a local provider."""
        return self._run_model_action(
            provider_id,
            model_identifier,
            method="unload_model",
            verb="unloaded",
            unsupported_noun="unloading",
        )

    def delete_model(self, provider_id: str, model_identifier: str) -> ModelActionResponse:
        """Delete/remove a model from a local provider's filesystem/registry."""
        return self._run_model_action(
            provider_id,
            model_identifier,
            method="delete_model",
            verb="deleted",
            unsupported_noun="management",
        )
