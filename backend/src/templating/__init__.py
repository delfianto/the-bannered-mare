"""Jinja2 prompt/greeting template rendering.

Its own module rather than ``core.utils`` because the render context is
domain-aware (character / persona / chat) — a shared-kernel utility must not
reference vertical-slice models. Consumed by prompt_template, chat_session, and
prompt_fragment; the model imports are ``TYPE_CHECKING``-only, so this stays a
runtime-leaf with no import cycles.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from jinja2 import TemplateSyntaxError
from jinja2.exceptions import SecurityError
from jinja2.sandbox import SandboxedEnvironment

if TYPE_CHECKING:
    from src.character.models import Character
    from src.chat_session.models import Chat
    from src.persona.models import Persona

__all__ = ["TemplateContext", "TemplateService"]


class TemplateContext:
    """Context data for template rendering"""

    def __init__(
        self,
        character: Character,
        persona: Persona | None,
        chat: Chat,
    ):
        self.character = character
        self.persona = persona
        self.chat = chat


class TemplateService:
    """Jinja2 template rendering for prompts"""

    def __init__(self):
        """Initialize the Jinja2 environment.

        A SANDBOXED environment is mandatory: template strings are user-controlled
        (character.system_prompt, prompt-fragment content, imported cards), so a
        plain Environment would be a server-side template injection → RCE vector
        (e.g. ``{{ cycler.__init__.__globals__ }}``). The sandbox blocks access to
        unsafe attributes/callables at render time.
        """
        self.env = SandboxedEnvironment(
            autoescape=False,  # Don't escape HTML entities
            trim_blocks=True,  # Remove newlines after block tags
            lstrip_blocks=True,  # Remove leading whitespace from blocks
        )

    def render(self, template_string: str, context: TemplateContext) -> str:
        """Render Jinja2 template with context data

        Args:
            template_string: Jinja2 template string
            context: Template context with character, persona, chat data

        Returns:
            Rendered template string

        Raises:
            TemplateSyntaxError: If template has syntax errors
        """
        try:
            template = self.env.from_string(template_string)
        except TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error: {e}") from e

        # Build template variables
        variables = self._build_variables(context)

        try:
            return template.render(**variables)
        except SecurityError as e:
            # A sandbox violation means the template tried to reach an unsafe
            # attribute/callable (injection attempt) — refuse rather than execute.
            raise ValueError(f"Template rendering blocked (unsafe operation): {e}") from e

    def _build_variables(self, context: TemplateContext) -> dict[str, str]:
        """Build template variables from context

        Supported variables:
        - {{char}} - Character name
        - {{user}} - Persona name (or "User" if no persona)
        - {{description}} - Character description
        - {{personality}} - Character personality
        - {{scenario}} - Current scenario
        - {{persona}} - User/persona description
        - {{time}} - Current time (HH:MM)
        - {{date}} - Current date (YYYY-MM-DD)
        - {{chat_title}} - Chat title

        Args:
            context: Template context

        Returns:
            Dictionary of template variables
        """
        now = datetime.now()

        return {
            # Character variables
            "char": context.character.name,
            "description": context.character.description or "",
            "personality": context.character.personality or "",
            "scenario": context.character.scenario or "",
            # Persona variables
            "user": context.persona.name if context.persona else "User",
            "persona": (context.persona.description or "") if context.persona else "",
            # Temporal variables
            "time": now.strftime("%H:%M"),
            "date": now.strftime("%Y-%m-%d"),
            # Chat metadata
            "chat_title": context.chat.title or "Untitled Chat",
        }

    def validate_template(self, template_string: str) -> tuple[bool, str | None]:
        """Validate Jinja2 template syntax

        Args:
            template_string: Template to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            _ = self.env.from_string(template_string)
            return True, None
        except TemplateSyntaxError as e:
            return False, str(e)
