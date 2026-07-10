"""Model and ModelFamily ORM models."""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, Any, final

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.models._base import BaseModel, StringList

if TYPE_CHECKING:
    from src.core.persistence.models.chat import Chat
    from src.core.persistence.models.prompt import PromptTemplate
    from src.core.persistence.models.provider import Provider


@final
class Model(BaseModel):
    """Model definition with fully flexible parameters"""

    __tablename__ = "models"

    provider_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("providers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Unique identifier of the AI provider for this model",
    )
    model_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Provider-specific model name (e.g., 'gpt-4o-mini', 'claude-4.5-sonnet')",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Display name of the model"
    )
    model_family_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("model_families.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Unique identifier of the model family this model belongs to",
    )
    template_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Default prompt template for this model configuration",
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Model-specific overrides for sampling and generation parameters",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this model is currently available for use",
    )

    provider: Mapped[Provider] = relationship(back_populates="models")
    model_family: Mapped[ModelFamily] = relationship(back_populates="models")
    template: Mapped[PromptTemplate | None] = relationship(back_populates="models")
    # Chat has two FKs to models (model_id + task_model_id); scope this reverse
    # collection to the primary model_id.
    chats: Mapped[list[Chat]] = relationship(back_populates="model", foreign_keys="Chat.model_id")

    @property
    def provider_enabled(self) -> bool:
        return self.provider.enabled


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

    models: Mapped[list[Model]] = relationship(back_populates="model_family")
