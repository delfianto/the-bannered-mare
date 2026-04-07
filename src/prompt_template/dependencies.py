"""Dependency injection factories for prompt template module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.prompt_template.repository import PromptTemplateRepository
from src.prompt_template.service import PromptTemplateService


def get_prompt_template_repository(db: DbSession) -> PromptTemplateRepository:
    """Factory for PromptTemplateRepository with DB injected"""
    return PromptTemplateRepository(db)


def get_prompt_template_service(
    template_repo: Annotated[PromptTemplateRepository, Depends(get_prompt_template_repository)],
) -> PromptTemplateService:
    """Factory for PromptTemplateService with repository injected"""
    return PromptTemplateService(template_repo)


PromptTemplateServiceDep = Annotated[PromptTemplateService, Depends(get_prompt_template_service)]
PromptTemplateRepositoryDep = Annotated[
    PromptTemplateRepository, Depends(get_prompt_template_repository)
]
