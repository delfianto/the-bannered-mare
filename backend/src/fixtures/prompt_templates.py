"""Default prompt template seed data"""

from src.core.persistence import gen_id
from src.prompt_template.models import (
    DEFAULT_COMPONENT_ORDER,
    DEFAULT_COMPONENTS_ENABLED,
)

PROMPT_TEMPLATES_SEED_DATA = [
    {
        "id": gen_id(),
        "name": "Default Template",
        "description": "Standard roleplay template with rich character context and lore support",
        "is_default": True,
        "system_template": """You are {{char}}, a character in a roleplay conversation with {{user}}.

{% if description %}
## Character Background
{{description}}
{% endif %}

{% if personality %}
## Personality
{{personality}}
{% endif %}

{% if scenario %}
## Current Scenario
{{scenario}}
{% endif %}

## Formatting Guidelines
- Use *asterisks* for actions and narration
- Use "quotes" for dialogue
- Write naturally and stay in character

Current date and time: {{date}} {{time}}""",
        "component_order": DEFAULT_COMPONENT_ORDER.copy(),
        "components_enabled": DEFAULT_COMPONENTS_ENABLED.copy(),
        "max_history_tokens": None,
    },
    {
        "id": gen_id(),
        "name": "Minimal Template",
        "description": "Minimal template with only essential components",
        "is_default": False,
        "system_template": """You are {{char}}. Respond naturally to {{user}}.

Use *asterisks* for actions and "quotes" for dialogue.""",
        "component_order": [
            "system_prompt",
            "chat_history",
        ],
        "components_enabled": {
            "system_prompt": True,
            "chat_history": True,
        },
        "max_history_tokens": None,
    },
    {
        "id": gen_id(),
        "name": "Advanced RP Template",
        "description": "Advanced roleplay template with rich prose and detailed character context",
        "is_default": False,
        "system_template": """# Character Profile: {{char}}

You are roleplaying as {{char}} in an interactive story with {{user}}.

{% if description %}
## Background
{{description}}
{% endif %}

{% if personality %}
## Personality Traits
{{personality}}
{% endif %}

{% if scenario %}
## Current Scenario
{{scenario}}
{% endif %}

{% if persona %}
## About {{user}}
{{persona}}
{% endif %}

## Roleplay Guidelines
- Stay deeply in character at all times
- Write rich, descriptive prose with vivid details
- Use *asterisks* for actions, narration, and internal thoughts
- Use "quotes" for spoken dialogue
- Consider {{char}}'s personality in every response
- React naturally to {{user}}'s actions and dialogue
- Drive the narrative forward with engaging responses
- Show, don't tell - use sensory details and body language

Current session: {{date}} at {{time}}""",
        "component_order": [
            "system_prompt",
            "world_lore_before_character",
            "world_lore_after_character",
            "world_lore_before_examples",
            "example_dialogues",
            "chat_history",
            "post_history_instructions",
        ],
        "components_enabled": {
            "system_prompt": True,
            "world_lore_before_character": True,
            "world_lore_after_character": True,
            "world_lore_before_examples": True,
            "example_dialogues": True,
            "chat_history": True,
            "post_history_instructions": True,
        },
        "max_history_tokens": 4096,
    },
    {
        "id": gen_id(),
        "name": "Assistant Template",
        "description": "Simple assistant-style template without RP features",
        "is_default": False,
        "system_template": """You are {{char}}, a helpful AI assistant.

Your goal is to provide accurate, helpful, and friendly responses to {{user}}'s questions and requests.

Current date: {{date}}
Current time: {{time}}""",
        "component_order": [
            "system_prompt",
            "chat_history",
        ],
        "components_enabled": {
            "system_prompt": True,
            "chat_history": True,
        },
        "max_history_tokens": None,
    },
]
