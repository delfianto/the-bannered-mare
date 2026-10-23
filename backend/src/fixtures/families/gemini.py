"""Google Gemini model family seed data (base-model-generation keyed).

Grouped at the parameter-contract boundary on the 2.5 -> 3 line. Gemini 2.5
(Pro / Flash / Flash-Lite) keeps the full sampling surface — top_k, frequency/
presence penalties — and a numeric thinking budget. Gemini 3.x (3.0 / 3.1
Pro / Flash / Lite) dropped top_k and the penalties, defaults temperature to 1.0,
and replaced the budget with thinking_level plus a media_resolution control.
3.0 and 3.1 share one family (identical contract). Gemini 3.5 and 3.6 each strip
sampling further (no temperature/top_p/top_k) and get their own families. Served
via the Google API or OpenRouter.

Parameter surface per the Gemini API docs (ai.google.dev/gemini-api/docs/gemini-3,
.../docs/thinking).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    GEMINI_3_SAMPLING,
    GEMINI_35_SAMPLING,
    GEMINI_SAMPLING,
)

GEMINI_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Gemini 2.5",
        "family_identifier": "google/gemini-2.5",
        "description": (
            "Google Gemini 2.5 Pro / Flash / Flash-Lite. 1M context, full sampling surface "
            "(top_k + penalties) and a numeric thinking budget."
        ),
        "provider_types": ["google", "openrouter"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            **GEMINI_SAMPLING,
            # -1 = dynamic (model decides); 0 = off (Flash / Flash-Lite only).
            "thinking_budget": {"type": "int", "default": -1, "min_value": -1, "max_value": 32768},
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "gemini",
            "developer": "google",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"],
        },
    },
    {
        "name": "Gemini 3",
        "family_identifier": "google/gemini-3",
        "description": (
            "Google Gemini 3.0 / 3.1 Pro / Flash / Flash-Lite. 1M context. thinking_level "
            "(low/medium/high) + media_resolution; top_k and penalties removed, temperature "
            "defaults to 1.0 (changing it is discouraged)."
        ),
        "provider_types": ["google", "openrouter"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            **GEMINI_3_SAMPLING,
            "thinking_level": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high"],
            },
            "media_resolution": {
                "type": "enum",
                "default": "MEDIA_RESOLUTION_MEDIUM",
                "str_values": [
                    "MEDIA_RESOLUTION_LOW",
                    "MEDIA_RESOLUTION_MEDIUM",
                    "MEDIA_RESOLUTION_HIGH",
                    "MEDIA_RESOLUTION_ULTRA_HIGH",
                ],
            },
        },
        "unsupported_parameters": [
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "thinking_budget",
        ],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "gemini",
            "developer": "google",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": [
                "gemini-3-flash-preview",
                "gemini-3.1-pro-preview",
                "gemini-3.1-flash-lite",
            ],
        },
    },
    {
        "name": "Gemini 3.5",
        "family_identifier": "google/gemini-3.5",
        "description": (
            "Google Gemini 3.5 Flash. 1M context. Removes temperature/top_p/top_k entirely; "
            "thinking_level (minimal/low/medium/high, default medium) + media_resolution."
        ),
        "provider_types": ["google", "openrouter", "opencode"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            **GEMINI_35_SAMPLING,
            "thinking_level": {
                "type": "enum",
                "default": "medium",
                "str_values": ["minimal", "low", "medium", "high"],
            },
            "media_resolution": {
                "type": "enum",
                "default": "MEDIA_RESOLUTION_MEDIUM",
                "str_values": [
                    "MEDIA_RESOLUTION_LOW",
                    "MEDIA_RESOLUTION_MEDIUM",
                    "MEDIA_RESOLUTION_HIGH",
                    "MEDIA_RESOLUTION_ULTRA_HIGH",
                ],
            },
        },
        "unsupported_parameters": [
            "temperature",
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "thinking_budget",
        ],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "gemini",
            "developer": "google",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": [
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "google/gemini-3.5-flash",
                "google/gemini-3.5-flash-lite",
            ],
        },
    },
    {
        "name": "Gemini 3.6",
        "family_identifier": "google/gemini-3.6",
        "description": (
            "Google Gemini 3.6 Flash / Flash-Lite. 1M context. Removes temperature/top_p/top_k "
            "entirely; thinking_level (minimal/low/medium/high, default medium) + media_resolution."
        ),
        "provider_types": ["google", "openrouter"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            **GEMINI_35_SAMPLING,
            "thinking_level": {
                "type": "enum",
                "default": "medium",
                "str_values": ["minimal", "low", "medium", "high"],
            },
            "media_resolution": {
                "type": "enum",
                "default": "MEDIA_RESOLUTION_MEDIUM",
                "str_values": [
                    "MEDIA_RESOLUTION_LOW",
                    "MEDIA_RESOLUTION_MEDIUM",
                    "MEDIA_RESOLUTION_HIGH",
                    "MEDIA_RESOLUTION_ULTRA_HIGH",
                ],
            },
        },
        "unsupported_parameters": [
            "temperature",
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "thinking_budget",
        ],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "gemini",
            "developer": "google",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["gemini-3.6-flash", "gemini-3.6-flash-lite"],
        },
    },
    # Catalog refresh: 2026-10-23; https://ai.google.dev/gemini-api/docs/models
    {
        "name": "Gemini 3.8",
        "family_identifier": "google/gemini-3.8",
        "description": "Gemini 3.8. 1M context; low/medium/high thinking only, no sampling parameters. "
        "Standard synchronous output is capped at 65,536 tokens.",
        "provider_types": ["google", "openrouter"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            "stop_sequences": {"type": "list", "item_schema": {"type": "string"}},
            "safety_settings": {
                "type": "list",
                "default": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "enum",
                            "str_values": [
                                "HARM_CATEGORY_HARASSMENT",
                                "HARM_CATEGORY_HATE_SPEECH",
                                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                "HARM_CATEGORY_DANGEROUS_CONTENT",
                                "HARM_CATEGORY_CIVIC_INTEGRITY",
                            ],
                        },
                        "threshold": {
                            "type": "enum",
                            "default": "BLOCK_NONE",
                            "str_values": [
                                "OFF",
                                "BLOCK_NONE",
                                "BLOCK_ONLY_HIGH",
                                "BLOCK_MEDIUM_AND_ABOVE",
                                "BLOCK_LOW_AND_ABOVE",
                            ],
                        },
                    },
                },
            },
            "thinking_level": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high"],
            },
            "media_resolution": {
                "type": "enum",
                "default": "MEDIA_RESOLUTION_MEDIUM",
                "str_values": [
                    "MEDIA_RESOLUTION_LOW",
                    "MEDIA_RESOLUTION_MEDIUM",
                    "MEDIA_RESOLUTION_HIGH",
                    "MEDIA_RESOLUTION_ULTRA_HIGH",
                ],
            },
        },
        "unsupported_parameters": [
            "temperature",
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "thinking_budget",
        ],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "gemini",
            "developer": "google",
            "context_window": 1048576,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["gemini-3.8-flash", "google/gemini-3.8-flash"],
        },
    },
    {
        "name": "Gemini 4 Argon",
        "family_identifier": "google/gemini-4",
        "description": "Gemini 4 Argon. 1M context; low/medium/high thinking only, no sampling "
        "parameters. Standard synchronous output is capped at 65,536 tokens.",
        "provider_types": ["google", "openrouter"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            "stop_sequences": {"type": "list", "item_schema": {"type": "string"}},
            "safety_settings": {
                "type": "list",
                "default": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "enum",
                            "str_values": [
                                "HARM_CATEGORY_HARASSMENT",
                                "HARM_CATEGORY_HATE_SPEECH",
                                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                "HARM_CATEGORY_DANGEROUS_CONTENT",
                                "HARM_CATEGORY_CIVIC_INTEGRITY",
                            ],
                        },
                        "threshold": {
                            "type": "enum",
                            "default": "BLOCK_NONE",
                            "str_values": [
                                "OFF",
                                "BLOCK_NONE",
                                "BLOCK_ONLY_HIGH",
                                "BLOCK_MEDIUM_AND_ABOVE",
                                "BLOCK_LOW_AND_ABOVE",
                            ],
                        },
                    },
                },
            },
            "thinking_level": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high"],
            },
            "media_resolution": {
                "type": "enum",
                "default": "MEDIA_RESOLUTION_MEDIUM",
                "str_values": [
                    "MEDIA_RESOLUTION_LOW",
                    "MEDIA_RESOLUTION_MEDIUM",
                    "MEDIA_RESOLUTION_HIGH",
                    "MEDIA_RESOLUTION_ULTRA_HIGH",
                ],
            },
        },
        "unsupported_parameters": [
            "temperature",
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "thinking_budget",
        ],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "gemini",
            "developer": "google",
            "context_window": 1048576,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["gemini-4-argon", "google/gemini-4-argon"],
            "note": "Unified input/output context; implicit caching only. Long decode "
            "requires a separate background/continuation flow.",
        },
    },
]
