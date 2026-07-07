# Persistence Layer

The persistence layer manages relational storage, schema migrations, and entity lifecycles.
It runs on **PostgreSQL** in production and **SQLite** in tests, built on **SQLAlchemy 2.0**
and **Alembic**. This page walks the layer from the bottom up: the base model every table
shares, why models live centrally, the mixed async/sync policy, the repository pattern, and
migrations.


## 1. Declarative Base and Base Model

All entities in the database inherit from `BaseModel` (defined in [base_model.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/core/persistence/base_model.py)), which is an abstract class built on SQLAlchemy's declarative mapping system.

```python
class BaseModel(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(12),
        primary_key=True,
        default=gen_id,
        comment="Unique short identifier (12 characters)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        comment="Timestamp when the record was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        comment="Timestamp when the record was last updated (UTC)",
    )
```

### Key Design Decisions
- **12-Character Nanoids**: Instead of standard auto-incrementing integers or bulky UUIDs, The Bannered Mare uses 12-character Nanoids as primary keys. They are compact, URL-safe, and secure against enumeration attacks.
- **Timezones**: All timestamps are stored with timezone support enabled (`DateTime(timezone=True)`) and default to timezone-aware UTC datetime objects.


## 2. Preventing Circular Imports (Centralized Model Definitions)

In a vertical-slices modular monolith, domains often reference each other (e.g., a `Chat` has a relationship with a `Character`, which in turn has a relationship with `Lorebook`). Placing ORM models directly inside domain folders can cause circular import issues.

To resolve this:
- All ORM database models are stored in [src/core/persistence/models/](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/core/persistence/models/) as separate modules (e.g., `character.py`, `chat.py`, `provider.py`).
- They are imported and re-exported from [src/core/persistence/models/__init__.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/core/persistence/models/__init__.py).
- Individual domain packages expose files like `models.py` which simply act as pass-through imports to the centralized persistence directory, preventing circular reference paths.


## 3. Asynchronous vs. Synchronous Operations

The Bannered Mare implements a **mixed-mode** synchronization policy to balance simplicity and performance. Two full engines are configured side by side in [database.py](https://github.com/delfianto/the-bannered-mare/blob/main/backend/src/core/persistence/database.py): a synchronous engine (with `SessionLocal` / `get_db`) and an asynchronous engine (with `AsyncSessionLocal` / `get_async_db`).

1. **Asynchronous (Async) Operations**:
   - **Where**: The hot, concurrent, streaming-adjacent paths — chat messages, chat sessions, persisted audit logging, and RAG embeddings. These slices ship a `repository_async.py` (`AsyncMessageRepository`, `AsyncChatRepository`, `AsyncEmbeddingRepository`, and the audit writer's `AuditRepository`).
   - **Implementation**: Uses `asyncpg` with async SQLAlchemy sessions, executing via `await session.execute(select(...))` and similar constructs.

2. **Synchronous (Sync) Operations**:
   - **Where**: Everything else — character configuration, personas, providers, models, presets, prompt templates and fragments, lore, profiles, and so on.
   - **Implementation**: Uses the `psycopg2` blocking driver inside a synchronous SQLAlchemy session to avoid async overhead and keep the code simple.

Note that `chat_message`, `chat_session`, and `rag` keep **both** a sync `repository.py` and an async `repository_async.py`, using whichever fits the call site.


## 4. Repository Pattern

Each domain features a dedicated repository extending the generic `BaseRepository[T]` (for synchronous operations) or `AsyncBaseRepository[T]` (for the async paths). Both are parameterized on the ORM model type.

### Base Repository CRUD
The base classes handle common CRUD and query logic — `find_by_id`, `find_all`, `find_paginated`, `find_paginated_with_count`, `create`, `update`, `delete`, `count`, and `exists` — plus a small dynamic `_apply_filters` helper (operators like `__eq`, `__in`, `__ilike`). Writes use `flush()` rather than `commit()` so the **service layer** controls transaction boundaries; the repository also exposes `commit()`, `rollback()`, and `refresh()` for the service to call.

### Example Custom Repository
```python
class CharacterRepository(BaseRepository[Character]):
    def __init__(self, db: Session):
        super().__init__(db, Character)

    def find_by_name(self, name: str) -> Character | None:
        stmt = select(Character).where(Character.name == name)
        return self.db.execute(stmt).scalars().first()
```

Custom queries use SQLAlchemy 2.0 `select(...)` statements executed through `self.db`, not the legacy `session.query(...)` API.


## 5. Schema Migrations (Alembic)

Database schema alterations are strictly managed through Alembic.
- **Creating Migrations**: Always generated using Alembic's autogenerate tool:
  ```bash
  alembic revision --autogenerate -m "add_provider_last_synced_at"
  ```
- **Applying Migrations**: Applied via the command line (not at application startup — the
  lifespan handler only seeds default data):
  ```bash
  alembic upgrade head
  ```
