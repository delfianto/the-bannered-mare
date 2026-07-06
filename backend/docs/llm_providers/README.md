# LLM Provider API Reference

> **Disclaimer:** These documents were created as implementation guidelines for building
> Candlekeep Core's multi-provider adapter architecture, authored with the assistance of
> Claude Opus 4.6. Each document attempts to capture the full API specification — endpoints,
> authentication, request/response schemas, streaming formats, parameter allowlists, and
> provider-specific features.
>
> **This information is subject to change.** LLM providers frequently add, deprecate, and
> modify models, parameters, and API behavior. We've done our best to represent the latest
> information as of each document's creation date, but this is by no means a 100% complete
> or perpetually accurate representation. **Always consult the official provider documentation
> for the most up-to-date information before making implementation decisions.**

---

## Documents

### Cloud Providers

| Document | Provider | Created |
|----------|----------|---------|
| [OPENAI.md](OPENAI.md) | OpenAI Chat Completions API (GPT-4o, o1/o3, etc.) | 2026-04-06 |
| [ANTHROPIC.md](ANTHROPIC.md) | Anthropic Messages API (Claude 4.x family) | 2026-04-06 |
| [GEMINI.md](GEMINI.md) | Google Gemini API (Gemini 2.x family) | 2026-04-06 |
| [XAI.md](XAI.md) | xAI Grok API (Grok 4.10/4.20 family) | 2026-04-07 |
| [OPENROUTER.md](OPENROUTER.md) | OpenRouter unified API (multi-provider routing) | 2026-04-06 |

### Local / Self-Hosted

| Document | Provider | Created |
|----------|----------|---------|
| [OLLAMA.md](OLLAMA.md) | Ollama API (native + OpenAI-compatible endpoints) | 2026-04-06 |
| [LOCAL_BACKENDS.md](LOCAL_BACKENDS.md) | llama.cpp, Oobabooga, vLLM, KoboldCpp, TabbyAPI | 2026-04-06 |

### Overview

| Document | Description | Created |
|----------|-------------|---------|
| [PROVIDERS.md](PROVIDERS.md) | Provider landscape overview and gap analysis | 2026-04-06 |

---

## Official Documentation Links

| Provider | Documentation |
|----------|---------------|
| OpenAI | https://platform.openai.com/docs/api-reference |
| Anthropic | https://docs.anthropic.com/en/api |
| Google Gemini | https://ai.google.dev/api |
| xAI | https://docs.x.ai/api |
| OpenRouter | https://openrouter.ai/docs |
| Ollama | https://github.com/ollama/ollama/blob/main/docs/api.md |

---

## Tool & Version Info

- **Author:** Claude Opus 4.6 (1M context)
- **Purpose:** Implementation reference for Candlekeep Core's `ProviderAdapter` system
- **Initial creation:** 2026-04-06
- **Last updated:** 2026-04-07
