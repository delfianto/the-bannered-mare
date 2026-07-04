"""Live model discovery + load/unload for local providers (Ollama, LM Studio).

Sync `httpx.Client` throughout — matches this module's existing sync-only
style (routes stay `def`, FastAPI runs them in its threadpool), consistent
with `ProviderService`/`ProviderRepository` being sync everywhere except
chat messages.
"""

from typing import Protocol

import httpx

from src.core.persistence.enums import ProviderType
from src.provider.adapters.lmstudio import strip_v1_suffix
from src.provider.schemas import DiscoveredModel

_LIST_TIMEOUT = 10.0
_LOAD_TIMEOUT = 120.0


class ModelDiscoveryClient(Protocol):
    """Queries a local provider's native API for its model inventory."""

    def list_models(self, base_url: str) -> list[DiscoveredModel]:
        """Return every model installed on the server, with load state."""
        ...

    def load_model(self, base_url: str, identifier: str) -> None:
        """Load a model into memory."""
        ...

    def unload_model(self, base_url: str, identifier: str) -> None:
        """Unload a model from memory."""
        ...


class OllamaDiscoveryClient:
    """Ollama's native API: /api/tags (installed), /api/ps (loaded)."""

    def list_models(self, base_url: str) -> list[DiscoveredModel]:
        clean_url = base_url.rstrip("/")
        with httpx.Client(timeout=_LIST_TIMEOUT) as client:
            tags_resp = client.get(f"{clean_url}/api/tags")
            tags_resp.raise_for_status()
            ps_resp = client.get(f"{clean_url}/api/ps")
            ps_resp.raise_for_status()

        loaded_names = {m["model"] for m in ps_resp.json().get("models", [])}

        models: list[DiscoveredModel] = []
        for m in tags_resp.json().get("models", []):
            details = m.get("details") or {}
            models.append(
                DiscoveredModel(
                    identifier=m["model"],
                    display_name=m.get("name", m["model"]),
                    state="loaded" if m["model"] in loaded_names else "not-loaded",
                    size_bytes=m.get("size"),
                    quantization=details.get("quantization_level"),
                    max_context_length=None,  # requires a per-model /api/show call
                )
            )
        return models

    def load_model(self, base_url: str, identifier: str) -> None:
        self._generate(base_url, identifier, keep_alive=-1)

    def unload_model(self, base_url: str, identifier: str) -> None:
        self._generate(base_url, identifier, keep_alive=0)

    def _generate(self, base_url: str, identifier: str, keep_alive: int) -> None:
        clean_url = base_url.rstrip("/")
        with httpx.Client(timeout=_LOAD_TIMEOUT) as client:
            resp = client.post(
                f"{clean_url}/api/generate",
                json={"model": identifier, "prompt": "", "keep_alive": keep_alive},
            )
            resp.raise_for_status()


class LMStudioDiscoveryClient:
    """LM Studio's native v1 REST API (0.4.0+): /api/v1/models[/load|/unload]."""

    def list_models(self, base_url: str) -> list[DiscoveredModel]:
        clean_url = strip_v1_suffix(base_url)
        with httpx.Client(timeout=_LIST_TIMEOUT) as client:
            resp = client.get(f"{clean_url}/api/v1/models")
            resp.raise_for_status()

        models: list[DiscoveredModel] = []
        for m in resp.json().get("models", []):
            quantization = m.get("quantization") or {}
            models.append(
                DiscoveredModel(
                    identifier=m["key"],
                    display_name=m.get("display_name", m["key"]),
                    state="loaded" if m.get("loaded_instances") else "not-loaded",
                    size_bytes=m.get("size_bytes"),
                    quantization=quantization.get("name"),
                    max_context_length=m.get("max_context_length"),
                )
            )
        return models

    def load_model(self, base_url: str, identifier: str) -> None:
        clean_url = strip_v1_suffix(base_url)
        with httpx.Client(timeout=_LOAD_TIMEOUT) as client:
            resp = client.post(f"{clean_url}/api/v1/models/load", json={"model": identifier})
            resp.raise_for_status()

    def unload_model(self, base_url: str, identifier: str) -> None:
        clean_url = strip_v1_suffix(base_url)
        with httpx.Client(timeout=_LOAD_TIMEOUT) as client:
            resp = client.post(
                f"{clean_url}/api/v1/models/unload", json={"instance_id": identifier}
            )
            resp.raise_for_status()


_REGISTRY: dict[ProviderType, ModelDiscoveryClient] = {
    ProviderType.OLLAMA: OllamaDiscoveryClient(),
    ProviderType.LMSTUDIO: LMStudioDiscoveryClient(),
}


def get_discovery_client(provider_type: ProviderType) -> ModelDiscoveryClient | None:
    """Look up the discovery client for a provider type, if it supports one."""
    return _REGISTRY.get(provider_type)
