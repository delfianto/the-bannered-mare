"""Dependency injection for the SillyTavern import service."""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.preset.repository import PresetRepository
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_template.repository import PromptTemplateRepository
from src.st_import.service import STImportService


def get_st_import_service(db: DbSession) -> STImportService:
    """Build STImportService with all four repositories bound to one session (atomic import)."""
    return STImportService(
        template_repo=PromptTemplateRepository(db),
        fragment_repo=FragmentRepository(db),
        template_fragment_repo=TemplateFragmentRepository(db),
        preset_repo=PresetRepository(db),
    )


STImportServiceDep = Annotated[STImportService, Depends(get_st_import_service)]
