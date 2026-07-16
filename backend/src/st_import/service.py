"""Application service: import a SillyTavern preset into The Bannered Mare entities.

Persists through each target slice's published *import seam* (``create_imported`` /
``attach_imported``) rather than its repositories. Those seams are
flush-only — they participate in this service's single unit of work, so the whole
import commits (or rolls back) atomically — and they skip the domain services'
Jinja2 validation, which would otherwise reject ST-specific macros. The join-row
``at_depth`` depth and the profile's import provenance are set through the seams too.
"""

from collections.abc import Callable

from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError, ValidationError
from src.core.persistence import UnitOfWork
from src.core.utils.upload import UploadedFile
from src.preset.service import PresetService
from src.profile.service import ProfileService
from src.prompt_fragment.service import FragmentService
from src.prompt_template.service import PromptTemplateService
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
        template_service: PromptTemplateService,
        fragment_service: FragmentService,
        preset_service: PresetService,
        profile_service: ProfileService,
        uow: UnitOfWork,
    ):
        self.template_service = template_service
        self.fragment_service = fragment_service
        self.preset_service = preset_service
        self.profile_service = profile_service
        # This application service owns the transaction boundary for the whole
        # cross-slice import: the slice import seams flush, and this uow commits once.
        self.uow = uow

    async def import_preset(self, upload: UploadedFile) -> STImportResult:
        """Validate and import a .json ST preset. Raises HTTP 400 on bad input."""
        filename = upload.filename
        if not filename.lower().endswith(".json"):
            raise ValidationError("Unsupported file format. Upload a .json SillyTavern preset.")

        raw = upload.data
        try:
            preset = parse_st_preset(raw)
        except STImportError as e:
            raise ValidationError(str(e)) from e

        plan = build_import_plan(preset, _derive_base_name(filename))

        try:
            return self._persist(plan, filename or None)
        except IntegrityError as e:
            self.uow.rollback()
            raise ConflictError("Import failed due to a database conflict.") from e
        except Exception:
            # Never leave a half-built import in the session.
            self.uow.rollback()
            raise

    def _persist(self, plan: ImportPlan, source_filename: str | None) -> STImportResult:
        """Create template -> fragments -> join rows -> optional preset -> profile; commit once."""
        template = self.template_service.create_imported(
            name=self._unique_name(plan.template.name, self.template_service.find_by_name),
            system_template=plan.template.system_template,
            description=plan.template.description,
            component_order=plan.template.component_order,
            components_enabled=plan.template.components_enabled,
        )

        used_fragment_names: set[str] = set()
        fragment_ids: list[str] = []
        for spec in plan.fragments:
            # Reimporting the same (or another preset sharing boilerplate) should
            # reuse the existing fragment rather than pile up "(2)", "(3)", ...
            # duplicates that only differ by name.
            fragment = self.fragment_service.find_by_content(spec.content)
            if fragment is None:
                frag_name = self._unique_name(
                    spec.name, self.fragment_service.find_by_name, used_fragment_names
                )
                used_fragment_names.add(frag_name)
                fragment = self.fragment_service.create_imported(
                    name=frag_name,
                    content=spec.content,
                    fragment_type=spec.fragment_type,
                    description=spec.description,
                )
            _ = self.fragment_service.attach_imported(
                template_id=template.id,
                fragment_id=fragment.id,
                position=spec.position,
                ordinal=spec.ordinal,
                depth=spec.depth,
            )
            fragment_ids.append(fragment.id)

        preset_id: str | None = None
        preset_name: str | None = None
        if plan.preset is not None:
            created_preset = self.preset_service.create_imported(
                name=self._unique_name(plan.preset.name, self.preset_service.find_by_name),
                description=plan.preset.description,
                parameters=plan.preset.parameters,
            )
            preset_id = created_preset.id
            preset_name = created_preset.name

        created_profile = self.profile_service.create_imported(
            name=self._unique_name(plan.profile.name, self.profile_service.find_by_name),
            description=plan.profile.description,
            prompt_template_id=template.id,
            preset_id=preset_id,
            source="sillytavern",
            source_filename=source_filename,
        )

        self.uow.commit()

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
