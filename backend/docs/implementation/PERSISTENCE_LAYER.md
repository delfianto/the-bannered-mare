# The Bannered Mare: Persistence Layer Architecture

The persistence layer of The Bannered Mare manages relational data storage, schema migrations, and entity lifecycles using PostgreSQL in production and SQLite in test environments. It relies on SQLAlchemy 2.0 and Alembic.

---

## 1. Declarative Base and Base Model

All entities in the database inherit from `BaseModel` (defined in [base_model.py](../../src/core/persistence/base_model.py)), which is an abstract class built on SQLAlchemy's declarative mapping system.

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

---

## 2. Preventing Circular Imports (Centralized Model Definitions)

In a vertical-slices modular monolith, domains often reference each other (e.g., a `Chat` has a relationship with a `Character`, which in turn has a relationship with `Lorebook`). Placing ORM models directly inside domain folders can cause circular import issues.

To resolve this:
- All ORM database models are stored in [src/core/persistence/models/](../../src/core/persistence/models/) as separate modules (e.g., `character.py`, `chat.py`, `provider.py`).
- They are imported and re-exported from [src/core/persistence/models/__init__.py](../../src/core/persistence/models/__init__.py).
- Individual domain packages expose files like `models.py` which simply act as pass-through imports to the centralized persistence directory, preventing circular reference paths.

---

## 3. Asynchronous vs. Synchronous Operations

The Bannered Mare implements a **mixed-mode** synchronization policy to balance simplicity and performance:

1. **Asynchronous (Async) Operations**:
   - **Constraint**: Database interactions involving chat messages (which are highly concurrent, read/write heavy, and tied to real-time LLM streaming) **must be asynchronous**.
   - **Implementation**: Uses `asyncpg` with async SQLAlchemy sessions, executing via `await session.execute(select(...))` and similar constructs.

2. **Synchronous (Sync) Operations**:
   - **Constraint**: All other operations (metadata updates, character configuration, provider management, presets, etc.) are synchronous.
   - **Implementation**: Uses standard `psycopg` blocking driver calls inside a synchronous SQLAlchemy session to avoid async overhead and keep the code simple.

---

## 4. Repository Pattern

Each domain features a dedicated repository extending `BaseRepository` (for synchronous operations) or an async base repository.

### Synchronous Base Repository
Handles basic CRUD logic (`find_by_id`, `find_all`, `create`, `update`, `delete`) so developers don't have to rewrite queries for each model.

### Example Custom Repository
```python
class CharacterRepository(BaseRepository[Character]):
    def __init__(self, session: Session):
        super().__init__(session, Character)

    def find_by_tags(self, tags: list[str]) -> list[Character]:
        return self.session.query(Character).filter(
            Character.tags.overlap(tags)
        ).all()
```

---

## 5. Schema Migrations (Alembic)

Database schema alterations are strictly managed through Alembic.
- **Creating Migrations**: Always generated using Alembic's autogenerate tool:
  ```bash
  alembic revision --autogenerate -m "add_provider_last_synced_at"
  ```
- **Applying Migrations**: Handled automatically on backend service start or via command-line:
  ```bash
  alembic upgrade head
  ```
