"""Tests for PersonaService"""

import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import NotFoundError
from src.persona import Persona, PersonaRepository, PersonaService


class TestPersonaService:
    """Test suite for PersonaService"""

    def test_list_all(self, db: Session) -> None:
        """Test listing all personas"""
        persona1 = Persona(name="User", description="Default user persona")
        persona2 = Persona(name="Admin", description="Administrator persona")
        db.add_all([persona1, persona2])
        db.commit()

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        personas = service.list_all()

        assert len(personas) == 2
        assert any(p.name == "User" for p in personas)
        assert any(p.name == "Admin" for p in personas)

    def test_get_by_id_success(self, db: Session) -> None:
        """Test getting a persona by ID successfully"""
        persona = Persona(name="User", description="Test persona")
        db.add(persona)
        db.commit()
        db.refresh(persona)

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        result = service.get_by_id(persona.id)

        assert result.id == persona.id
        assert result.name == "User"
        assert result.description == "Test persona"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a persona that doesn't exist raises 404"""
        repo = PersonaRepository(db)
        service = PersonaService(repo)

        with pytest.raises(NotFoundError) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_persona_basic(self, db: Session) -> None:
        """Test creating a persona with basic fields"""
        repo = PersonaRepository(db)
        service = PersonaService(repo)

        persona = await service.create(
            name="User",
            description="Default user persona",
            is_default=False,
        )

        assert persona.name == "User"
        assert persona.description == "Default user persona"
        assert persona.is_default is False
        assert persona.id is not None

    @pytest.mark.asyncio
    async def test_create_persona_as_default(self, db: Session) -> None:
        """Test creating a persona as default"""
        repo = PersonaRepository(db)
        service = PersonaService(repo)

        persona = await service.create(
            name="User",
            description="Default persona",
            is_default=True,
        )

        assert persona.is_default is True

    @pytest.mark.asyncio
    async def test_create_persona_unsets_other_defaults(self, db: Session) -> None:
        """Test creating default persona unsets other defaults"""
        # Create existing default
        existing = Persona(name="Old Default", is_default=True)
        db.add(existing)
        db.commit()

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        new_default = await service.create(
            name="New Default",
            is_default=True,
        )

        db.refresh(existing)
        assert existing.is_default is False
        assert new_default.is_default is True

    @pytest.mark.asyncio
    async def test_update_persona_basic_fields(self, db: Session) -> None:
        """Test updating persona basic fields"""
        persona = Persona(name="User", description="Old description")
        db.add(persona)
        db.commit()
        db.refresh(persona)

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        updated = await service.update(
            persona.id,
            name="User Updated",
            description="New description",
        )

        assert updated.name == "User Updated"
        assert updated.description == "New description"

    @pytest.mark.asyncio
    async def test_update_persona_to_default(self, db: Session) -> None:
        """Test updating persona to be default"""
        # Create existing default
        existing_default = Persona(name="Old Default", is_default=True)
        persona = Persona(name="User", is_default=False)
        db.add_all([existing_default, persona])
        db.commit()
        db.refresh(persona)

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        updated = await service.update(persona.id, is_default=True)

        db.refresh(existing_default)
        assert existing_default.is_default is False
        assert updated.is_default is True

    @pytest.mark.asyncio
    async def test_update_persona_partial(self, db: Session) -> None:
        """Test updating only some fields"""
        persona = Persona(
            name="User",
            description="Description",
            is_default=False,
        )
        db.add(persona)
        db.commit()
        db.refresh(persona)

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        updated = await service.update(persona.id, description="Updated description")

        assert updated.name == "User"  # Unchanged
        assert updated.description == "Updated description"  # Changed
        assert updated.is_default is False  # Unchanged

    @pytest.mark.asyncio
    async def test_update_persona_not_found(self, db: Session) -> None:
        """Test updating non-existent persona raises 404"""
        repo = PersonaRepository(db)
        service = PersonaService(repo)

        with pytest.raises(NotFoundError) as exc_info:
            _ = await service.update("nonexistent-id", name="New Name")

        assert exc_info.value.status_code == 404

    def test_delete_persona_success(self, db: Session) -> None:
        """Test deleting a persona successfully"""
        persona = Persona(name="User")
        db.add(persona)
        db.commit()
        db.refresh(persona)
        persona_id = persona.id

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        service.delete(persona_id)

        # Verify persona is deleted
        deleted = db.query(Persona).filter(Persona.id == persona_id).first()
        assert deleted is None

    def test_delete_persona_not_found(self, db: Session) -> None:
        """Test deleting non-existent persona raises 404"""
        repo = PersonaRepository(db)
        service = PersonaService(repo)

        with pytest.raises(NotFoundError) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_set_default_persona(self, db: Session) -> None:
        """Test setting a persona as default"""
        # Create personas
        persona1 = Persona(name="Persona 1", is_default=True)
        persona2 = Persona(name="Persona 2", is_default=False)
        db.add_all([persona1, persona2])
        db.commit()
        db.refresh(persona2)

        repo = PersonaRepository(db)
        service = PersonaService(repo)
        result = service.set_default(persona2.id)

        db.refresh(persona1)
        assert persona1.is_default is False
        assert result.is_default is True

    def test_set_default_persona_not_found(self, db: Session) -> None:
        """Test setting non-existent persona as default raises 404"""
        repo = PersonaRepository(db)
        service = PersonaService(repo)

        with pytest.raises(NotFoundError) as exc_info:
            _ = service.set_default("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_unset_all_defaults(self, db: Session) -> None:
        """Test unsetting all default personas"""
        # Create multiple defaults
        persona1 = Persona(name="Default 1", is_default=True)
        persona2 = Persona(name="Default 2", is_default=True)
        db.add_all([persona1, persona2])
        db.commit()

        repo = PersonaRepository(db)
        repo.unset_all_defaults()
        db.commit()

        db.refresh(persona1)
        db.refresh(persona2)
        assert persona1.is_default is False
        assert persona2.is_default is False

    def test_unset_all_defaults_except_one(self, db: Session) -> None:
        """Test unsetting all defaults except specified one"""
        # Create multiple defaults
        persona1 = Persona(name="Default 1", is_default=True)
        persona2 = Persona(name="Default 2", is_default=True)
        db.add_all([persona1, persona2])
        db.commit()
        db.refresh(persona1)

        repo = PersonaRepository(db)
        repo.unset_all_defaults(exclude_id=persona1.id)
        db.commit()

        db.refresh(persona1)
        db.refresh(persona2)
        assert persona1.is_default is True  # Excluded
        assert persona2.is_default is False  # Unset
