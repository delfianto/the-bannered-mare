"""
Seed data for parameter definitions, specifically for Roleplay contexts.
Updated to match all parameters used in model_families.py

Also provides reusable parameter schemas to eliminate duplication across
per-provider model family files.
"""

from typing import Any

from src.fixtures.model_families import (
    BooleanParameterSchema,
    JsonParameterSchema,
    ListParameterSchema,
    NumericParameterSchema,
)

# ---------------------------------------------------------------------------
# Reusable parameter schema blocks
# ---------------------------------------------------------------------------

TEMPERATURE: NumericParameterSchema = {
    "type": "float",
    "default": 1.0,
    "min_value": 0.0,
    "max_value": 2.0,
}

TOP_P: NumericParameterSchema = {
    "type": "float",
    "default": 1.0,
    "min_value": 0.0,
    "max_value": 1.0,
}

TOP_P_95: NumericParameterSchema = {
    "type": "float",
    "default": 0.95,
    "min_value": 0.0,
    "max_value": 1.0,
}

TOP_K: NumericParameterSchema = {
    "type": "int",
    "default": 40,
    "min_value": 1,
}

FREQUENCY_PENALTY: NumericParameterSchema = {
    "type": "float",
    "default": 0.0,
    "min_value": -2.0,
    "max_value": 2.0,
}

PRESENCE_PENALTY: NumericParameterSchema = {
    "type": "float",
    "default": 0.0,
    "min_value": -2.0,
    "max_value": 2.0,
}

STOP_LIST: ListParameterSchema = {
    "type": "list",
    "item_schema": {"type": "string"},
}

STREAM: BooleanParameterSchema = {"type": "boolean", "default": True}

RESPONSE_FORMAT: JsonParameterSchema = {"type": "json", "default": None}

# Gemini safety settings schema (shared by all Gemini families)
GEMINI_SAFETY_SETTINGS: dict[str, Any] = {
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
                ],
            },
            "threshold": {
                "type": "enum",
                "default": "BLOCK_NONE",
                "str_values": [
                    "BLOCK_NONE",
                    "BLOCK_LOW_AND_ABOVE",
                    "BLOCK_MEDIUM_AND_ABOVE",
                    "BLOCK_HIGH_AND_ABOVE",
                ],
            },
        },
    },
}

# ---------------------------------------------------------------------------
# Composable parameter bundles
# ---------------------------------------------------------------------------

OPENAI_SAMPLING: dict[str, Any] = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "frequency_penalty": FREQUENCY_PENALTY,
    "presence_penalty": PRESENCE_PENALTY,
    "stop": STOP_LIST,
    "stream": STREAM,
    "response_format": RESPONSE_FORMAT,
}

OPENAI_THINKING_COMMON: dict[str, Any] = {
    "stop": STOP_LIST,
    "stream": STREAM,
    "response_format": RESPONSE_FORMAT,
}

XAI_BASE: dict[str, Any] = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "stream": STREAM,
}

GEMINI_SAMPLING: dict[str, Any] = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P_95,
    "top_k": TOP_K,
    "stop_sequences": STOP_LIST,
    "frequency_penalty": FREQUENCY_PENALTY,
    "presence_penalty": PRESENCE_PENALTY,
    "safety_settings": GEMINI_SAFETY_SETTINGS,
}

# Gemini 3.x dropped top_k and the frequency/presence penalties, and discourages
# changing temperature from its 1.0 default. Thinking moved from a numeric budget
# to thinking_level (+ the new media_resolution control), declared per family.
GEMINI_3_SAMPLING: dict[str, Any] = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P_95,
    "stop_sequences": STOP_LIST,
    "safety_settings": GEMINI_SAFETY_SETTINGS,
}

# Gemini 3.5 went further than 3.0/3.1: temperature, top_p, and top_k are removed
# outright (not just discouraged). Only stop/safety remain alongside thinking_level
# (which gains a "minimal" tier, default medium) and media_resolution.
GEMINI_35_SAMPLING: dict[str, Any] = {
    "stop_sequences": STOP_LIST,
    "safety_settings": GEMINI_SAFETY_SETTINGS,
}

# Shared Claude transport/sampling. 4.5 exposes an explicit thinking
# budget_tokens; 4.6+ moved to adaptive thinking (no budget) plus an `effort`
# enum declared per tier (Opus also adds a "max" tier and top_k up to 500).
# NOTE: temperature and top_p are mutually exclusive on every Claude 4.x model
# (sending both 400s) — model seeds must set at most one. Opus 4.7+/Fable drop
# sampling parameters entirely; see CLAUDE_47_BASE.
CLAUDE_45_BASE: dict[str, Any] = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "top_k": TOP_K,
    "stop_sequences": STOP_LIST,
    "stream": STREAM,
    "system": {"type": "string"},
    "thinking": {
        "type": "object",
        "properties": {
            "type": {"type": "enum", "str_values": ["enabled", "disabled"]},
            "budget_tokens": {"type": "int", "min_value": 1024, "max_value": 20000},
        },
    },
}

CLAUDE_46_BASE: dict[str, Any] = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "top_k": TOP_K,
    "stop_sequences": STOP_LIST,
    "stream": STREAM,
    "system": {"type": "string"},
    "thinking": {
        "type": "object",
        "properties": {
            "type": {"type": "enum", "str_values": ["enabled", "disabled"]},
        },
    },
}

# Opus 4.7+/Fable removed temperature/top_p/top_k entirely (400 if sent) and use
# adaptive thinking only (budget_tokens removed). The `effort` enum gains "xhigh".
CLAUDE_47_BASE: dict[str, Any] = {
    "stop_sequences": STOP_LIST,
    "stream": STREAM,
    "system": {"type": "string"},
    "thinking": {
        "type": "object",
        "properties": {
            "type": {"type": "enum", "str_values": ["adaptive", "disabled"]},
        },
    },
}

# ---------------------------------------------------------------------------
# User-facing parameter descriptions (unchanged)
# ---------------------------------------------------------------------------

PARAMETER_DEFINITIONS_SEED_DATA = {
    # --- 1. Creativity & Randomness ---
    "temperature": {
        "label": "Temperature (Creativity)",
        "short_info": "Controls how predictable or wild the character's responses are.",
        "detailed_info": (
            "Determines how 'safe' the AI plays it. "
            "Low values (0.5-0.7) make characters consistent, logical, and sticky to their definitions, but potentially boring. "
            "High values (0.9-1.2) allow for creative phrasing, unexpected plot twists, and emotional volatility, but risk incoherence. "
            "For ERP/RP, slightly higher (0.85-1.0) is often preferred to keep the interaction dynamic."
        ),
    },
    "top_p": {
        "label": "Top P (Nucleus Sampling)",
        "short_info": "Filters out unlikely words. Determines vocabulary breadth.",
        "detailed_info": (
            "Acts as a sanity filter. A value of 0.9 means the AI only considers the top 90% of likely words. "
            "Lowering this helps if the character starts speaking gibberish or using made-up words at high temperatures. "
            "Leave at 1.0 if you want the full range of the model's vocabulary."
        ),
    },
    "top_k": {
        "label": "Top K",
        "short_info": "Hard limit on vocabulary choices. Stabilizes output.",
        "detailed_info": (
            "Strictly limits the AI to choosing from the top K best words. "
            "Useful for anime-style or smaller models to prevent them from 'breaking' or going off-track. "
            "For modern models (Claude/Gemini), higher values (40-100) allow for more literary flair and rare descriptors."
        ),
    },
    # --- 2. Repetition Control (The "Anti-Loop" Settings) ---
    "frequency_penalty": {
        "label": "Frequency Penalty (Repetition)",
        "short_info": "Punishes words that have been used many times.",
        "detailed_info": (
            "Prevents the character from getting stuck in loops (e.g., saying 'smirks' or 'chuckles' every sentence). "
            "Turn this up if the character sounds like a broken record. "
            "Too high, and the grammar may break as it runs out of common words like 'the' or 'a'."
        ),
    },
    "presence_penalty": {
        "label": "Presence Penalty (Variety)",
        "short_info": "Punishes words that have appeared at least once.",
        "detailed_info": (
            "Encourages the model to introduce NEW topics and words rather than dwelling on the current scene. "
            "Useful if the RP feels stagnant and you want the character to push the plot forward."
        ),
    },
    # --- 3. Length & Formatting ---
    "max_completion_tokens": {
        "label": "Max Response Length (OpenAI/xAI)",
        "short_info": "Hard limit on how much the character can write.",
        "detailed_info": (
            "The maximum text generation allowed. "
            "Lower this if you want snappy dialogue or short emotes. "
            "Raise this for slow-burn, novella-style responses. "
            "Used by OpenAI models (GPT-4, GPT-5 series) and xAI Grok models. "
            "xAI deprecated max_tokens in favor of this parameter."
        ),
    },
    "max_tokens": {
        "label": "Max Response Length (Anthropic)",
        "short_info": "Hard limit on how much the character can write.",
        "detailed_info": (
            "The maximum text generation allowed. Set higher for 'Purple Prose' or detailed scene descriptions. "
            "Used by Anthropic (Claude) and OpenRouter models."
        ),
    },
    "max_output_tokens": {
        "label": "Max Response Length (Google)",
        "short_info": "Hard limit on how much the character can write.",
        "detailed_info": ("The maximum text generation allowed. Used by Google Gemini models."),
    },
    "num_ctx": {
        "label": "Context Window (Ollama)",
        "short_info": "Maximum context length for local models.",
        "detailed_info": (
            "Controls how much chat history the model can 'remember' at once. "
            "Higher values allow for longer RPs without forgetting plot details, but use more RAM. "
            "Used by Ollama (local GGUF models)."
        ),
    },
    "stop": {
        "label": "Stop Sequences (OpenAI)",
        "short_info": "Keywords that force the AI to stop typing immediately.",
        "detailed_info": (
            "Crucial for RP to prevent the AI from impersonating YOU. "
            "Common settings include your username, 'User:', or '\\n\\n'. "
            "Tells the model: 'You are done, now it is my turn'."
        ),
    },
    "stop_sequences": {
        "label": "Stop Sequences (Anthropic/Google)",
        "short_info": "Keywords that force the AI to stop typing immediately.",
        "detailed_info": (
            "Same purpose as 'stop', but used by Anthropic (Claude) and Google (Gemini) models. "
            "Prevents the AI from roleplaying as you or continuing beyond natural turn boundaries."
        ),
    },
    # --- 4. Advanced Reasoning & Thinking ---
    "reasoning_effort": {
        "label": "Reasoning Effort (GPT-5)",
        "short_info": "How hard the model thinks about the scenario context.",
        "detailed_info": (
            "Controls the depth of the internal thought chain in GPT-5 reasoning models. "
            "'high' is useful for complex lore checks, solving riddles, or political intrigue RPs where keeping facts straight is critical. "
            "'low' or 'minimal' is faster and better for casual chat. For RP, use 'low' to minimize reasoning overhead."
        ),
    },
    "thinking": {
        "label": "Thinking Mode (Claude)",
        "short_info": "Enable internal monologue before speaking.",
        "detailed_info": (
            "Allows the character to 'think' silently before replying. "
            "Incredible for RP: the character can plan lies, weigh emotional reactions, or recall obscure lore without polluting the chat log. "
            "Claude 4.5: set budget_tokens (e.g., 2000-10000) to control thinking depth. "
            "Claude 4.6: use the 'effort' parameter instead (budget_tokens is deprecated). "
            "Disable with type='disabled' for normal chat."
        ),
    },
    "effort": {
        "label": "Effort Level (Claude 4.6)",
        "short_info": "Controls adaptive thinking depth in Claude 4.6 models.",
        "detailed_info": (
            "Replaces budget_tokens in Claude 4.6. The model dynamically decides when and how much to think. "
            "'low' is fast with minimal reasoning — best for casual RP chat. "
            "'medium' balances speed and depth. "
            "'high' (default) gives thorough reasoning — good for complex plot-heavy scenes. "
            "'max' (Opus only) maximizes reasoning for the most intricate scenarios. "
            "For RP, 'low' keeps responses snappy while 'high' helps maintain lore consistency."
        ),
    },
    "thinking_level": {
        "label": "Thinking Level (Gemini 3.0)",
        "short_info": "Depth of reasoning in Gemini 3.0 models.",
        "detailed_info": (
            "Controls how much internal reasoning Gemini 3.0 uses before responding. "
            "'minimal' keeps responses fast and natural for RP. "
            "'high' is for complex reasoning tasks. For most RP scenarios, stick with 'minimal' or 'low'."
        ),
    },
    "summary": {
        "label": "Summary Mode (GPT-5.x)",
        "short_info": "Controls response verbosity in GPT-5.x models.",
        "detailed_info": (
            "Available in GPT-5.1/5.2 chat and thinking models. "
            "'concise' gives shorter, punchier responses. "
            "'detailed' provides more elaborate scene descriptions. "
            "'auto' lets the model decide based on context. For RP, 'concise' often works best to avoid bloat."
        ),
    },
    "verbosity": {
        "label": "Verbosity (GPT-5 Reasoning)",
        "short_info": "How much the reasoning model explains itself.",
        "detailed_info": (
            "Controls how much the GPT-5 reasoning models explain their thought process. "
            "'low' minimizes reasoning tokens and speeds up responses. "
            "'high' shows more of the internal chain-of-thought. For RP, use 'low' to avoid exposing meta-reasoning."
        ),
    },
    # --- 5. System & Context ---
    "system": {
        "label": "System Prompt Override",
        "short_info": "The core instructions defining the world and character.",
        "detailed_info": (
            "Usually handled automatically by your Character Card. "
            "Overrides the base instructions. Use this to enforce global rules like 'Write in third person past tense' or 'NSFW allowed'. "
            "Used by Claude models."
        ),
    },
    "metadata": {
        "label": "Request Metadata (Claude Opus)",
        "short_info": "Custom metadata for request tracking.",
        "detailed_info": (
            "Allows passing arbitrary metadata with Claude Opus requests. "
            "Primarily for analytics and tracking purposes. Not typically needed for RP."
        ),
    },
    # --- 6. Safety & Format ---
    "safety_settings": {
        "label": "Safety Filters (Gemini)",
        "short_info": "Content filtering sensitivity.",
        "detailed_info": (
            "Controls how aggressive Gemini is about blocking NSFW or violent content. "
            "For RP/ERP, set all categories to 'BLOCK_NONE' to prevent interruptions. "
            "Categories include: HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT, DANGEROUS_CONTENT."
        ),
    },
    "response_format": {
        "label": "Response Format",
        "short_info": "Force JSON or Text structure.",
        "detailed_info": (
            "Usually not used for chat, but can force the model to output structured data for game mechanics (e.g. inventory updates). "
            "Used by OpenAI models. Leave unset for normal RP."
        ),
    },
    "stream": {
        "label": "Stream Response",
        "short_info": "Typewriter effect.",
        "detailed_info": (
            "If enabled, you see the text appearing as it is written (SSE streaming). "
            "If disabled, you wait until the whole message is done. "
            "Streaming is generally preferred for RP to feel more interactive."
        ),
    },
}
