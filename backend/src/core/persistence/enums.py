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
    LMSTUDIO = "lmstudio"
    OPENCODE = "opencode"
    OPENCODE_GO = "opencode_go"
    CUSTOM = "custom"


class ReasoningMode(enum.StrEnum):
    """Whether a model family reasons, and whether that reasoning can be disabled.

    A first-class capability (stored per family) so behavior is driven by declared
    metadata rather than by sniffing which sampler parameters happen to be present.
    """

    NONE = "none"  # Does not reason — no reasoning control applies.
    OPTIONAL = "optional"  # Reasons, but reasoning can be turned off (suppress on aux calls).
    ALWAYS_ON = "always_on"  # Reasons and cannot be disabled — suppression is futile, skip it.


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
