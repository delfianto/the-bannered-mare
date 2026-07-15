"""Builders for synthetic SillyTavern preset data used across st_import tests."""

from typing import Any

from sqlalchemy.orm import Session
from src.core.persistence import UnitOfWork
from src.core.utils.upload import UploadedFile
from src.preset.repository import PresetRepository
from src.preset.service import PresetService
from src.profile.dependencies import get_profile_service
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_fragment.service import FragmentService
from src.prompt_template.repository import PromptTemplateRepository
from src.prompt_template.service import PromptTemplateService
from src.st_import.service import STImportService

# Identifiers that resolve to The Bannered Mare components.
MARKERS = (
    "charDescription",
    "charPersonality",
    "scenario",
    "personaDescription",
    "worldInfoBefore",
    "worldInfoAfter",
    "dialogueExamples",
    "chatHistory",
)


def st_prompt(
    identifier: str,
    *,
    name: str | None = None,
    content: str = "",
    role: str = "system",
    system_prompt: bool = False,
    marker: bool = False,
    injection_position: int = 0,
    injection_depth: int | None = 4,
    enabled: bool | None = True,
    **extra: Any,
) -> dict[str, Any]:
    """A `prompts[]` entry (custom prompt by default)."""
    entry: dict[str, Any] = {
        "identifier": identifier,
        "name": name if name is not None else identifier,
        "role": role,
        "content": content,
        "system_prompt": system_prompt,
        "marker": marker,
        "injection_position": injection_position,
        "injection_depth": injection_depth,
        "forbid_overrides": False,
        "enabled": enabled,
    }
    entry.update(extra)
    return entry


def st_marker(identifier: str) -> dict[str, Any]:
    """A marker `prompts[]` entry (no content)."""
    return {"identifier": identifier, "name": identifier, "system_prompt": True, "marker": True}


def st_order(items: list[Any], character_id: int = 100001) -> dict[str, Any]:
    """A prompt_order entry. `items` are identifiers or (identifier, enabled) tuples."""
    order: list[dict[str, Any]] = []
    for it in items:
        ident, enabled = it if isinstance(it, tuple) else (it, True)
        order.append({"identifier": ident, "enabled": enabled})
    return {"character_id": character_id, "order": order}


def preset_dict(
    prompts: list[dict[str, Any]],
    order_items: list[Any],
    *,
    character_id: int = 100001,
    samplers: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a full ST chat-completion preset dict."""
    data: dict[str, Any] = {
        "prompts": prompts,
        "prompt_order": [st_order(order_items, character_id)],
    }
    if samplers:
        data.update(samplers)
    if extra:
        data.update(extra)
    return data


def make_upload(data: str | bytes, filename: str = "preset.json") -> UploadedFile:
    """Wrap bytes/str as an UploadedFile for direct service tests."""
    payload = data.encode("utf-8") if isinstance(data, str) else data
    return UploadedFile(payload, filename)


def make_service(db: Session) -> STImportService:
    """Build an STImportService over domain services sharing the test session."""
    return STImportService(
        template_service=PromptTemplateService(PromptTemplateRepository(db)),
        fragment_service=FragmentService(FragmentRepository(db), TemplateFragmentRepository(db)),
        preset_service=PresetService(PresetRepository(db)),
        profile_service=get_profile_service(db),
        uow=UnitOfWork(db),
    )
