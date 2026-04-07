"""Centralized enums for the persistence layer to avoid circular imports"""

import enum


class MessageRole(str, enum.Enum):
    """Message role types"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProviderType(str, enum.Enum):
    """Supported provider types"""

    XAI = "xai"
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class Gender(str, enum.Enum):
    """Character gender options"""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non-binary"
    OTHERS = "others"


class InsertionPosition(str, enum.Enum):
    """Where activated lore entries are injected into the prompt"""

    BEFORE_CHARACTER = "before_character"
    AFTER_CHARACTER = "after_character"
    AT_DEPTH = "at_depth"
    BEFORE_EXAMPLES = "before_examples"


class SecondaryLogic(str, enum.Enum):
    """Logic for combining primary and secondary keyword matches"""

    AND_ANY = "and_any"
    AND_ALL = "and_all"
    NOT_ANY = "not_any"
    NOT_ALL = "not_all"
