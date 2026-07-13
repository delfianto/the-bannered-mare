"""Concrete tokenizer backends: tiktoken (OpenAI), HuggingFace (open-weight), heuristic."""

import math

import tiktoken

from src.core.tokenization.base import Tokenizer


class TiktokenTokenizer(Tokenizer):
    """Exact, offline OpenAI tokenizer. Also a decent general proxy for others."""

    def __init__(self, encoding: str):
        self.name = f"tiktoken:{encoding}"
        self._enc = tiktoken.get_encoding(encoding)

    def count(self, text: str) -> int:
        if not text:
            return 0
        # disallowed_special=() so user/RP content containing "<|...|>" is encoded
        # as ordinary text instead of raising.
        return len(self._enc.encode(text, disallowed_special=()))


class HuggingFaceTokenizer(Tokenizer):
    """Exact tokenizer for an open-weight family, loaded from a HF repo's
    ``tokenizer.json`` (downloaded once, then cached on disk). Construction may
    raise (offline / gated / missing repo); the registry catches and falls back.
    """

    def __init__(self, repo_id: str):
        from tokenizers import Tokenizer as HFTokenizer  # local import: heavy dep

        self.name = f"hf:{repo_id}"
        self._tok = HFTokenizer.from_pretrained(repo_id)

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._tok.encode(text, add_special_tokens=False).ids)


class HeuristicTokenizer(Tokenizer):
    """Offline chars/token estimate for families with no public tokenizer
    (Claude, Grok, …). Never fails; approximate only."""

    def __init__(self, chars_per_token: float = 3.8):
        self.name = f"heuristic:{chars_per_token}"
        self._ratio = chars_per_token

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / self._ratio))
