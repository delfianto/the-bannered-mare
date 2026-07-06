"""Tests for TokenizerService"""

from src.core.utils.tokenizer import TokenizerService


def test_count_tokens() -> None:
    """Test counting tokens in text"""
    service = TokenizerService()
    text = "Hello world!"
    # "Hello world!" is typically 3 tokens in cl100k_base
    count = service.count_tokens(text)
    assert count > 0


def test_count_messages() -> None:
    """Test counting tokens in message array"""
    service = TokenizerService()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    count = service.count_messages(messages)
    assert count > service.count_tokens("You are a helpful assistant.") + service.count_tokens(
        "Hello!"
    )


def test_calculate_budget() -> None:
    """Test budget calculation"""
    service = TokenizerService()
    budget = service.calculate_budget(
        max_context_tokens=1000, max_response_tokens=200, safety_margin=0.9
    )
    # (1000 * 0.9) - 200 = 700
    assert budget == 700


def test_calculate_budget_zero() -> None:
    """Test budget calculation doesn't go below zero"""
    service = TokenizerService()
    budget = service.calculate_budget(max_context_tokens=100, max_response_tokens=200)
    assert budget == 0
