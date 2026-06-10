"""Alembic environment configuration"""

import sys
from logging.config import fileConfig
from pathlib import Path

import alembic_postgresql_enum  # noqa: F401  # import registers native-PG-enum autogenerate handlers
from sqlalchemy import engine_from_config, pool

from alembic import context  # type: ignore
from alembic.autogenerate.api import AutogenContext
from alembic.operations import ops as alembic_ops
from alembic.runtime.migration import MigrationContext

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.audit.models import *  # noqa
from src.chat_message.models import *  # noqa
from src.chat_session.models import *  # noqa
from src.core.persistence.base_model import Base
from src.core.config import settings
from src.model.models import *  # noqa
from src.model_family.models import *  # noqa
from src.prompt_template.models import *  # noqa
from src.provider.models import *  # noqa
from src.character.models import *  # noqa
from src.persona.models import *  # noqa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with value from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def _include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    """Exclude manually-managed DDL from autogenerate/`alembic check`.

    The vchordrq index uses VectorChord's access method, which SQLAlchemy doesn't
    model — it's created via raw SQL in the migration, so autogenerate must not
    try to drop it.
    """
    return not (type_ == "index" and name == "ix_embeddings_vchordrq")


# VectorChord approximate-NN index backing the cosine `<=>` similarity search.
# `lists` is omitted (flat RaBitQ scan) — the right default for modest local datasets.
_VCHORDRQ_SQL = (
    "CREATE INDEX ix_embeddings_vchordrq ON embeddings "
    "USING vchordrq (embedding vector_cosine_ops) "
    "WITH (options = $$\nresidual_quantization = true\n$$)"
)


def _render_item(type_: str, obj: object, autogen_context: AutogenContext) -> bool:
    """Emit pgvector's import when a VECTOR column type is rendered.

    Autogenerate renders the type fully-qualified but never injects the import,
    so the generated migration would NameError without this.
    """
    if type_ == "type" and type(obj).__module__.startswith("pgvector"):
        autogen_context.imports.add("import pgvector.sqlalchemy.vector")
    return False  # fall back to Alembic's default rendering


def _process_revision_directives(
    context: MigrationContext,
    revision: object,
    directives: list[alembic_ops.MigrationScript],
) -> None:
    """Inject the VectorChord DDL that Alembic's schema diff cannot model.

    Fires only when a migration (re)creates the embeddings table — i.e. the
    consolidated full-schema build — so delta migrations are left untouched.
    Complements `_include_object`, which keeps the raw index out of comparison.
    """
    if not directives:
        return
    upgrade_ops = directives[0].upgrade_ops
    if upgrade_ops is None:
        return
    builds_embeddings = any(
        isinstance(op, alembic_ops.CreateTableOp) and op.table_name == "embeddings"
        for op in upgrade_ops.ops
    )
    if not builds_embeddings:
        return
    # pgvector (pulled in via CASCADE) must exist before the embeddings.embedding column.
    upgrade_ops.ops.insert(
        0, alembic_ops.ExecuteSQLOp("CREATE EXTENSION IF NOT EXISTS vchord CASCADE")
    )
    upgrade_ops.ops.append(alembic_ops.ExecuteSQLOp(_VCHORDRQ_SQL))


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
        render_item=_render_item,
        process_revision_directives=_process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=_include_object,
            render_item=_render_item,
            process_revision_directives=_process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
