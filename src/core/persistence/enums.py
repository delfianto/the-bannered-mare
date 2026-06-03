"""Centralized enums for the persistence layer to avoid circular imports"""

import enum


class MessageRole(enum.StrEnum):
    """Message role types"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ProviderType(enum.StrEnum):
    """Supported provider types"""

    XAI = "xai"
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class Gender(enum.StrEnum):
    """Character gender options"""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non-binary"
    OTHERS = "others"


class InsertionPosition(enum.StrEnum):
    """Where activated lore entries are injected into the prompt"""

    BEFORE_CHARACTER = "before_character"
    AFTER_CHARACTER = "after_character"
    AT_DEPTH = "at_depth"
    BEFORE_EXAMPLES = "before_examples"


class SecondaryLogic(enum.StrEnum):
    """Logic for combining primary and secondary keyword matches"""

    AND_ANY = "and_any"
    AND_ALL = "and_all"
    NOT_ANY = "not_any"
    NOT_ALL = "not_all"
