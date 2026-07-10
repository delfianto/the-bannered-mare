"""Tests for local-provider model discovery/load/unload clients."""

from unittest.mock import MagicMock, patch

from src.core.persistence.enums import ProviderType
from src.provider.discovery import (
    AnthropicDiscoveryClient,
    GoogleDiscoveryClient,
    LMStudioDiscoveryClient,
    OllamaDiscoveryClient,
    OpenAIDiscoveryClient,
    get_discovery_client,
)


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
        assert isinstance(get_discovery_client(ProviderType.OPENCODE), OpenAIDiscoveryClient)
        assert isinstance(get_discovery_client(ProviderType.OPENCODE_GO), OpenAIDiscoveryClient)


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
