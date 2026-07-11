"""Tests for local-provider model discovery/load/unload clients."""

from unittest.mock import MagicMock, patch

from src.core.persistence.enums import ProviderType
from src.provider.discovery import (
    AnthropicDiscoveryClient,
    GoogleDiscoveryClient,
    LMStudioDiscoveryClient,
    OllamaDiscoveryClient,
    OpenAIDiscoveryClient,
    OpenCodeDiscoveryClient,
    _humanize_model_id,
    get_discovery_client,
)


class TestHumanizeModelId:
    def test_acronyms_uppercased(self) -> None:
        # gpt and glm are acronyms — both fully uppercased, version tokens left as-is.
        assert _humanize_model_id("gpt-4o-mini") == "GPT 4o Mini"
        assert _humanize_model_id("glm-5.2") == "GLM 5.2"

    def test_brand_names_cased(self) -> None:
        # Brand names keep canonical casing; letter-led version tokens (v4, m3,
        # hy3) get a leading capital, while number-led ones (4o) stay as-is.
        assert _humanize_model_id("deepseek-v4-flash") == "DeepSeek V4 Flash"
        assert _humanize_model_id("minimax-m3") == "MiniMax M3"
        assert _humanize_model_id("mimo-v2.5-pro") == "MiMo V2.5 Pro"
        assert _humanize_model_id("hy3-preview") == "Hy3 Preview"
        assert _humanize_model_id("gpt-4o-mini") == "GPT 4o Mini"

    def test_brand_fused_to_version_split(self) -> None:
        # Qwen fuses brand + version in its ids (qwen3.7); split and case it.
        assert _humanize_model_id("qwen3.7-max") == "Qwen 3.7 Max"
        assert _humanize_model_id("qwen3.6-plus") == "Qwen 3.6 Plus"

    def test_prefix_split_requires_digit(self) -> None:
        # A word that merely starts with a known prefix must not be split.
        assert _humanize_model_id("airoboros-70b") == "Airoboros 70b"

    def test_vendor_prefix_dropped(self) -> None:
        assert _humanize_model_id("z-ai/glm-5") == "GLM 5"


def _mock_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestGetDiscoveryClient:
    def test_ollama_and_lmstudio_supported(self) -> None:
        assert isinstance(get_discovery_client(ProviderType.OLLAMA), OllamaDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.LMSTUDIO), LMStudioDiscoveryClient)

    def test_cloud_providers_supported(self) -> None:
        assert isinstance(get_discovery_client(ProviderType.OPENAI), OpenAIDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.ANTHROPIC), AnthropicDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.GOOGLE), GoogleDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.OPENROUTER), OpenAIDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.XAI), OpenAIDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.CUSTOM), OpenAIDiscoveryClient)

    def test_opencode_providers_supported(self) -> None:
        # Discovery has no fallback (unlike the adapter registry), so both plans
        # must be registered explicitly or model sync would return None.
        assert isinstance(get_discovery_client(ProviderType.OPENCODE), OpenCodeDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.OPENCODE_GO), OpenCodeDiscoveryClient)


class TestOpenCodeDiscoveryClient:
    def test_display_name_derived_from_id_not_provider_name(self) -> None:
        # OpenCode's /models returns poorly-cased names; the humanized id wins.
        resp = _mock_response(
            {
                "data": [
                    {"id": "minimax-m3", "name": "Minimax m3"},
                    {"id": "glm-5.2", "name": "Glm 5.2"},
                    {"id": "deepseek-v4-pro", "name": "Deepseek v4 Pro"},
                    {"id": "qwen3.7-max", "name": "qwen3.7 max"},
                ]
            }
        )
        with patch("httpx.Client.get", return_value=resp):
            models = OpenCodeDiscoveryClient().list_models("https://opencode.ai/zen/go/v1", "sk-x")
        names = {m.identifier: m.display_name for m in models}
        assert names == {
            "minimax-m3": "MiniMax M3",
            "glm-5.2": "GLM 5.2",
            "deepseek-v4-pro": "DeepSeek V4 Pro",
            "qwen3.7-max": "Qwen 3.7 Max",
        }


class TestOllamaDiscoveryClient:
    def setup_method(self):
        self.client = OllamaDiscoveryClient()

    def test_list_models_marks_loaded_state(self) -> None:
        tags = _mock_response(
            {
                "models": [
                    {
                        "name": "llama3:8b",
                        "model": "llama3:8b",
                        "size": 4700000000,
                        "details": {"quantization_level": "Q4_K_M"},
                    },
                    {
                        "name": "mistral:7b",
                        "model": "mistral:7b",
                        "size": 4100000000,
                        "details": {"quantization_level": "Q4_0"},
                    },
                ]
            }
        )
        ps = _mock_response({"models": [{"model": "llama3:8b"}]})

        with patch("httpx.Client.get", side_effect=[tags, ps]):
            models = self.client.list_models("http://localhost:11434")

        assert len(models) == 2
        loaded = next(m for m in models if m.identifier == "llama3:8b")
        not_loaded = next(m for m in models if m.identifier == "mistral:7b")
        assert loaded.state == "loaded"
        assert loaded.size_bytes == 4700000000
        assert loaded.quantization == "Q4_K_M"
        assert not_loaded.state == "not-loaded"

    def test_load_model_uses_negative_keep_alive(self) -> None:
        with patch("httpx.Client.post", return_value=_mock_response({})) as mock_post:
            self.client.load_model("http://localhost:11434", "llama3:8b")

        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {"model": "llama3:8b", "prompt": "", "keep_alive": -1}

    def test_unload_model_uses_zero_keep_alive(self) -> None:
        with patch("httpx.Client.post", return_value=_mock_response({})) as mock_post:
            self.client.unload_model("http://localhost:11434", "llama3:8b")

        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {"model": "llama3:8b", "prompt": "", "keep_alive": 0}


class TestLMStudioDiscoveryClient:
    def setup_method(self):
        self.client = LMStudioDiscoveryClient()

    def test_list_models_maps_fields(self) -> None:
        resp = _mock_response(
            {
                "models": [
                    {
                        "key": "google/gemma-4-26b-a4b",
                        "display_name": "Gemma 4 26B A4B",
                        "size_bytes": 17990911801,
                        "quantization": {"name": "Q4_K_M", "bits_per_weight": 4},
                        "max_context_length": 262144,
                        "loaded_instances": [{"id": "google/gemma-4-26b-a4b"}],
                    },
                    {
                        "key": "other/model",
                        "display_name": "Other Model",
                        "size_bytes": 1000,
                        "quantization": None,
                        "max_context_length": 4096,
                        "loaded_instances": [],
                    },
                ]
            }
        )

        with patch("httpx.Client.get", return_value=resp):
            models = self.client.list_models("http://localhost:1234")

        loaded = next(m for m in models if m.identifier == "google/gemma-4-26b-a4b")
        not_loaded = next(m for m in models if m.identifier == "other/model")
        assert loaded.state == "loaded"
        assert loaded.quantization == "Q4_K_M"
        assert loaded.max_context_length == 262144
        assert not_loaded.state == "not-loaded"
        assert not_loaded.quantization is None

    def test_list_models_strips_v1_suffix_from_base_url(self) -> None:
        resp = _mock_response({"models": []})
        with patch("httpx.Client.get", return_value=resp) as mock_get:
            self.client.list_models("http://localhost:1234/v1")

        args, _ = mock_get.call_args
        assert args[0] == "http://localhost:1234/api/v1/models"

    def test_load_model(self) -> None:
        with patch("httpx.Client.post", return_value=_mock_response({})) as mock_post:
            self.client.load_model("http://localhost:1234", "google/gemma-4-26b-a4b")

        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:1234/api/v1/models/load"
        assert kwargs["json"] == {"model": "google/gemma-4-26b-a4b"}

    def test_unload_model_uses_instance_id(self) -> None:
        with patch("httpx.Client.post", return_value=_mock_response({})) as mock_post:
            self.client.unload_model("http://localhost:1234", "google/gemma-4-26b-a4b")

        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:1234/api/v1/models/unload"
        assert kwargs["json"] == {"instance_id": "google/gemma-4-26b-a4b"}


class TestGoogleDiscoveryClient:
    def setup_method(self):
        self.client = GoogleDiscoveryClient()

    def test_list_models_strips_models_prefix_from_identifier(self) -> None:
        """The v1beta list returns `models/<id>`; the callable id is the bare tail.

        The registry stores routes by the bare id, so discovery must strip the
        prefix or nothing lines up (the "already added" detection breaks).
        """
        resp = _mock_response(
            {
                "models": [
                    {
                        "name": "models/gemini-2.5-pro",
                        "displayName": "Gemini 2.5 Pro",
                        "inputTokenLimit": 1048576,
                    },
                    {"name": "models/gemini-3.5-flash"},  # no displayName -> falls back to id
                ]
            }
        )

        with patch("httpx.Client.get", return_value=resp):
            models = self.client.list_models("https://generativelanguage.googleapis.com")

        by_id = {m.identifier: m for m in models}
        assert set(by_id) == {"gemini-2.5-pro", "gemini-3.5-flash"}
        assert by_id["gemini-2.5-pro"].display_name == "Gemini 2.5 Pro"
        assert by_id["gemini-2.5-pro"].max_context_length == 1048576
        # Fallback display name is the bare identifier, not the prefixed name.
        assert by_id["gemini-3.5-flash"].display_name == "gemini-3.5-flash"


class TestAnthropicDiscoveryClient:
    def setup_method(self):
        self.client = AnthropicDiscoveryClient()

    def test_list_models_strips_dated_snapshot_to_bare_alias(self) -> None:
        """/models lists the dated snapshot; the undated alias is equally callable.

        We seed the bare alias, so discovery strips the trailing -YYYYMMDD to
        match (and dedupes if two snapshots collapse to the same alias). Undated
        ids (claude-opus-4-6) pass through untouched.
        """
        resp = _mock_response(
            {
                "data": [
                    {"id": "claude-haiku-4-5-20251001", "display_name": "Claude 4.5 Haiku"},
                    {"id": "claude-opus-4-5-20251101", "display_name": "Claude 4.5 Opus"},
                    {"id": "claude-opus-4-5-20250601"},  # older snapshot -> same alias, deduped
                    {"id": "claude-opus-4-6", "display_name": "Claude 4.6 Opus"},
                ]
            }
        )

        with patch("httpx.Client.get", return_value=resp):
            models = self.client.list_models("https://api.anthropic.com/v1")

        ids = [m.identifier for m in models]
        assert ids == ["claude-haiku-4-5", "claude-opus-4-5", "claude-opus-4-6"]
        by_id = {m.identifier: m for m in models}
        assert by_id["claude-haiku-4-5"].display_name == "Claude 4.5 Haiku"
