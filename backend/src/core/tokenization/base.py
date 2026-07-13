"""Tokenizer interface for per-model-family token counting.

The abstraction produces the *pre-send estimate* used for prompt budgeting and
history truncation; the provider's reported usage stays the authoritative
post-hoc source. Concrete backends live in ``backends.py``; families are resolved
to a backend by ``registry.get_tokenizer``.
"""

from abc import ABC, abstractmethod

# Message-array framing overhead (base + per-message + assistant priming), kept
# as a small OpenAI-style constant. It's a minor estimate term — not worth
# rendering each family's real chat template.
_ARRAY_OVERHEAD = 3
_REPLY_PRIMING = 3


class Tokenizer(ABC):
    """Counts tokens for one model family. ``name`` identifies the backend."""

    name: str

    @abstractmethod
    def count(self, text: str) -> int:
        """Token count for a plain string (no chat framing)."""

    def count_messages(self, messages: list[dict[str, str]], *, per_message: int = 3) -> int:
        """Approximate token count for an OpenAI-style message array."""
        tokens = _ARRAY_OVERHEAD
        for message in messages:
            tokens += per_message + self.count(message.get("content", ""))
        return tokens + _REPLY_PRIMING
