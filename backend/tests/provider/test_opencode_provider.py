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
        # OpenCode takes the bare name, unlike the vendor-prefixed OpenRouter slug.
        assert config.identifier_style == "bare name"

    def test_go_config(self) -> None:
        config = PROVIDER_CONFIGS[ProviderType.OPENCODE_GO]
        assert config.display_name == "OpenCode Go"
        assert config.env_var_name == "OPENCODE_GO_API_KEY"
        assert config.default_base_url == "https://opencode.ai/zen/go/v1"
        assert config.requires_api_key is True
        assert config.identifier_style == "bare name"


class TestIdentifierNamingMetadata:
    def test_every_provider_type_has_naming_metadata(self) -> None:
        for provider_type in ProviderType:
            config = PROVIDER_CONFIGS[provider_type]
            assert config.identifier_style, provider_type
            assert config.identifier_hint, provider_type

    def test_openrouter_is_vendor_prefixed(self) -> None:
        config = PROVIDER_CONFIGS[ProviderType.OPENROUTER]
        assert config.identifier_style == "vendor/model"
        assert "author/model" in config.identifier_hint

    def test_native_providers_are_bare(self) -> None:
        for provider_type in (ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.XAI):
            assert PROVIDER_CONFIGS[provider_type].identifier_style == "bare name"

    def test_provider_orm_derives_naming_metadata(self) -> None:
        provider = Provider(name="Router", provider_type=ProviderType.OPENROUTER)
        assert provider.identifier_style == "vendor/model"
        assert provider.identifier_hint == PROVIDER_CONFIGS[ProviderType.OPENROUTER].identifier_hint


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
