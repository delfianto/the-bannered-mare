"""Application configuration using Pydantic Settings"""

from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ = load_dotenv()


class LoggingSettings(BaseModel):
    """Logging configuration"""

    level: str = "INFO"
    format: Literal["json", "console"] = "json"

    # Persisted audit logging (PostgreSQL). Master switch for the audit writer.
    audit_enabled: bool = True

    # Per-type toggles
    log_http_requests: bool = True
    log_llm_calls: bool = True
    log_errors: bool = True
    log_request_body: bool = False
    log_response_body: bool = False
    redact_api_keys: bool = True


class DatabaseSettings(BaseModel):
    """Database configuration"""

    # Connection Pool
    pool_size: int = Field(default=10, description="Number of persistent connections in the pool")
    max_overflow: int = Field(
        default=20, description="Maximum overflow connections beyond pool_size"
    )
    pool_timeout: int = Field(
        default=30, description="Seconds to wait for a connection from the pool"
    )
    pool_recycle: int = Field(
        default=3600, description="Recycle connections after this many seconds"
    )
    pool_pre_ping: bool = Field(default=True, description="Verify connections before using them")

    # Engine Configuration
    echo: bool = Field(default=False, description="Log all SQL statements")
    echo_pool: bool = Field(default=False, description="Log connection pool checkouts/checkins")


class EmbeddingSettings(BaseModel):
    """Embedding provider configuration.

    Defaults target a local llama.cpp server running EmbeddingGemma (768-dim,
    matching the pinned `embeddings.embedding` column). `ollama` and `openai`
    (any OpenAI-compatible endpoint) remain selectable via `provider`.
    """

    provider: str = "llamacpp"
    model: str = "embeddinggemma"
    dimensions: int = 768
    llamacpp_url: str = "http://localhost:8080"
    ollama_url: str = "http://localhost:11434"
    openai_url: str = "https://api.openai.com/v1"
    openai_key_env: str = "OPENAI_API_KEY"
    # EmbeddingGemma is asymmetric — queries and documents need different prompts.
    # https://ai.google.dev/gemma/docs/embeddinggemma/model_card#prompt_instructions
    query_prefix: str = "task: search result | query: "
    document_prefix: str = "title: none | text: "


class RAGSettings(BaseModel):
    """RAG system configuration"""

    enabled: bool = False
    embedding: EmbeddingSettings = EmbeddingSettings()
    chunk_size: int = 500
    chunk_overlap: int = 50
    similarity_threshold: float = 0.3
    max_results: int = 5
    query_messages: int = 2
    vectorize_messages: bool = True


class DiscoveryCacheSettings(BaseModel):
    """In-process cache for auto-detected provider model lists (Ollama/LM Studio).

    Named ``discovery_cache`` rather than ``model_cache`` — Pydantic reserves
    the ``model_`` attribute prefix on BaseModel subclasses.
    """

    enabled: bool = True
    ttl_seconds: int = 300


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/candlekeep"
    database: DatabaseSettings = DatabaseSettings()

    # Storage
    storage_path: str = "./storage"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["*"]

    # Security
    encryption_key: str = "your-encryption-key-here"

    # Logging
    logging: LoggingSettings = LoggingSettings()

    # RAG
    rag: RAGSettings = RAGSettings()

    # Local provider auto-detection
    discovery_cache: DiscoveryCacheSettings = DiscoveryCacheSettings()
    ollama_host: str | None = Field(
        default=None, description="Initial base URL for the seeded Ollama provider"
    )
    lmstudio_host: str | None = Field(
        default=None, description="Initial base URL for the seeded LM Studio provider"
    )

    model_blacklist: list[str] = [
        "dall-e",
        "whisper",
        "tts-",
        "embedding",
        "moderation",
        "flux",
        "stable-diffusion",
        "imagen",
        "sora",
        "veo",
        "audio-",
        "bge-",
        "clip-",
        "rerank",
        "colbert",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )


# Global settings instance
settings = Settings()
