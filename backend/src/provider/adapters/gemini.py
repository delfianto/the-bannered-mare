"""Google Gemini generateContent API adapter."""

import json
from typing import Any
from urllib.parse import urlencode

from src.provider.adapters.base import (
    CompletionResponse,
    ProviderAdapter,
    StreamChunk,
    TokenUsage,
)

_FINISH_REASON_MAP: dict[str, str] = {
    "STOP": "stop",
    "MAX_TOKENS": "length",
    "SAFETY": "content_filter",
    "RECITATION": "content_filter",
    "LANGUAGE": "content_filter",
    "BLOCKLIST": "content_filter",
    "PROHIBITED_CONTENT": "content_filter",
    "SPII": "content_filter",
    "MALFORMED_FUNCTION_CALL": "stop",
}

# Parameters that map into generationConfig
_GENERATION_CONFIG_MAP: dict[str, str] = {
    "temperature": "temperature",
    "top_p": "topP",
    "top_k": "topK",
    "max_output_tokens": "maxOutputTokens",
    "stop_sequences": "stopSequences",
    "frequency_penalty": "frequencyPenalty",
    "presence_penalty": "presencePenalty",
    "seed": "seed",
}

_ROLE_MAP: dict[str, str] = {"assistant": "model", "user": "user"}


class GeminiAdapter(ProviderAdapter):
    """Adapter for the Google Gemini generateContent API."""

    def build_url(
        self,
        base_url: str,
        model: str,
        stream: bool,
        api_key: str | None = None,
    ) -> str:
        base = base_url.rstrip("/")

        if stream:
            action = "streamGenerateContent"
            params: dict[str, str] = {"alt": "sse"}
        else:
            action = "generateContent"
            params = {}

        if api_key:
            params["key"] = api_key

        url = f"{base}/v1beta/models/{model}:{action}"
        if params:
            url = f"{url}?{urlencode(params)}"
        return url

    def build_headers(self, api_key: str | None) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def build_payload(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_parts.append(content)
                continue

            gemini_role = _ROLE_MAP.get(role, role)
            contents.append({"role": gemini_role, "parts": [{"text": content}]})

        payload: dict[str, Any] = {"contents": contents}

        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        generation_config: dict[str, Any] = {}
        for param_key, config_key in _GENERATION_CONFIG_MAP.items():
            value = parameters.get(param_key)
            if value is not None:
                generation_config[config_key] = value

        # max_tokens → maxOutputTokens fallback
        if "maxOutputTokens" not in generation_config and "max_tokens" in parameters:
            generation_config["maxOutputTokens"] = parameters["max_tokens"]

        # Thinking controls: 2.5 uses thinkingBudget (int tokens), 3.x uses
        # thinkingLevel (enum). They are mutually exclusive (sending both 400s), and
        # a family declares only one, so at most one is present.
        thinking_config: dict[str, Any] = {}
        thinking_budget = parameters.get("thinking_budget")
        if thinking_budget is not None:
            thinking_config["thinkingBudget"] = thinking_budget
        thinking_level = parameters.get("thinking_level")
        if thinking_level is not None:
            thinking_config["thinkingLevel"] = thinking_level
        if thinking_config:
            generation_config["thinkingConfig"] = thinking_config

        media_resolution = parameters.get("media_resolution")
        if media_resolution is not None:
            generation_config["mediaResolution"] = media_resolution

        if generation_config:
            payload["generationConfig"] = generation_config

        safety_settings = parameters.get("safety_settings")
        if safety_settings:
            payload["safetySettings"] = safety_settings

        return payload

    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        candidates = data.get("candidates", [{}])
        candidate = candidates[0] if candidates else {}

        parts = candidate.get("content", {}).get("parts", [])
        text_parts = [p.get("text", "") for p in parts if "text" in p and not p.get("thought")]
        content = "".join(text_parts)

        # Gemini 2.5+ marks thinking parts with thought: true
        thought_parts = [p.get("text", "") for p in parts if p.get("thought")]
        reasoning = "".join(thought_parts) or None

        raw_reason: str = candidate.get("finishReason") or "STOP"
        finish_reason = _FINISH_REASON_MAP.get(raw_reason, raw_reason.lower())

        usage_data = data.get("usageMetadata", {})

        return CompletionResponse(
            content=content,
            finish_reason=finish_reason,
            usage=TokenUsage(
                input_tokens=usage_data.get("promptTokenCount", 0),
                output_tokens=usage_data.get("candidatesTokenCount", 0),
                total_tokens=usage_data.get("totalTokenCount", 0),
                cache_read_tokens=usage_data.get("cachedContentTokenCount", 0),
            ),
            reasoning=reasoning,
            raw=data,
        )

    def parse_stream_line(self, line: str) -> StreamChunk | None:
        if not line.startswith("data: "):
            return None

        data_str = line[6:]

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return None

        candidates = data.get("candidates", [])
        if not candidates:
            return None

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text_parts = [p.get("text", "") for p in parts if "text" in p and not p.get("thought")]
        content = "".join(text_parts) if text_parts else None

        thought_parts = [p.get("text", "") for p in parts if p.get("thought")]
        reasoning = "".join(thought_parts) if thought_parts else None

        raw_reason = candidate.get("finishReason")
        finish_reason = None
        if raw_reason:
            finish_reason = _FINISH_REASON_MAP.get(raw_reason, raw_reason.lower())

        usage = None
        usage_data = data.get("usageMetadata")
        if usage_data:
            usage = TokenUsage(
                input_tokens=usage_data.get("promptTokenCount", 0),
                output_tokens=usage_data.get("candidatesTokenCount", 0),
                total_tokens=usage_data.get("totalTokenCount", 0),
                cache_read_tokens=usage_data.get("cachedContentTokenCount", 0),
            )

        if content is None and reasoning is None and finish_reason is None and usage is None:
            return None

        return StreamChunk(
            content=content, reasoning=reasoning, finish_reason=finish_reason, usage=usage
        )

    def get_timeout(self, model: str) -> float:
        return 120.0
