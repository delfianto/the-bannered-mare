"""Default discovery blacklists — reference data, not tunable config.

These seed ``Settings.model_blacklist`` / ``model_vendor_blacklist`` (still
overridable via the MODEL_BLACKLIST / MODEL_VENDOR_BLACKLIST env vars). Kept out
of config.py so the settings class stays about *configuration*, not payload.
"""

# Case-insensitive substrings matched against a model's identifier; any hit drops
# it from discovery. These name fragments mark non-chat / non-RP families (image,
# video, audio, embeddings, retrieval, moderation, legacy completion, specialised
# tooling) that would only clutter the picker — nobody roleplays with an embedding
# or "deep-research" model.
DEFAULT_MODEL_BLACKLIST: list[str] = [
    # Image generation
    "dall-e",
    "flux",
    "gpt-image",
    "ideogram",
    "image",
    "imagen",
    "midjourney",
    "recraft",
    "sdxl",
    "stable-diffusion",
    # Video generation
    "sora",
    "veo",
    # Audio / speech / music (TTS, STT, music generation)
    "audio",
    "lyria",
    "speech",
    "transcribe",
    "tts",
    "whisper",
    # Embeddings, retrieval & rerankers
    "bge-",
    "clip-",
    "colbert",
    "e5-",
    "embed",
    "gte-",
    "rerank",
    # Moderation / safety classifiers
    "guard",
    "moderation",
    "safety",  # e.g. nemotron content-safety
    "shield",
    # Code / developer models
    "code",  # codestral, qwen *-coder, kimi-*-code, arcee coder, kat-coder…
    "devstral",
    # Legacy completion / base models (not chat-formatted)
    "babbage",
    "davinci",
    # Specialised, non-conversational variants
    "computer-use",
    "ocr",
    "realtime",
    "research",
    "search",  # web-search-augmented (gpt-4o-search-preview, gpt-5-search-api)
    # Outdated or off-task chat variants
    "codex",  # code-completion variants (e.g. gpt-5.x-codex)
    "gpt-3",  # GPT-3.x — obsolete for RP
    # NB: no blanket "latest" rule — OpenAI's chat SKUs are only callable via
    # their "-chat-latest" rolling alias, so dropping "latest" would hide them.
    # Redundant *dated* snapshots are handled by _OPENAI_ALIAS_RE instead.
    "remm",  # ReMM-SLERP — ancient L2-13B RP merge
]

# Vendors — the identifier's first path segment (e.g. "perplexity" in
# "perplexity/sonar") — dropped wholesale: search-augmented, code-edit, or
# otherwise off-task for RP, plus OpenRouter's own meta-routers. Substring match,
# so "bytedance" also covers "bytedance-seed".
DEFAULT_MODEL_VENDOR_BLACKLIST: list[str] = [
    "bytedance",
    "cohere",
    "morph",  # code fast-apply / edit
    "openrouter",
    "perceptron",
    "perplexity",
    "reka",
    "relace",
    "sakana",
    "writer",  # Palmyra — enterprise business writing
]
