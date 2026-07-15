"""Dependency injection factory for the templating service.

Lives beside :class:`TemplateService` rather than in a domain module because the
renderer is a stateless, cross-cutting service that prompt_template, chat_session,
and prompt_fragment all consume — a shared home keeps those domains from pointing
at one another just to reach it.
"""

from typing import Annotated

from fastapi import Depends

from src.templating import TemplateService


def get_template_service() -> TemplateService:
    """Factory for the stateless, sandboxed-Jinja TemplateService."""
    return TemplateService()


TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
