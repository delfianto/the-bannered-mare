"""Provider business logic service"""

import re
from typing import Literal

import httpx

from src.core.base_service import BaseCrudService, apply_update
from src.core.config import settings
from src.core.exceptions import ConflictError, ProviderException, ValidationError
from src.core.logging import get_logger
from src.core.persistence import UnitOfWork
from src.core.persistence.base_model import utc_now
from src.provider.discovery import get_discovery_client
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

# OpenAI o-series reasoning models (o1, o3-mini, o4-mini, …). Matched as a
# name-segment prefix — not a loose "o1" substring, which would also hit RP
# finetunes like "sao10k/…" — so these deep-thinking, pricey models stay out of
# the RP picker.
_REASONING_MODEL_RE = re.compile(r"^o[1-9]([.-]|$)")

# Local providers (Ollama / LM Studio) expose a live "loaded" state that flips
# whenever a model is loaded/unloaded in the provider's own UI — outside this
# app, so the discovery cache can't be invalidated for it. Their catalogs are
# small and on the LAN, so we always fetch them fresh rather than serving a
# stale cached state (falling back to the cache only if the box is unreachable).
_LOCAL_PROVIDER_TYPES = frozenset({ProviderType.OLLAMA, ProviderType.LMSTUDIO})

# OpenAI ships dated GPT snapshots (gpt-5-2025-08-07, gpt-5.4-2026-03-05)
# alongside the bare/rolling id they pin, so they only clutter the RP picker —
# drop them. NOT the "-chat-latest" aliases: those are the *only* callable form
# of the chat SKUs (there is no bare "gpt-5-chat"), so they must stay. Scoped to
# gpt/chatgpt so other vendors' dated names (e.g. Claude's) are untouched.
_OPENAI_ALIAS_RE = re.compile(r"^(?:chat)?gpt.*-\d{4}-\d{2}-\d{2}$")


def _dedupe_preserving_order(identifiers: list[str]) -> list[str]:
    """Trim, drop blanks, and de-duplicate while keeping first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in identifiers:
        value = raw.strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


_EDITABLE = {"name", "base_url", "api_key_env_var", "enabled"}


class ProviderService(BaseCrudService[Provider, ProviderRepository]):
    """Service for provider-related business logic (inherits get_by_id)."""

    def __init__(
        self,
        provider_repo: ProviderRepository,
        model_cache: ModelListCache,
        uow: UnitOfWork | None = None,
    ):
        # Fallback keeps direct `ProviderService(...)` construction (tests) valid —
        # the DI factory injects the request-scoped UoW.
        super().__init__(provider_repo, uow or UnitOfWork(provider_repo.db), "Provider")
        self.model_cache = model_cache

    def list_all(self) -> list[Provider]:
        """List all providers (insertion order)."""
        return self.repo.find_all()

    def create(
        self,
        name: str,
        provider_type: ProviderType,
        base_url: str | None = None,
        api_key_env_var: str | None = None,
    ) -> Provider:
        """Create a new provider"""
        if provider_type == ProviderType.CUSTOM:
            if not api_key_env_var:
                raise ValidationError("Custom providers must specify api_key_env_var")

            if not re.match(r"^[A-Z][A-Z0-9_]*$", api_key_env_var):
                raise ValidationError(
                    "Invalid api_key_env_var format. Must be uppercase with "
                    "underscores (e.g., MY_CUSTOM_API_KEY)"
                )

            if not base_url:
                raise ValidationError("Custom providers must specify base_url")

        elif api_key_env_var:
            raise ValidationError(
                f"Cannot specify api_key_env_var for {provider_type.value} provider. "
                f"This provider uses predefined environment variable"
            )

        existing = self.repo.find_by_name(name)
        if existing:
            raise ConflictError(f"Provider with name '{name}' already exists")

        provider = Provider(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_env_var=api_key_env_var,
        )

        created = self.repo.create(provider)
        self.uow.commit()

        if not created.has_api_key():
            env_var_name = created.get_env_var_name()
            logger.warning(
                f"Provider '{name}' created but API key not found. "
                + f"Set environment variable: {env_var_name}"
            )

        return created

    def update(
        self,
        provider_id: str,
        name: str | None = None,
        base_url: str | None = None,
        api_key_env_var: str | None = None,
        enabled: bool | None = None,
    ) -> Provider:
        """Update provider"""
        provider = self.get_by_id(provider_id)

        if api_key_env_var is not None:
            if provider.provider_type != ProviderType.CUSTOM:
                raise ValidationError(
                    f"Cannot update api_key_env_var for {provider.provider_type.value} "
                    f"provider. This provider uses predefined environment variable"
                )

            if not re.match(r"^[A-Z][A-Z0-9_]*$", api_key_env_var):
                raise ValidationError(
                    "Invalid api_key_env_var format. Must be uppercase with "
                    "underscores (e.g., MY_CUSTOM_API_KEY)"
                )

        patch = {
            "name": name,
            "base_url": base_url,
            "api_key_env_var": api_key_env_var,
            "enabled": enabled,
        }
        apply_update(provider, {k: v for k, v in patch.items() if v is not None}, _EDITABLE)

        updated = self.repo.update(provider)
        self.uow.commit()
        return updated

    def update_flags(self, provider_id: str, enabled: bool) -> Provider:
        """Update provider enabled/disabled state"""
        provider = self.get_by_id(provider_id)
        provider.enabled = enabled
        updated = self.repo.update(provider)
        self.uow.commit()

        logger.info(
            "provider_flags_updated",
            provider_id=provider_id,
            enabled=enabled,
        )
        return updated

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
        provider = self.get_by_id(provider_id)
        models, from_cache = self._fetch_discovered_models(provider, force_refresh=force_refresh)
        return AvailableModelsResponse(
            provider_id=provider_id,
            models=self._apply_allow_list(provider, models),
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
        provider = self.get_by_id(provider_id)
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
        provider = self.get_by_id(provider_id)
        provider.allowed_models = _dedupe_preserving_order(allowed_models)
        self.repo.update(provider)
        self.uow.commit()

        # Reuse the cache — changing the filter never needs a fresh provider call.
        models, from_cache = self._fetch_discovered_models(provider, force_refresh=False)
        return AvailableModelsResponse(
            provider_id=provider_id,
            models=self._apply_allow_list(provider, models),
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
                return self._filter_blacklisted(cached), True

        try:
            api_key = provider.get_api_key()
            models = client.list_models(provider.get_base_url(), api_key=api_key)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
            # A briefly-unreachable local box shouldn't blank the picker — serve
            # the last-known list if we have one.
            if is_local and settings.discovery_cache.enabled:
                cached = self.model_cache.get(provider.id)
                if cached is not None:
                    return self._filter_blacklisted(cached), True
            raise self._unreachable(provider, e) from e

        provider.last_synced_at = utc_now()
        self.repo.update(provider)
        self.uow.commit()

        # Cache the raw discovered list; the blacklist is applied on the way out
        # so editing settings.model_blacklist takes effect without a re-sync.
        if settings.discovery_cache.enabled:
            self.model_cache.set(provider.id, models)

        return self._filter_blacklisted(models), False

    @staticmethod
    def _filter_blacklisted(models: list[DiscoveredModel]) -> list[DiscoveredModel]:
        """Drop non-chat/non-RP models via three configurable rules.

        The identifier splits as ``vendor/name`` (or just ``name`` for
        vendor-less providers like OpenAI). Rules:
        - ``settings.model_vendor_blacklist`` substrings vs the **vendor** —
          whole vendors dropped (Perplexity, Cohere, OpenRouter meta-routers…).
        - ``settings.model_blacklist`` substrings vs the **name** only (not the
          vendor, so ``sao10k/l3.3-euryale-70b`` isn't nuked for the "o1" in
          "sao10k"; and not the display name, which may read "Research Preview"
          on a fine chat model).
        - the OpenAI o-series reasoning models (o1/o3/o4…) by name prefix.
        - OpenAI's redundant GPT "-latest"/dated-snapshot aliases by name.
        """
        name_bl = [k.lower() for k in settings.model_blacklist]
        vendor_bl = [k.lower() for k in settings.model_vendor_blacklist]
        kept: list[DiscoveredModel] = []
        for m in models:
            vendor, _, name = m.identifier.lower().rpartition("/")
            if vendor and any(v in vendor for v in vendor_bl):
                continue
            if _REASONING_MODEL_RE.match(name):
                continue
            if _OPENAI_ALIAS_RE.match(name):
                continue
            if any(k in name for k in name_bl):
                continue
            kept.append(m)
        return kept

    @staticmethod
    def _apply_allow_list(
        provider: Provider, models: list[DiscoveredModel]
    ) -> list[DiscoveredModel]:
        """Keep only allow-listed identifiers; an empty allow-list keeps all."""
        allowed = set(provider.allowed_models or [])
        if not allowed:
            return models
        return [m for m in models if m.identifier in allowed]

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
        provider = self.get_by_id(provider_id)
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

    def delete(self, provider_id: str) -> None:
        """Providers cannot be deleted (referential integrity); disable instead.

        Raises a domain ``ConflictError`` (→ HTTP 409) rather than
        ``NotImplementedError`` so that, if ever routed, it maps cleanly through
        the global handler instead of surfacing as an unhandled 500.
        """
        raise ConflictError(
            "Providers cannot be deleted. Use update_flags to disable the provider instead."
        )
