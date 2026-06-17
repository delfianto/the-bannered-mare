"""Tests for ProfileService"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.core.persistence import Preset, PromptTemplate
from src.model.repository import ModelRepository
from src.persona.repository import PersonaRepository
from src.preset.repository import PresetRepository
from src.profile.repository import ProfileRepository
from src.profile.service import ProfileService
from src.prompt_template.repository import PromptTemplateRepository


def _service(db: Session) -> ProfileService:
    return ProfileService(
        profile_repo=ProfileRepository(db),
        template_repo=PromptTemplateRepository(db),
        preset_repo=PresetRepository(db),
        persona_repo=PersonaRepository(db),
        model_repo=ModelRepository(db),
    )


class TestProfileService:
    def test_create_minimal(self, db: Session) -> None:
        profile = _service(db).create(name="Loadout A")

        assert profile.name == "Loadout A"
        assert profile.source == "manual"
        assert profile.is_default is False
        assert profile.prompt_template_id is None

    def test_create_with_valid_refs(self, db: Session) -> None:
        tmpl = PromptTemplate(name="T", system_template="x")
        preset = Preset(name="P", parameters={})
        db.add_all([tmpl, preset])
        db.commit()
        db.refresh(tmpl)
        db.refresh(preset)

        profile = _service(db).create(
            name="Loadout B", prompt_template_id=tmpl.id, preset_id=preset.id
        )

        assert profile.prompt_template_id == tmpl.id
        assert profile.preset_id == preset.id

    def test_create_with_invalid_template_raises_404(self, db: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _service(db).create(name="Bad", prompt_template_id="nonexistent")
        assert exc_info.value.status_code == 404
        assert "Prompt template" in exc_info.value.detail

    def test_create_with_invalid_model_raises_404(self, db: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _service(db).create(name="Bad", model_id="nonexistent")
        assert exc_info.value.status_code == 404
        assert "Model" in exc_info.value.detail

    def test_default_is_exclusive(self, db: Session) -> None:
        service = _service(db)
        p1 = service.create(name="D1", is_default=True)
        p2 = service.create(name="D2", is_default=True)

        db.refresh(p1)
        assert p1.is_default is False
        assert p2.is_default is True

    def test_update(self, db: Session) -> None:
        service = _service(db)
        profile = service.create(name="Original")
        updated = service.update(profile.id, name="Renamed")

        assert updated.name == "Renamed"

    def test_update_with_invalid_ref_raises_404(self, db: Session) -> None:
        service = _service(db)
        profile = service.create(name="Loadout")
        with pytest.raises(HTTPException) as exc_info:
            service.update(profile.id, preset_id="nonexistent")
        assert exc_info.value.status_code == 404

    def test_set_default(self, db: Session) -> None:
        service = _service(db)
        p1 = service.create(name="S1", is_default=True)
        p2 = service.create(name="S2")

        service.set_default(p2.id)
        db.refresh(p1)
        db.refresh(p2)

        assert p1.is_default is False
        assert p2.is_default is True

    def test_delete(self, db: Session) -> None:
        service = _service(db)
        profile = service.create(name="ToDelete")
        service.delete(profile.id)

        with pytest.raises(HTTPException) as exc_info:
            service.get_by_id(profile.id)
        assert exc_info.value.status_code == 404

    def test_get_by_id_not_found(self, db: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _service(db).get_by_id("nonexistent")
        assert exc_info.value.status_code == 404
