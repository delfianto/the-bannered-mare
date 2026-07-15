"""Dependency injection factories for prompt fragment module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession, UnitOfWork
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_fragment.service import FragmentService
from src.templating.dependencies import TemplateServiceDep


def get_fragment_repository(db: DbSession) -> FragmentRepository:
    """Factory for FragmentRepository with DB injected"""
    return FragmentRepository(db)


def get_template_fragment_repository(db: DbSession) -> TemplateFragmentRepository:
    """Factory for TemplateFragmentRepository with DB injected"""
    return TemplateFragmentRepository(db)


def get_fragment_service(
    fragment_repo: Annotated[FragmentRepository, Depends(get_fragment_repository)],
    template_fragment_repo: Annotated[
        TemplateFragmentRepository, Depends(get_template_fragment_repository)
    ],
    template_service: TemplateServiceDep,
) -> FragmentService:
    """Factory for FragmentService with repositories injected"""
    return FragmentService(
        fragment_repo, template_fragment_repo, template_service, uow=UnitOfWork(fragment_repo.db)
    )


FragmentServiceDep = Annotated[FragmentService, Depends(get_fragment_service)]
FragmentRepositoryDep = Annotated[FragmentRepository, Depends(get_fragment_repository)]
TemplateFragmentRepositoryDep = Annotated[
    TemplateFragmentRepository, Depends(get_template_fragment_repository)
]
