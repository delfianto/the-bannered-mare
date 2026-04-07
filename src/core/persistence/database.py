"""Database connection and session management"""

from collections.abc import AsyncGenerator, Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.core.config import settings

# Create SQLAlchemy engine with explicit connection pooling
engine = create_engine(
    settings.database_url,
    # Connection Pool Configuration
    poolclass=QueuePool,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=settings.database.pool_pre_ping,
    # Engine Configuration
    echo=settings.database.echo,
    echo_pool=settings.database.echo_pool,
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# SYNCHRONOUS SESSION
def get_db() -> Generator[Session]:
    """
    Dependency function to get a database session.

    Each request gets a session from the connection pool.
    The session is automatically closed after the request,
    returning the connection to the pool for reuse.

    Usage in FastAPI endpoints:
        @app.get("/items")
        def read_items(db: DbSession):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Type alias for database session dependency
DbSession = Annotated[Session, Depends(get_db)]


# ASYNCHRONOUS SESSION
def get_async_db_url(url: str) -> str:
    """Ensure the database URL uses an async driver"""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


# Create async engine
async_engine = create_async_engine(
    get_async_db_url(settings.database_url),
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    pool_recycle=settings.database.pool_recycle,
    pool_pre_ping=settings.database.pool_pre_ping,
    echo=settings.database.echo,
    echo_pool=settings.database.echo_pool,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Important: prevents lazy loading issues after commit
)


async def get_async_db() -> AsyncGenerator[AsyncSession]:
    """
    Dependency for asynchronous database session.

    Used by: Chat and Message domains for streaming operations

    Usage:
        @router.post("/stream")
        async def stream_endpoint(db: AsyncDbSession):
            ...
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


AsyncDbSession = Annotated[AsyncSession, Depends(get_async_db)]
