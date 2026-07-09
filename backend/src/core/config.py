"""Application configuration using Pydantic Settings"""

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ = load_dotenv()

# A relative STORAGE_PATH resolves against the repo root, derived from this file's
# location (backend/src/core/config.py → parents[3]) rather than the process CWD.
# Without this, `just db-seed` (run from the repo root) and the server (run from
# backend/) would resolve "./storage" to different directories.
_REPO_ROOT = Path(__file__).resolve().parents[3]


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
    matching the pinned `embeddings.embedding` column). Selectable via `provider`:
    - `llamacpp` / `openai`: any OpenAI-compatible `/v1/embeddings` endpoint.
    - `ollama`: Ollama's native `/api/embed`.
    - `huggingface`: HF Text Embeddings Inference's native `/embed`. TEI has no
      OpenAI-compatible rerank route (text-embeddings-inference#683), so its
      native dialect is used for both embeddings and (later) reranking.
    """

    provider: str = "llamacpp"
    model: str = "embeddinggemma"
    dimensions: int = 768
    llamacpp_url: str = "http://localhost:8080"
    huggingface_url: str = "http://localhost:8080"
    ollama_url: str = "http://localhost:11434"
    openai_url: str = "https://api.openai.com/v1"
    openai_key_env: str = "OPENAI_API_KEY"
    # EmbeddingGemma is asymmetric — queries and documents need different prompts.
    # https://ai.google.dev/gemma/docs/embeddinggemma/model_card#prompt_instructions
    query_prefix: str = "task: search result | query: "
    document_prefix: str = "title: none | text: "


class RerankSettings(BaseModel):
    """Cross-encoder reranker over the RAG candidate set.

    Runs on a dedicated HF Text Embeddings Inference instance via its native
    `/rerank` (TEI serves one model per process and has no OpenAI-compatible
    rerank route — text-embeddings-inference#683). Disabled by default.

    When enabled the retriever casts a wide net: it pulls up to `candidates`
    vector hits WITHOUT the vector similarity floor (so the cross-encoder, not
    cosine distance, decides relevance), then keeps hits scoring at least
    `score_threshold` and cuts to `rag.max_results`.
    """

    enabled: bool = False
    huggingface_url: str = "http://localhost:8091"
    model: str = "BAAI/bge-reranker-v2-m3"  # informational; TEI serves a fixed model
    candidates: int = 30
    # Minimum reranker score (0-1, normalized) to keep a hit — this replaces the
    # vector similarity_threshold as the relevance floor whenever reranking is on.
    score_threshold: float = 0.3


class RAGSettings(BaseModel):
    """RAG system configuration"""

    enabled: bool = False
    embedding: EmbeddingSettings = EmbeddingSettings()
    rerank: RerankSettings = RerankSettings()
    chunk_size: int = 500
    chunk_overlap: int = 50
    similarity_threshold: float = 0.3
    max_results: int = 5
    query_messages: int = 2
    vectorize_messages: bool = True

    # --- VectorChord (vchordrq) search tuning ---
    # The embeddings.embedding column is served by a flat VectorChord vchordrq
    # RaBitQ index. These optional knobs are applied per search via `SET LOCAL`
    # (best-effort — ignored if the GUC/extension is absent). Leave as None to
    # use VectorChord's own defaults. `probes` is intentionally not exposed: it
    # only affects IVF (`lists`) indexes, and ours is flat.
    #
    # - vchordrq_epsilon: RaBitQ distance lower-bound conservativeness, range
    #   0.0-4.0 (VectorChord default 1.9). Higher = better recall, slower.
    # - vchordrq_max_scan_tuples: cap on tuples scanned *before* the WHERE
    #   filter. Raise it when the source_type/source_id filters are selective so
    #   the flat scan reaches enough matches to fill `max_results`.
    vchordrq_epsilon: float | None = None
    vchordrq_max_scan_tuples: int | None = None


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
    database_url: str = "postgresql://user:password@localhost:5432/bannered_mare"
    database: DatabaseSettings = DatabaseSettings()

    # Storage — root directory for all binary/generated files (character & persona
    # avatars, temp uploads, db backups). A relative value resolves against the repo
    # root; in Docker/production set an absolute path, e.g. STORAGE_PATH=/data.
    storage_path: str = Field(default="./storage", validate_default=True)

    @field_validator("storage_path")
    @classmethod
    def _resolve_storage_path(cls, value: str) -> str:
        """Normalize STORAGE_PATH to an absolute path (relative → repo root)."""
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = _REPO_ROOT / path
        return str(path.resolve())

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

    # Case-insensitive substrings matched against a model's identifier; any hit
    # drops it from discovery. These name fragments mark non-chat / non-RP model
    # families (image, video, audio, embeddings, retrieval, moderation, legacy
    # completion, and specialised tooling variants) that would only clutter the
    # picker — nobody roleplays with an embedding or "deep-research" model.
    # Override wholesale via the MODEL_BLACKLIST env var (JSON array).
    model_blacklist: list[str] = [
        # Image generation
        "dall-e",
        "gpt-image",
        "image",
        "imagen",
        "flux",
        "stable-diffusion",
        "sdxl",
        "midjourney",
        "ideogram",
        "recraft",
        # Video generation
        "sora",
        "veo",
        # Audio / speech / music (TTS, STT, music generation)
        "whisper",
        "tts",
        "audio",
        "speech",
        "transcribe",
        "lyria",
        # Embeddings, retrieval & rerankers
        "embed",
        "bge-",
        "gte-",
        "e5-",
        "clip-",
        "colbert",
        "rerank",
        # Moderation / safety classifiers
        "moderation",
        "guard",
        "shield",
        # Legacy completion / base models (not chat-formatted)
        "davinci",
        "babbage",
        # Specialised, non-conversational variants
        "realtime",
        "computer-use",
        "research",
        "ocr",
        # Outdated or off-task chat variants
        "gpt-3",  # GPT-3.x — obsolete for RP
        "codex",  # code-completion variants (e.g. gpt-5.x-codex)
        "latest",  # rolling "*-latest" auto-alias pointers
        "remm",  # ReMM-SLERP — ancient L2-13B RP merge
    ]

    # Vendors — the identifier's first path segment (e.g. "perplexity" in
    # "perplexity/sonar") — dropped wholesale from discovery: search-augmented,
    # code-edit, or otherwise off-task for RP, plus OpenRouter's own meta-routers
    # (auto / free / fusion / pareto / bodybuilder). Substring match, so
    # "bytedance" also covers "bytedance-seed". Override via MODEL_VENDOR_BLACKLIST.
    model_vendor_blacklist: list[str] = [
        "openrouter",
        "perplexity",
        "cohere",
        "reka",
        "bytedance",
        "sakana",
        "relace",
        "perceptron",
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
