"""Dependency injection factories for prompt template module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession, UnitOfWork
from src.prompt_fragment.dependencies import get_fragment_service
from src.prompt_fragment.service import FragmentService
from src.prompt_template.repository import PromptTemplateRepository
from src.prompt_template.service import PromptTemplateService
from src.templating.dependencies import TemplateServiceDep


def get_prompt_template_repository(db: DbSession) -> PromptTemplateRepository:
    """Factory for PromptTemplateRepository with DB injected"""
    return PromptTemplateRepository(db)


def get_prompt_template_service(
    template_repo: Annotated[PromptTemplateRepository, Depends(get_prompt_template_repository)],
    fragment_service: Annotated[FragmentService, Depends(get_fragment_service)],
    db: DbSession,
    template_service: TemplateServiceDep,
) -> PromptTemplateService:
    """Factory for PromptTemplateService with its fragment-cleanup seam injected"""
    return PromptTemplateService(
        template_repo, fragment_service, template_service, uow=UnitOfWork(db)
    )


PromptTemplateServiceDep = Annotated[PromptTemplateService, Depends(get_prompt_template_service)]
PromptTemplateRepositoryDep = Annotated[
    PromptTemplateRepository, Depends(get_prompt_template_repository)
]
