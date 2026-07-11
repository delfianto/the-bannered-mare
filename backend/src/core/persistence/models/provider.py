"""Provider ORM model and ProviderConfig."""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, final

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.enums import ProviderType
from src.core.persistence.models._base import BaseModel, StringList

if TYPE_CHECKING:
    from src.core.persistence.models.model import ModelRoute


@dataclass
class ProviderConfig:
    """Static configuration for each provider type"""

    display_name: str
    env_var_name: str | None
    default_base_url: str
    requires_api_key: bool
    # Model identifiers are provider-specific: aggregators (OpenRouter) prepend a
    # vendor slug (``author/model``), native and OpenCode endpoints take the bare
    # name, Ollama uses ``name:tag``. Surfaced in the UI so users know what to type.
    identifier_style: str
    identifier_hint: str


PROVIDER_CONFIGS: dict[ProviderType, ProviderConfig] = {
    ProviderType.OPENAI: ProviderConfig(
        display_name="OpenAI",
        env_var_name="OPENAI_API_KEY",
        default_base_url="https://api.openai.com/v1",
        requires_api_key=True,
        identifier_style="bare name",
        identifier_hint="Bare model name, no vendor prefix — e.g. gpt-5.6 or gpt-4o-mini.",
    ),
    ProviderType.ANTHROPIC: ProviderConfig(
        display_name="Anthropic",
        env_var_name="ANTHROPIC_API_KEY",
        default_base_url="https://api.anthropic.com/v1",
        requires_api_key=True,
        identifier_style="bare name",
        identifier_hint="Bare model name, no vendor prefix — e.g. claude-opus-4-8.",
    ),
    ProviderType.GOOGLE: ProviderConfig(
        display_name="Google AI",
        env_var_name="GOOGLE_API_KEY",
        default_base_url="https://generativelanguage.googleapis.com",
        requires_api_key=True,
        identifier_style="bare name",
        identifier_hint="Bare model name, no vendor prefix — e.g. gemini-3.5-flash.",
    ),
    ProviderType.OPENROUTER: ProviderConfig(
        display_name="OpenRouter",
        env_var_name="OPENROUTER_API_KEY",
        default_base_url="https://openrouter.ai/api/v1",
        requires_api_key=True,
        identifier_style="vendor/model",
        identifier_hint=(
            "Vendor-prefixed slug author/model — e.g. openai/gpt-5.6 or "
            "deepseek/deepseek-v4-flash. Optional :free / :nitro / :floor variant "
            "suffix; a leading ~ pins the latest in a family."
        ),
    ),
    ProviderType.XAI: ProviderConfig(
        display_name="xAI",
        env_var_name="XAI_API_KEY",
        default_base_url="https://api.x.ai/v1",
        requires_api_key=True,
        identifier_style="bare name",
        identifier_hint="Bare model name, no vendor prefix — e.g. grok-4.5.",
    ),
    ProviderType.OLLAMA: ProviderConfig(
        display_name="Ollama",
        env_var_name=None,
        default_base_url="http://localhost:11434",
        requires_api_key=False,
        identifier_style="name:tag",
        identifier_hint="Model name with an optional :tag — e.g. llama3.1:8b or qwen2.5:14b-instruct.",
    ),
    ProviderType.LMSTUDIO: ProviderConfig(
        display_name="LM Studio",
        env_var_name=None,
        default_base_url="http://localhost:1234",
        requires_api_key=False,
        identifier_style="bare key",
        identifier_hint="The loaded model's key — e.g. qwen2.5-7b-instruct.",
    ),
    ProviderType.OPENCODE: ProviderConfig(
        display_name="OpenCode Zen",
        env_var_name="OPENCODE_ZEN_API_KEY",
        default_base_url="https://opencode.ai/zen/v1",
        requires_api_key=True,
        identifier_style="bare name",
        identifier_hint=(
            "Bare model name, no vendor prefix — e.g. deepseek-v4-flash or glm-5.2. "
            "(The opencode/ prefix is only for OpenCode's own config, not the API.)"
        ),
    ),
    ProviderType.OPENCODE_GO: ProviderConfig(
        display_name="OpenCode Go",
        env_var_name="OPENCODE_GO_API_KEY",
        default_base_url="https://opencode.ai/zen/go/v1",
        requires_api_key=True,
        identifier_style="bare name",
        identifier_hint="Bare model name, no vendor prefix — e.g. deepseek-v4-flash.",
    ),
    ProviderType.CUSTOM: ProviderConfig(
        display_name="Custom",
        env_var_name=None,
        default_base_url="",
        requires_api_key=True,
        identifier_style="provider-defined",
        identifier_hint="Whatever identifier the upstream OpenAI-compatible API expects.",
    ),
}


@final
class Provider(BaseModel):
    """Provider model defining AI API service connection settings"""

    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="Unique name of the AI provider"
    )
    base_url: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="API endpoint base URL for the service"
    )
    api_key_env_var: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Name of the environment variable storing the API key"
    )
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Classification of the provider (openai, anthropic, etc.)",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this provider is currently active and usable",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the provider's models were last synced",
    )
    allowed_models: Mapped[list[str]] = mapped_column(
        StringList,
        default=list,
        nullable=False,
        comment="Curated allow-list of provider-native model identifiers; empty means show all",
    )

    model_routes: Mapped[list[ModelRoute]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )

    @property
    def api_key_configured(self) -> bool:
        return self.has_api_key()

    @property
    def env_var_name(self) -> str | None:
        return self.get_env_var_name()

    @property
    def identifier_style(self) -> str:
        return PROVIDER_CONFIGS[self.provider_type].identifier_style

    @property
    def identifier_hint(self) -> str:
        return PROVIDER_CONFIGS[self.provider_type].identifier_hint

    def get_api_key(self) -> str | None:
        config = PROVIDER_CONFIGS[self.provider_type]
        env_var_name = (
            self.api_key_env_var
            if self.provider_type == ProviderType.CUSTOM
            else config.env_var_name
        )
        if not env_var_name:
            return None
        return os.getenv(env_var_name)

    def get_env_var_name(self) -> str | None:
        if self.provider_type == ProviderType.CUSTOM:
            return self.api_key_env_var
        return PROVIDER_CONFIGS[self.provider_type].env_var_name

    def has_api_key(self) -> bool:
        config = PROVIDER_CONFIGS[self.provider_type]
        if not config.requires_api_key:
            return True
        return self.get_api_key() is not None

    def get_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        return PROVIDER_CONFIGS[self.provider_type].default_base_url
