"""Wiring tests for the OpenCode Zen / Go first-class providers.

Both plans are OpenAI-compatible and reuse the OpenAI adapter + discovery
client; they differ only in default base URL and the fixed API-key env var.
"""

import pytest
from src.provider.adapters import get_adapter
from src.provider.adapters.openai import OpenAIAdapter
from src.provider.models import PROVIDER_CONFIGS, Provider, ProviderType


class TestOpenCodeProviderConfig:
    def test_zen_config(self) -> None:
        config = PROVIDER_CONFIGS[ProviderType.OPENCODE]
        assert config.display_name == "OpenCode Zen"
        assert config.env_var_name == "OPENCODE_ZEN_API_KEY"
        assert config.default_base_url == "https://opencode.ai/zen/v1"
        assert config.requires_api_key is True

    def test_go_config(self) -> None:
        config = PROVIDER_CONFIGS[ProviderType.OPENCODE_GO]
        assert config.display_name == "OpenCode Go"
        assert config.env_var_name == "OPENCODE_GO_API_KEY"
        assert config.default_base_url == "https://opencode.ai/zen/go/v1"
        assert config.requires_api_key is True


class TestOpenCodeAdapter:
    def test_both_plans_use_openai_adapter(self) -> None:
        assert isinstance(get_adapter(ProviderType.OPENCODE), OpenAIAdapter)
        assert isinstance(get_adapter(ProviderType.OPENCODE_GO), OpenAIAdapter)

    def test_zen_builds_openai_compatible_url(self) -> None:
        provider = Provider(name="OpenCode Zen", provider_type=ProviderType.OPENCODE)
        adapter = get_adapter(provider.provider_type)
        url = adapter.build_url(provider.get_base_url(), "deepseek-v4-flash", False)
        assert url == "https://opencode.ai/zen/v1/chat/completions"

    def test_go_builds_openai_compatible_url(self) -> None:
        provider = Provider(name="OpenCode Go", provider_type=ProviderType.OPENCODE_GO)
        adapter = get_adapter(provider.provider_type)
        url = adapter.build_url(provider.get_base_url(), "glm-5.2", False)
        assert url == "https://opencode.ai/zen/go/v1/chat/completions"


class TestOpenCodeApiKey:
    def test_zen_reads_fixed_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENCODE_ZEN_API_KEY", "sk-zen")
        provider = Provider(name="OpenCode Zen", provider_type=ProviderType.OPENCODE)
        assert provider.get_env_var_name() == "OPENCODE_ZEN_API_KEY"
        assert provider.get_api_key() == "sk-zen"
        assert provider.has_api_key() is True
        headers = get_adapter(provider.provider_type).build_headers(provider.get_api_key())
        assert headers["Authorization"] == "Bearer sk-zen"

    def test_go_reads_fixed_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENCODE_GO_API_KEY", "sk-go")
        provider = Provider(name="OpenCode Go", provider_type=ProviderType.OPENCODE_GO)
        assert provider.get_env_var_name() == "OPENCODE_GO_API_KEY"
        assert provider.get_api_key() == "sk-go"
        assert provider.has_api_key() is True
