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

    def list_models(self, base_url: str, api_key: str | None = None) -> list[DiscoveredModel]:
        """Return every model installed on the server, with load state."""
        ...

    def load_model(self, base_url: str, identifier: str) -> None:
        """Load a model into memory."""
        ...

    def unload_model(self, base_url: str, identifier: str) -> None:
        """Unload a model from memory."""
        ...

    def delete_model(self, base_url: str, identifier: str) -> None:
        """Delete/remove a model from the server."""
        ...


class OllamaDiscoveryClient:
    """Ollama's native API: /api/tags (installed), /api/ps (loaded)."""

    def list_models(self, base_url: str, api_key: str | None = None) -> list[DiscoveredModel]:
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

    def delete_model(self, base_url: str, identifier: str) -> None:
        clean_url = base_url.rstrip("/")
        with httpx.Client(timeout=_LIST_TIMEOUT) as client:
            resp = client.request(
                "DELETE",
                f"{clean_url}/api/delete",
                json={"name": identifier},
            )
            resp.raise_for_status()

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

    def list_models(self, base_url: str, api_key: str | None = None) -> list[DiscoveredModel]:
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

    def delete_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("LM Studio does not support model deletion via API")


# Canonical display casing for tokens that title()/capitalize() would mangle —
# acronyms (GPT, GLM) and CamelCase brand names (DeepSeek, MiniMax, MiMo).
_NAME_CASING = {
    "gpt": "GPT",
    "glm": "GLM",
    "deepseek": "DeepSeek",
    "minimax": "MiniMax",
    "mimo": "MiMo",
    "qwen": "Qwen",
    "tts": "TTS",
    "hd": "HD",
    "ai": "AI",
    "llm": "LLM",
}


# Longest-first so a fused brand splits on its longest known prefix.
_CASING_PREFIXES = sorted(_NAME_CASING, key=len, reverse=True)


def _humanize_model_id(model_id: str) -> str:
    """Best-effort friendly name for providers that only return raw ids (OpenAI).

    e.g. ``gpt-4o-mini`` -> ``GPT 4o Mini``. Version-ish tokens (``4o``, ``3.5``)
    are left as-is; a brand fused to its version (``qwen3.7`` -> ``Qwen 3.7``) is
    split; a leading vendor prefix (``vendor/model``) is dropped.
    """
    tail = model_id.rsplit("/", 1)[-1]
    words: list[str] = []
    for tok in tail.replace("_", "-").split("-"):
        low = tok.lower()
        if low in _NAME_CASING:
            words.append(_NAME_CASING[low])
            continue
        # Brand/acronym fused to a version tag, e.g. ``qwen3.7`` -> ``Qwen`` + ``3.7``.
        # The digit guard prevents false splits like ``airoboros`` (ai + roboros).
        fused = next(
            (
                p
                for p in _CASING_PREFIXES
                if low.startswith(p) and low[len(p) : len(p) + 1].isdigit()
            ),
            None,
        )
        if fused:
            words.append(_NAME_CASING[fused])
            words.append(tok[len(fused) :])
        elif tok[:1].isalpha() and not any(c.isdigit() for c in tok):
            words.append(tok.capitalize())
        else:
            words.append(tok)
    return " ".join(w for w in words if w)


class OpenAIDiscoveryClient:
    """OpenAI compatible model listing."""

    def list_models(self, base_url: str, api_key: str | None = None) -> list[DiscoveredModel]:
        clean_url = base_url.rstrip("/")
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        with httpx.Client(timeout=_LIST_TIMEOUT) as client:
            resp = client.get(f"{clean_url}/models", headers=headers)
            resp.raise_for_status()

        models: list[DiscoveredModel] = []
        for m in resp.json().get("data", []):
            model_id = m.get("id")
            if not model_id:
                continue
            # OpenRouter (and some OpenAI-compatible gateways) return a friendly
            # `name`; OpenAI's /v1/models returns only ids, so humanize those.
            friendly = m.get("name")
            models.append(
                DiscoveredModel(
                    identifier=model_id,
                    display_name=friendly or _humanize_model_id(model_id),
                    state="loaded",
                    size_bytes=None,
                    quantization=None,
                    max_context_length=None,
                )
            )
        return models

    def load_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support loading models")

    def unload_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support unloading models")

    def delete_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support deleting models")


class AnthropicDiscoveryClient:
    """Anthropic model listing."""

    def list_models(self, base_url: str, api_key: str | None = None) -> list[DiscoveredModel]:
        clean_url = base_url.rstrip("/")
        headers = {
            "anthropic-version": "2023-06-01",
        }
        if api_key:
            headers["x-api-key"] = api_key

        with httpx.Client(timeout=_LIST_TIMEOUT) as client:
            resp = client.get(f"{clean_url}/models", headers=headers)
            resp.raise_for_status()

        models: list[DiscoveredModel] = []
        for m in resp.json().get("data", []):
            model_id = m.get("id")
            if not model_id:
                continue
            models.append(
                DiscoveredModel(
                    identifier=model_id,
                    display_name=m.get("display_name", model_id),
                    state="loaded",
                    size_bytes=None,
                    quantization=None,
                    max_context_length=None,
                )
            )
        return models

    def load_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support loading models")

    def unload_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support unloading models")

    def delete_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support deleting models")


class GoogleDiscoveryClient:
    """Google Gemini model listing."""

    def list_models(self, base_url: str, api_key: str | None = None) -> list[DiscoveredModel]:
        clean_url = base_url.rstrip("/")
        params = {}
        if api_key:
            params["key"] = api_key

        with httpx.Client(timeout=_LIST_TIMEOUT) as client:
            resp = client.get(f"{clean_url}/v1beta/models", params=params)
            resp.raise_for_status()

        models: list[DiscoveredModel] = []
        for m in resp.json().get("models", []):
            name = m.get("name", "")
            if not name:
                continue
            display_name = name.split("/")[-1] if "/" in name else name
            models.append(
                DiscoveredModel(
                    identifier=name,
                    display_name=m.get("displayName", display_name),
                    state="loaded",
                    size_bytes=None,
                    quantization=None,
                    max_context_length=m.get("inputTokenLimit"),
                )
            )
        return models

    def load_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support loading models")

    def unload_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support unloading models")

    def delete_model(self, base_url: str, identifier: str) -> None:
        raise NotImplementedError("Cloud providers do not support deleting models")


_REGISTRY: dict[ProviderType, ModelDiscoveryClient] = {
    ProviderType.OLLAMA: OllamaDiscoveryClient(),
    ProviderType.LMSTUDIO: LMStudioDiscoveryClient(),
    ProviderType.OPENAI: OpenAIDiscoveryClient(),
    ProviderType.ANTHROPIC: AnthropicDiscoveryClient(),
    ProviderType.GOOGLE: GoogleDiscoveryClient(),
    ProviderType.OPENROUTER: OpenAIDiscoveryClient(),
    ProviderType.XAI: OpenAIDiscoveryClient(),
    ProviderType.OPENCODE: OpenAIDiscoveryClient(),
    ProviderType.OPENCODE_GO: OpenAIDiscoveryClient(),
    ProviderType.CUSTOM: OpenAIDiscoveryClient(),
}


def get_discovery_client(provider_type: ProviderType) -> ModelDiscoveryClient | None:
    """Look up the discovery client for a provider type, if it supports one."""
    return _REGISTRY.get(provider_type)
