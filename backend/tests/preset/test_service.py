"""Tests for PresetService"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.preset.repository import PresetRepository
from src.preset.service import PresetService


class TestPresetService:
    def test_create_preset(self, db: Session) -> None:
        repo = PresetRepository(db)
        service = PresetService(repo)

        preset = service.create(
            name="Creative",
            description="High temperature for creative writing",
            parameters={"temperature": 1.5, "top_p": 0.9},
        )

        assert preset.name == "Creative"
        assert preset.parameters["temperature"] == 1.5
        assert preset.is_default is False

    def test_create_preset_as_default(self, db: Session) -> None:
        repo = PresetRepository(db)
        service = PresetService(repo)

        p1 = service.create(name="First", is_default=True)
        assert p1.is_default is True

        p2 = service.create(name="Second", is_default=True)
        assert p2.is_default is True

        db.refresh(p1)
        assert p1.is_default is False

    def test_update_preset(self, db: Session) -> None:
        repo = PresetRepository(db)
        service = PresetService(repo)

        preset = service.create(name="Original", parameters={"temperature": 0.7})
        updated = service.update(preset.id, name="Renamed", parameters={"temperature": 1.0})

        assert updated.name == "Renamed"
        assert updated.parameters["temperature"] == 1.0

    def test_delete_preset(self, db: Session) -> None:
        repo = PresetRepository(db)
        service = PresetService(repo)

        preset = service.create(name="ToDelete")
        service.delete(preset.id)

        with pytest.raises(HTTPException) as exc_info:
            service.get_by_id(preset.id)
        assert exc_info.value.status_code == 404

    def test_get_by_id_not_found(self, db: Session) -> None:
        repo = PresetRepository(db)
        service = PresetService(repo)

        with pytest.raises(HTTPException) as exc_info:
            service.get_by_id("nonexistent")
        assert exc_info.value.status_code == 404

    def test_list_all(self, db: Session) -> None:
        repo = PresetRepository(db)
        service = PresetService(repo)

        service.create(name="Preset A")
        service.create(name="Preset B")

        presets = service.list_all()
        assert len(presets) == 2

    def test_set_default(self, db: Session) -> None:
        repo = PresetRepository(db)
        service = PresetService(repo)

        p1 = service.create(name="P1", is_default=True)
        p2 = service.create(name="P2")

        service.set_default(p2.id)
        db.refresh(p1)
        db.refresh(p2)

        assert p1.is_default is False
        assert p2.is_default is True
