"""ModelRegistry, ModelRoute, and ModelFamily ORM models.

Three tiers describe a model:

- ``ModelFamily`` — a capability group + the parameter *schema* + which provider
  types can run it.
- ``ModelRegistry`` — the canonical model (SKU) users pick: a provider-independent
  identity, concrete parameter *values*, a default template, and a pointer to the
  active route.
- ``ModelRoute`` — one provider binding (provider + the identifier that provider
  uses). The same canonical model reachable through several providers is several
  routes sharing one registry entry; the *provider is the route*.
"""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, Any, final

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.enums import ReasoningMode
from src.core.persistence.models._base import BaseModel, StringList

if TYPE_CHECKING:
    from src.core.persistence.models.chat import Chat
    from src.core.persistence.models.prompt import PromptTemplate
    from src.core.persistence.models.provider import Provider


@final
class ModelRegistry(BaseModel):
    """Canonical model (SKU): identity + parameter values + family + active route."""

    __tablename__ = "model_registry"

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Provider-independent identity of the canonical model (e.g. 'deepseek-v4-pro')",
    )
    display_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Display name of the canonical model"
    )
    original_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Native/canonical identifier as the originating lab names it",
    )
    model_family_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("model_families.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Model family this canonical model belongs to",
    )
    template_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Default prompt template for this model",
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Per-model overrides for sampling and generation parameters",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this model is currently available for use",
    )
    # Which route the model is currently reached through. Circular FK with
    # model_routing (routes point back at the registry); use_alter defers the
    # constraint so the two tables can be created in any order.
    active_route_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey(
            "model_routing.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_model_registry_active_route",
        ),
        nullable=True,
        comment="The active route: which provider binding this model resolves to",
    )

    model_family: Mapped[ModelFamily] = relationship(back_populates="models")
    template: Mapped[PromptTemplate | None] = relationship(back_populates="models")
    routes: Mapped[list[ModelRoute]] = relationship(
        back_populates="model_registry",
        cascade="all, delete-orphan",
        foreign_keys="ModelRoute.model_registry_id",
    )
    # post_update breaks the registry<->route write cycle on insert/delete.
    active_route: Mapped[ModelRoute | None] = relationship(
        foreign_keys=[active_route_id], post_update=True
    )
    # Chat has two FKs to model_registry (model_id + task_model_id); scope this
    # reverse collection to the primary model_id.
    chats: Mapped[list[Chat]] = relationship(back_populates="model", foreign_keys="Chat.model_id")

    @property
    def provider_enabled(self) -> bool:
        """Reachable only if the active route exists and it + its provider are enabled."""
        route = self.active_route
        return bool(route and route.enabled and route.provider.enabled)


@final
class ModelRoute(BaseModel):
    """One provider binding for a canonical model: a provider + the identifier it uses."""

    __tablename__ = "model_routing"
    __table_args__ = (
        UniqueConstraint("provider_id", "model_identifier", name="uq_route_provider_identifier"),
        UniqueConstraint("model_registry_id", "provider_id", name="uq_route_registry_provider"),
    )

    model_registry_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("model_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Canonical model this route belongs to",
    )
    provider_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Provider this route reaches the model through",
    )
    model_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Provider-specific model identifier (e.g. 'deepseek/deepseek-v4-pro')",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether this route is usable"
    )

    model_registry: Mapped[ModelRegistry] = relationship(
        back_populates="routes", foreign_keys=[model_registry_id]
    )
    provider: Mapped[Provider] = relationship(back_populates="model_routes")


@final
class ModelFamily(BaseModel):
    """Defines capabilities and default parameters for a family of models"""

    __tablename__ = "model_families"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="Display name of the model family"
    )
    family_identifier: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe identifier following provider/model-name pattern",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detailed description of the model family capabilities"
    )
    provider_types: Mapped[list[str]] = mapped_column(
        StringList,
        default=list,
        nullable=False,
        comment="List of provider types that support this family",
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Schema and default values for supported parameters",
    )
    unsupported_parameters: Mapped[list[str]] = mapped_column(
        StringList,
        default=list,
        nullable=False,
        comment="List of parameters explicitly known to be unsupported by this family",
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Additional family-specific technical metadata"
    )

    models: Mapped[list[ModelRegistry]] = relationship(back_populates="model_family")

    @property
    def reasoning_mode(self) -> ReasoningMode:
        """Declared reasoning capability, read from ``extra_metadata['reasoning_mode']``.

        The authoritative signal for whether reasoning applies and can be disabled;
        defaults to ``NONE`` (and tolerates an unknown value) so callers never need
        to sniff the parameter schema.
        """
        raw = (self.extra_metadata or {}).get("reasoning_mode")
        try:
            return ReasoningMode(raw) if raw else ReasoningMode.NONE
        except ValueError:
            return ReasoningMode.NONE

    @property
    def context_window(self) -> int | None:
        """Total context length in tokens, read from ``extra_metadata['context_window']``.

        The ceiling history truncation budgets against; ``None`` (missing or a
        non-positive/non-int value) means "unknown", so callers fall back to the
        template's flat ``max_history_tokens`` instead of a real window.
        """
        raw = (self.extra_metadata or {}).get("context_window")
        return raw if isinstance(raw, int) and raw > 0 else None
