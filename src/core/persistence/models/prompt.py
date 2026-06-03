"""PromptTemplate, PromptFragment, and TemplateFragment ORM models."""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, final

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.models._base import BaseModel

if TYPE_CHECKING:
    from src.core.persistence.models.chat import Chat
    from src.core.persistence.models.model import Model

# Component order for prompt construction
DEFAULT_COMPONENT_ORDER = [
    "system_prompt",
    "world_lore_before_character",
    "character_context",
    "world_lore_after_character",
    "scenario",
    "persona",
    "world_lore_before_examples",
    "example_dialogues",
    "rag_context",
    "chat_history",
    "post_history_instructions",
]

# Component toggles
DEFAULT_COMPONENTS_ENABLED = {
    "system_prompt": True,
    "world_lore_before_character": True,
    "character_context": False,
    "world_lore_after_character": True,
    "scenario": False,
    "persona": True,
    "world_lore_before_examples": True,
    "example_dialogues": True,
    "rag_context": True,
    "chat_history": True,
    "post_history_instructions": True,
}


@final
class PromptTemplate(BaseModel):
    """Configurable prompt template with component ordering"""

    __tablename__ = "prompt_templates"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique name of the prompt template",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Brief description of the template's purpose"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this template is automatically selected for new chats",
    )
    system_template: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Jinja2 template string for the system prompt"
    )
    component_order: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=DEFAULT_COMPONENT_ORDER,
        comment="Ordered list of component names for prompt construction",
    )
    components_enabled: Mapped[dict[str, bool]] = mapped_column(
        JSON,
        nullable=False,
        default=DEFAULT_COMPONENTS_ENABLED,
        comment="Map of component names to their enabled status",
    )
    max_history_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Maximum number of tokens to include from chat history"
    )

    chats: Mapped[list[Chat]] = relationship(back_populates="template")
    models: Mapped[list[Model]] = relationship(back_populates="template")
    template_fragments: Mapped[list[TemplateFragment]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateFragment.position, TemplateFragment.ordinal",
    )


@final
class PromptFragment(BaseModel):
    """Reusable prompt instruction block (NSFW rules, jailbreaks, writing style, etc.)"""

    __tablename__ = "prompt_fragments"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="Display name"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Brief description of the fragment's purpose"
    )
    fragment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="instruction",
        comment="Category: system, nsfw, jailbreak, instruction, context",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Jinja2 template text for this fragment"
    )
    is_global: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Available to all templates if True"
    )

    template_fragments: Mapped[list[TemplateFragment]] = relationship(
        back_populates="fragment", cascade="all, delete-orphan"
    )


@final
class TemplateFragment(BaseModel):
    """Join table linking prompt fragments to templates with position and ordering"""

    __tablename__ = "template_fragments"

    template_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fragment_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("prompt_fragments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="after_system",
        comment="Injection position: after_system, pre_history, post_history",
    )
    ordinal: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Order within position (0-based)"
    )

    template: Mapped[PromptTemplate] = relationship(back_populates="template_fragments")
    fragment: Mapped[PromptFragment] = relationship(back_populates="template_fragments")
