"""Token counting service using tiktoken"""

import tiktoken


class TokenizerService:
    """Fast token counting with tiktoken (90-95% accurate for all providers)"""

    def __init__(self, model_family: str = "gpt-4"):
        """Initialize tokenizer for specific model family

        Args:
            model_family: Model identifier (e.g., "gpt-4", "claude-3.5", "gemini")
        """
        self.model_family = model_family
        self.encoder = self._get_encoder()

    def _get_encoder(self) -> tiktoken.Encoding:
        """Get appropriate tiktoken encoding for model family"""
        # OpenAI models: use model-specific encoding
        if "gpt-4" in self.model_family.lower():
            return tiktoken.encoding_for_model("gpt-4")
        elif "gpt-3.5" in self.model_family.lower():
            return tiktoken.encoding_for_model("gpt-3.5-turbo")

        # All other providers: use cl100k_base (90-95% accurate)
        # This includes Claude, Gemini, Llama, Mistral, etc.
        return tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text string

        Args:
            text: Text to count tokens for

        Returns:
            Token count (accurate within 90-95% for non-OpenAI models)
        """
        return len(self.encoder.encode(text))

    def count_messages(self, messages: list[dict[str, str]]) -> int:
        """Count tokens in OpenAI-format message array

        Includes message overhead tokens (role, content formatting, etc.)

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Total token count including message overhead
        """
        tokens = 3  # Base overhead for message array

        for message in messages:
            tokens += 3  # Per-message overhead (role + content markers)
            tokens += self.count_tokens(message["content"])

            # Additional overhead for messages with names
            if message.get("name"):
                tokens += self.count_tokens(message["name"])
                tokens -= 1  # Name adjustment

        tokens += 3  # Assistant reply priming tokens

        return tokens

    def calculate_budget(
        self,
        max_context_tokens: int,
        max_response_tokens: int,
        safety_margin: float = 0.9,
    ) -> int:
        """Calculate available token budget for chat history

        Args:
            max_context_tokens: Model's maximum context window
            max_response_tokens: Reserved tokens for response generation
            safety_margin: Safety factor to avoid hitting limits (default 0.9 = 90%)

        Returns:
            Available tokens for chat history after applying safety margin
        """
        # Apply 90% safety margin to max context
        safe_context = int(max_context_tokens * safety_margin)

        # Reserve tokens for response
        available = safe_context - max_response_tokens

        return max(0, available)
