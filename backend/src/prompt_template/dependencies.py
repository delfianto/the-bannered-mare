"""Dependency injection factories for prompt template module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.prompt_fragment.repository import FragmentRepository
from src.prompt_template.repository import PromptTemplateRepository
from src.prompt_template.service import PromptTemplateService
from src.templating.dependencies import TemplateServiceDep


def get_prompt_template_repository(db: DbSession) -> PromptTemplateRepository:
    """Factory for PromptTemplateRepository with DB injected"""
    return PromptTemplateRepository(db)


def get_prompt_template_service(
    template_repo: Annotated[PromptTemplateRepository, Depends(get_prompt_template_repository)],
    db: DbSession,
    template_service: TemplateServiceDep,
) -> PromptTemplateService:
    """Factory for PromptTemplateService with repository injected"""
    return PromptTemplateService(template_repo, FragmentRepository(db), template_service)


PromptTemplateServiceDep = Annotated[PromptTemplateService, Depends(get_prompt_template_service)]
PromptTemplateRepositoryDep = Annotated[
    PromptTemplateRepository, Depends(get_prompt_template_repository)
]
