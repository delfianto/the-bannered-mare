"""Builders for synthetic SillyTavern preset data used across st_import tests."""

import io
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.preset.repository import PresetRepository
from src.profile.repository import ProfileRepository
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_template.repository import PromptTemplateRepository
from src.st_import.service import STImportService
from starlette.datastructures import Headers

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


def make_upload(data: str | bytes, filename: str = "preset.json") -> UploadFile:
    """Wrap bytes/str as an UploadFile for service/router tests."""
    payload = data.encode("utf-8") if isinstance(data, str) else data
    return UploadFile(
        filename=filename,
        file=io.BytesIO(payload),
        headers=Headers({"content-type": "application/json"}),
    )


def make_service(db: Session) -> STImportService:
    """Build an STImportService whose repos all share the test session."""
    return STImportService(
        template_repo=PromptTemplateRepository(db),
        fragment_repo=FragmentRepository(db),
        template_fragment_repo=TemplateFragmentRepository(db),
        preset_repo=PresetRepository(db),
        profile_repo=ProfileRepository(db),
    )
