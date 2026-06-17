"""Application service: import a SillyTavern preset into Candlekeep entities.

Persists via repositories directly (not the domain services) so the whole import
is one transaction, the ``at_depth`` depth can be set on join rows, and ST-specific
macros are not rejected by the services' Jinja2 validation.
"""

from collections.abc import Callable

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError

from src.core.persistence import (
    Preset,
    Profile,
    PromptFragment,
    PromptTemplate,
    TemplateFragment,
    gen_id,
)
from src.preset.repository import PresetRepository
from src.profile.repository import ProfileRepository
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_template.repository import PromptTemplateRepository
from src.st_import.errors import STImportError
from src.st_import.mapper import ImportPlan, build_import_plan
from src.st_import.parser import parse_st_preset
from src.st_import.schemas import STImportResult

_MAX_NAME_LEN = 100
_FALLBACK_NAME = "Imported ST Preset"


class STImportService:
    """Imports SillyTavern chat-completion presets atomically."""

    def __init__(
        self,
        template_repo: PromptTemplateRepository,
        fragment_repo: FragmentRepository,
        template_fragment_repo: TemplateFragmentRepository,
        preset_repo: PresetRepository,
        profile_repo: ProfileRepository,
    ):
        self.template_repo = template_repo
        self.fragment_repo = fragment_repo
        self.template_fragment_repo = template_fragment_repo
        self.preset_repo = preset_repo
        self.profile_repo = profile_repo

    async def import_preset(self, file: UploadFile) -> STImportResult:
        """Read, validate, and import a .json ST preset. Raises HTTP 400 on bad input."""
        filename = file.filename or ""
        if not filename.lower().endswith(".json"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Upload a .json SillyTavern preset.",
            )

        raw = await file.read()
        try:
            preset = parse_st_preset(raw)
        except STImportError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        plan = build_import_plan(preset, _derive_base_name(filename))

        try:
            return self._persist(plan, filename or None)
        except IntegrityError as e:
            self.template_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import failed due to a database conflict.",
            ) from e
        except Exception:
            # Never leave a half-built import in the session.
            self.template_repo.rollback()
            raise

    def _persist(self, plan: ImportPlan, source_filename: str | None) -> STImportResult:
        """Create template -> fragments -> join rows -> optional preset -> profile; commit once."""
        template = self.template_repo.create(
            PromptTemplate(
                id=gen_id(),
                name=self._unique_name(plan.template.name, self.template_repo.find_by_name),
                description=plan.template.description,
                is_default=False,
                system_template=plan.template.system_template,
                component_order=plan.template.component_order,
                components_enabled=plan.template.components_enabled,
            )
        )

        used_fragment_names: set[str] = set()
        fragment_ids: list[str] = []
        for spec in plan.fragments:
            frag_name = self._unique_name(
                spec.name, self.fragment_repo.find_by_name, used_fragment_names
            )
            used_fragment_names.add(frag_name)
            fragment = self.fragment_repo.create(
                PromptFragment(
                    id=gen_id(),
                    name=frag_name,
                    description=spec.description,
                    fragment_type=spec.fragment_type,
                    content=spec.content,
                    is_global=False,
                )
            )
            _ = self.template_fragment_repo.create(
                TemplateFragment(
                    id=gen_id(),
                    template_id=template.id,
                    fragment_id=fragment.id,
                    position=spec.position,
                    ordinal=spec.ordinal,
                    depth=spec.depth,
                )
            )
            fragment_ids.append(fragment.id)

        preset_id: str | None = None
        preset_name: str | None = None
        if plan.preset is not None:
            created_preset = self.preset_repo.create(
                Preset(
                    id=gen_id(),
                    name=self._unique_name(plan.preset.name, self.preset_repo.find_by_name),
                    description=plan.preset.description,
                    parameters=plan.preset.parameters,
                    is_default=False,
                )
            )
            preset_id = created_preset.id
            preset_name = created_preset.name

        created_profile = self.profile_repo.create(
            Profile(
                id=gen_id(),
                name=self._unique_name(plan.profile.name, self.profile_repo.find_by_name),
                description=plan.profile.description,
                prompt_template_id=template.id,
                preset_id=preset_id,
                source="sillytavern",
                source_filename=source_filename,
                is_default=False,
            )
        )

        self.template_repo.commit()

        return STImportResult(
            template_id=template.id,
            template_name=template.name,
            fragment_ids=fragment_ids,
            preset_id=preset_id,
            preset_name=preset_name,
            profile_id=created_profile.id,
            profile_name=created_profile.name,
            warnings=plan.warnings,
        )

    def _unique_name(
        self,
        base: str,
        find_by_name: Callable[[str], object | None],
        also_used: set[str] | None = None,
    ) -> str:
        """Return a name unique against the DB and this import, auto-suffixing ' (n)'."""
        also_used = also_used or set()
        base = (base or _FALLBACK_NAME).strip()[:_MAX_NAME_LEN] or _FALLBACK_NAME

        def taken(name: str) -> bool:
            return name in also_used or find_by_name(name) is not None

        if not taken(base):
            return base

        n = 2
        while True:
            suffix = f" ({n})"
            candidate = base[: _MAX_NAME_LEN - len(suffix)] + suffix
            if not taken(candidate):
                return candidate
            n += 1


def _derive_base_name(filename: str) -> str:
    """ST presets have no name field; use the uploaded filename stem."""
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if base.lower().endswith(".json"):
        base = base[:-5]
    return base.strip() or _FALLBACK_NAME
