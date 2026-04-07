"""initial_schema

Revision ID: 3e8d44254c65
Revises:
Create Date: 2026-04-07 16:35:36.507697

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3e8d44254c65"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Migration targets PostgreSQL — use ARRAY directly
StringList = postgresql.ARRAY(sa.String)


def _try_create_vector_extension() -> bool:
    """Try to enable pgvector. Returns True if available, False if not."""
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        return True
    except Exception:
        import warnings

        warnings.warn(
            "pgvector extension not available (need superuser or pre-installed). "
            "RAG features will not work. Run as superuser: "
            "CREATE EXTENSION IF NOT EXISTS vector;",
            stacklevel=2,
        )
        return False


def upgrade() -> None:
    # === Extensions (optional — RAG requires pgvector) ===
    has_vector = _try_create_vector_extension()

    # === Independent tables ===

    op.create_table(
        "providers",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("base_url", sa.String(255), nullable=True),
        sa.Column("api_key_env_var", sa.String(100), nullable=True),
        sa.Column(
            "provider_type",
            sa.Enum(
                "xai",
                "google",
                "openai",
                "anthropic",
                "openrouter",
                "ollama",
                "custom",
                name="providertype",
            ),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "model_families",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("family_identifier", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider_types", StringList, nullable=False, server_default="{}"),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("unsupported_parameters", StringList, nullable=False, server_default="{}"),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_families_family_identifier", "model_families", ["family_identifier"])

    op.create_table(
        "personas",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("avatar", sa.String(255), nullable=True),
        sa.Column("avatar_thumbnail", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personas_name", "personas", ["name"])

    op.create_table(
        "presets",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_presets_name", "presets", ["name"])

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("component_order", sa.JSON(), nullable=False),
        sa.Column("components_enabled", sa.JSON(), nullable=False),
        sa.Column("max_history_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_templates_name", "prompt_templates", ["name"])

    op.create_table(
        "prompt_fragments",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("fragment_type", sa.String(50), nullable=False, server_default="instruction"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_fragments_name", "prompt_fragments", ["name"])

    op.create_table(
        "characters",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("first_message", sa.Text(), nullable=True),
        sa.Column("example_dialogues", StringList, nullable=True),
        sa.Column("avatar", sa.String(255), nullable=True),
        sa.Column("avatar_thumbnail", sa.String(255), nullable=True),
        sa.Column("scenario", sa.Text(), nullable=True),
        sa.Column("post_history_instructions", sa.Text(), nullable=True),
        sa.Column("alternate_greetings", StringList, nullable=True),
        sa.Column("tags", StringList, nullable=True),
        sa.Column(
            "gender",
            sa.Enum("male", "female", "non_binary", "others", name="gender"),
            nullable=True,
        ),
        sa.Column("custom_gender", sa.String(100), nullable=True),
        sa.Column("creator", sa.String(100), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("creator_notes", sa.Text(), nullable=True),
        sa.Column("character_version", sa.String(100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # === Tables with FKs ===

    op.create_table(
        "models",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("provider_id", sa.String(12), nullable=False),
        sa.Column("model_identifier", sa.String(100), nullable=False),
        sa.Column("openrouter_identifier", sa.String(100), nullable=True),
        sa.Column("use_openrouter", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("model_family_id", sa.String(12), nullable=False),
        sa.Column("template_id", sa.String(12), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_family_id"], ["model_families.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["prompt_templates.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_models_provider_id", "models", ["provider_id"])
    op.create_index("ix_models_model_identifier", "models", ["model_identifier"])
    op.create_index("ix_models_model_family_id", "models", ["model_family_id"])
    op.create_index("ix_models_template_id", "models", ["template_id"])

    op.create_table(
        "chats",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("character_id", sa.String(12), nullable=False),
        sa.Column("model_id", sa.String(12), nullable=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("preview", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("template_id", sa.String(12), nullable=True),
        sa.Column("persona_id", sa.String(12), nullable=True),
        sa.Column("preset_id", sa.String(12), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["prompt_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["preset_id"], ["presets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_chats_character_id", "chats", ["character_id"])
    op.create_index("ix_chats_model_id", "chats", ["model_id"])
    op.create_index("ix_chats_template_id", "chats", ["template_id"])
    op.create_index("ix_chats_persona_id", "chats", ["persona_id"])
    op.create_index("ix_chats_preset_id", "chats", ["preset_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("chat_id", sa.String(12), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="messagerole"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("reasoning_content", sa.Text(), nullable=True),
        sa.Column("active_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_chat_id", "messages", ["chat_id"])

    op.create_table(
        "message_alternatives",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("message_id", sa.String(12), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_message_alternatives_message_id", "message_alternatives", ["message_id"])

    op.create_table(
        "lorebooks",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("character_id", sa.String(12), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "lore_entries",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("lorebook_id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("keys", StringList, nullable=False, server_default="{}"),
        sa.Column("secondary_keys", StringList, nullable=False, server_default="{}"),
        sa.Column(
            "secondary_logic",
            sa.Enum("and_any", "and_all", "not_any", "not_all", name="secondarylogic"),
            nullable=False,
            server_default="and_any",
        ),
        sa.Column("case_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("match_whole_words", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("use_regex", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("constant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "position",
            sa.Enum(
                "before_character",
                "after_character",
                "at_depth",
                "before_examples",
                name="insertionposition",
            ),
            nullable=False,
            server_default="after_character",
        ),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="4"),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="messagerole", create_type=False),
            nullable=False,
            server_default="system",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("scan_depth", sa.Integer(), nullable=True),
        sa.Column("ignore_budget", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["lorebook_id"], ["lorebooks.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "template_fragments",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("template_id", sa.String(12), nullable=False),
        sa.Column("fragment_id", sa.String(12), nullable=False),
        sa.Column("position", sa.String(50), nullable=False, server_default="after_system"),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["template_id"], ["prompt_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fragment_id"], ["prompt_fragments.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_template_fragments_template_id", "template_fragments", ["template_id"])
    op.create_index("ix_template_fragments_fragment_id", "template_fragments", ["fragment_id"])

    op.create_table(
        "data_bank_entries",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False, server_default="global"),
        sa.Column("character_id", sa.String(12), nullable=True),
        sa.Column("chat_id", sa.String(12), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_data_bank_entries_scope", "data_bank_entries", ["scope"])
    op.create_index("ix_data_bank_entries_character_id", "data_bank_entries", ["character_id"])
    op.create_index("ix_data_bank_entries_chat_id", "data_bank_entries", ["chat_id"])

    op.create_table(
        "embeddings",
        sa.Column("id", sa.String(12), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(12), nullable=False),
        sa.Column("content_hash", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_embeddings_source_type", "embeddings", ["source_type"])
    op.create_index("ix_embeddings_source_id", "embeddings", ["source_id"])
    op.create_index("ix_embeddings_content_hash", "embeddings", ["content_hash"])

    if has_vector:
        # Create vector column without fixed dimensions — allows any embedding model.
        # HNSW index requires dimensions, so we skip auto-index creation.
        # The application creates the index on first use when dimensions are known,
        # or users can create it manually:
        #   CREATE INDEX ix_embeddings_vector ON embeddings
        #   USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
        op.execute("ALTER TABLE embeddings ADD COLUMN embedding vector")


def downgrade() -> None:
    op.drop_table("embeddings")
    op.drop_table("data_bank_entries")
    op.drop_table("template_fragments")
    op.drop_table("lore_entries")
    op.drop_table("lorebooks")
    op.drop_table("message_alternatives")
    op.drop_table("messages")
    op.drop_table("chats")
    op.drop_table("models")
    op.drop_table("characters")
    op.drop_table("prompt_fragments")
    op.drop_table("prompt_templates")
    op.drop_table("presets")
    op.drop_table("personas")
    op.drop_table("model_families")
    op.drop_table("providers")
    sa.Enum(name="providertype").drop(op.get_bind())
    sa.Enum(name="gender").drop(op.get_bind())
    sa.Enum(name="messagerole").drop(op.get_bind())
    sa.Enum(name="secondarylogic").drop(op.get_bind())
    sa.Enum(name="insertionposition").drop(op.get_bind())
