"""Dependency injection for the SillyTavern import service."""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession, UnitOfWork
from src.preset.dependencies import get_preset_service
from src.preset.service import PresetService
from src.profile.dependencies import get_profile_service
from src.profile.service import ProfileService
from src.prompt_fragment.dependencies import get_fragment_service
from src.prompt_fragment.service import FragmentService
from src.prompt_template.dependencies import get_prompt_template_service
from src.prompt_template.service import PromptTemplateService
from src.st_import.service import STImportService


def get_st_import_service(
    db: DbSession,
    template_service: Annotated[PromptTemplateService, Depends(get_prompt_template_service)],
    fragment_service: Annotated[FragmentService, Depends(get_fragment_service)],
    preset_service: Annotated[PresetService, Depends(get_preset_service)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> STImportService:
    """Build STImportService over the domain services (all bound to one session → atomic import)."""
    return STImportService(
        template_service=template_service,
        fragment_service=fragment_service,
        preset_service=preset_service,
        profile_service=profile_service,
        uow=UnitOfWork(db),
    )


STImportServiceDep = Annotated[STImportService, Depends(get_st_import_service)]
