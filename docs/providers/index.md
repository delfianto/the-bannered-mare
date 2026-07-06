# LLM Providers

This section is the API reference behind The Bannered Mare's multi-provider adapter system.
Each page captures one provider's full surface — endpoints, authentication, request/response
schemas, streaming format, parameter allowlists, and provider-specific features — as the
implementation contract each `ProviderAdapter` must satisfy. Start with the
[Landscape & Gap Analysis](/providers/landscape) for the cross-provider view, then drill into a
specific provider.

::: warning Accuracy & provenance
These pages were authored as implementation guidelines (with the assistance of Claude Opus 4.6)
and represent each provider's API **as of its creation date** below. Providers frequently add,
deprecate, and change models, parameters, and behavior. Always consult the official
documentation before making implementation decisions.
:::

## Cloud Providers

| Provider | Coverage | Created |
|----------|----------|---------|
| [OpenAI](/providers/openai) | Chat Completions API (GPT-4o, o1/o3, …) | 2026-04-06 |
| [Anthropic](/providers/anthropic) | Messages API (Claude 4.x family) | 2026-04-06 |
| [Google Gemini](/providers/gemini) | Gemini API (Gemini 2.x family) | 2026-04-06 |
| [xAI](/providers/xai) | Grok API (Grok 4.10 / 4.20 family) | 2026-04-07 |
| [OpenRouter](/providers/openrouter) | Unified API (multi-provider routing) | 2026-04-06 |

## Local / Self-Hosted

| Provider | Coverage | Created |
|----------|----------|---------|
| [Ollama](/providers/ollama) | Native + OpenAI-compatible endpoints | 2026-04-06 |
| [Local Backends](/providers/local-backends) | llama.cpp · Oobabooga · vLLM · KoboldCpp · TabbyAPI | 2026-04-06 |

## Cross-Provider

| Page | Description | Created |
|------|-------------|---------|
| [Landscape & Gap Analysis](/providers/landscape) | Where the providers agree and diverge, and what the adapter layer must reconcile | 2026-04-06 |

## Official Documentation

| Provider | Documentation |
|----------|---------------|
| OpenAI | <https://platform.openai.com/docs/api-reference> |
| Anthropic | <https://docs.anthropic.com/en/api> |
| Google Gemini | <https://ai.google.dev/api> |
| xAI | <https://docs.x.ai/api> |
| OpenRouter | <https://openrouter.ai/docs> |
| Ollama | <https://github.com/ollama/ollama/blob/main/docs/api.md> |

---

*Reference for The Bannered Mare's `ProviderAdapter` system. Initial creation 2026-04-06; last
updated 2026-04-07.*
