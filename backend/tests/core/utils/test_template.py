"""Tests for TemplateService"""

from unittest.mock import MagicMock

import pytest
from src.core.utils.template import TemplateContext, TemplateService


@pytest.fixture
def template_service() -> TemplateService:
    return TemplateService()


@pytest.fixture
def mock_context() -> TemplateContext:
    character = MagicMock()
    character.name = "Aria"
    character.description = "A brave warrior"
    character.personality = "Serious"
    character.scenario = "At the gate"

    persona = MagicMock()
    persona.name = "Player"
    persona.description = "A mysterious traveler"

    chat = MagicMock()
    chat.title = "Journey begins"

    return TemplateContext(character=character, persona=persona, chat=chat)


def test_render_basic(template_service: TemplateService, mock_context: TemplateContext) -> None:
    """Test basic variable replacement"""
    template = "Your name is {{char}} and you are talking to {{user}}."
    rendered = template_service.render(template, mock_context)
    assert rendered == "Your name is Aria and you are talking to Player."


def test_render_character_context(
    template_service: TemplateService, mock_context: TemplateContext
) -> None:
    """Test character-related variables"""
    template = "{{char}}'s description: {{description}}. Personality: {{personality}}."
    rendered = template_service.render(template, mock_context)
    assert "Aria's description: A brave warrior" in rendered
    assert "Personality: Serious" in rendered


def test_validate_template_valid(template_service: TemplateService) -> None:
    """Test validation of valid template"""
    is_valid, error = template_service.validate_template("Hello {{char}}")
    assert is_valid is True
    assert error is None


def test_validate_template_invalid(template_service: TemplateService) -> None:
    """Test validation of invalid template"""
    is_valid, error = template_service.validate_template("Hello {{char")
    assert is_valid is False
    assert error is not None


def test_render_invalid_syntax(
    template_service: TemplateService, mock_context: TemplateContext
) -> None:
    """Test rendering template with invalid syntax"""
    with pytest.raises(ValueError, match="Template syntax error"):
        _ = template_service.render("Hello {{char", mock_context)


def test_render_blocks_sandbox_escape(
    template_service: TemplateService, mock_context: TemplateContext
) -> None:
    """A template-injection payload (user-controlled content) must not reach unsafe
    internals — the sandbox blocks it and we surface a clean error instead of RCE."""
    payload = "{{ cycler.__init__.__globals__ }}"
    with pytest.raises(ValueError, match="unsafe operation"):
        _ = template_service.render(payload, mock_context)


def test_render_blocks_attribute_access_on_context(
    template_service: TemplateService, mock_context: TemplateContext
) -> None:
    """Accessing dunder attributes on injected variables is also blocked."""
    with pytest.raises(ValueError, match="unsafe operation"):
        _ = template_service.render("{{ char.__class__.__mro__ }}", mock_context)
