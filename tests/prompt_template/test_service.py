"""Tests for PromptTemplateService"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.prompt_template import PromptTemplate, PromptTemplateRepository, PromptTemplateService


class TestPromptTemplateService:
    """Test suite for PromptTemplateService"""

    def test_list_all(self, db: Session) -> None:
        """Test listing all prompt templates"""
        template1 = PromptTemplate(
            name="Default",
            system_template="You are {{char}}",
        )
        template2 = PromptTemplate(
            name="Advanced",
            system_template="Advanced template for {{char}}",
        )
        db.add_all([template1, template2])
        db.commit()

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        templates = service.list_all()

        assert len(templates) == 2
        assert any(t.name == "Default" for t in templates)
        assert any(t.name == "Advanced" for t in templates)

    def test_get_by_id_success(self, db: Session) -> None:
        """Test getting a template by ID successfully"""
        template = PromptTemplate(
            name="Test Template",
            system_template="You are {{char}}",
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        result = service.get_by_id(template.id)

        assert result.id == template.id
        assert result.name == "Test Template"
        assert result.system_template == "You are {{char}}"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a template that doesn't exist raises 404"""
        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_create_template_success(self, db: Session) -> None:
        """Test creating a template successfully"""
        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)

        with patch.object(service.template_service, "validate_template", return_value=(True, None)):
            _ = (
                template := service.create(
                    name="Test Template",
                    system_template="You are {{char}}",
                    description="A test template",
                    is_default=False,
                    component_order=["system_prompt", "character_context"],
                    components_enabled={"system_prompt": True, "character_context": True},
                )
            )

        assert template.name == "Test Template"
        assert template.system_template == "You are {{char}}"
        assert template.description == "A test template"
        assert template.is_default is False
        assert template.component_order == ["system_prompt", "character_context"]
        assert template.components_enabled == {
            "system_prompt": True,
            "character_context": True,
        }

    def test_create_template_invalid_syntax(self, db: Session) -> None:
        """Test creating a template with invalid syntax raises error"""
        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)

        with (
            patch.object(
                service.template_service,
                "validate_template",
                return_value=(False, "Invalid syntax"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            _ = service.create(
                name="Test Template",
                system_template="Invalid {{template",
            )

        assert exc_info.value.status_code == 400
        assert "Invalid" in exc_info.value.detail
        assert "syntax" in exc_info.value.detail

    def test_create_template_as_default(self, db: Session) -> None:
        """Test creating a template as default unsets other defaults"""
        # Create existing default
        existing = PromptTemplate(
            name="Old Default",
            system_template="Old",
            is_default=True,
        )
        db.add(existing)
        db.commit()

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        with patch.object(service.template_service, "validate_template", return_value=(True, None)):
            new_default = service.create(
                name="New Default",
                system_template="New",
                is_default=True,
            )

        db.refresh(existing)
        assert existing.is_default is False
        assert new_default.is_default is True

    def test_update_template_success(self, db: Session) -> None:
        """Test updating a template successfully"""
        template = PromptTemplate(
            name="Old Name",
            system_template="Old template",
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        with patch.object(service.template_service, "validate_template", return_value=(True, None)):
            _ = (
                updated := service.update(
                    template.id,
                    name="New Name",
                    system_template="New template",
                    description="Updated description",
                )
            )

        assert updated.name == "New Name"
        assert updated.system_template == "New template"
        assert updated.description == "Updated description"

    def test_update_template_invalid_syntax(self, db: Session) -> None:
        """Test updating template with invalid syntax raises error"""
        template = PromptTemplate(
            name="Test",
            system_template="Valid template",
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        with (
            patch.object(
                service.template_service,
                "validate_template",
                return_value=(False, "Invalid syntax"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            _ = service.update(
                template.id,
                system_template="Invalid {{template",
            )

        assert exc_info.value.status_code == 400

    def test_update_template_to_default(self, db: Session) -> None:
        """Test updating template to be default"""
        # Create existing default
        existing_default = PromptTemplate(
            name="Old Default",
            system_template="Old",
            is_default=True,
        )
        template = PromptTemplate(
            name="Template",
            system_template="Template",
            is_default=False,
        )
        db.add_all([existing_default, template])
        db.commit()
        db.refresh(template)

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        updated = service.update(template.id, is_default=True)

        db.refresh(existing_default)
        assert existing_default.is_default is False
        assert updated.is_default is True

    def test_update_template_not_found(self, db: Session) -> None:
        """Test updating non-existent template raises 404"""
        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.update("nonexistent-id", name="New Name")

        assert exc_info.value.status_code == 404

    def test_delete_template_success(self, db: Session) -> None:
        """Test deleting a template successfully"""
        template = PromptTemplate(
            name="Test",
            system_template="Template",
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        template_id = template.id

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        service.delete(template_id)

        # Verify template is deleted
        deleted = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
        assert deleted is None

    def test_delete_template_not_found(self, db: Session) -> None:
        """Test deleting non-existent template raises 404"""
        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)

        with pytest.raises(HTTPException) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_set_default_template(self, db: Session) -> None:
        """Test setting a template as default"""
        # Create templates
        template1 = PromptTemplate(
            name="Template 1",
            system_template="T1",
            is_default=True,
        )
        template2 = PromptTemplate(
            name="Template 2",
            system_template="T2",
            is_default=False,
        )
        db.add_all([template1, template2])
        db.commit()
        db.refresh(template2)

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)
        result = service.set_default(template2.id)

        db.refresh(template1)
        assert template1.is_default is False
        assert result.is_default is True

    def test_set_default_template_not_found(self, db: Session) -> None:
        """Test setting non-existent template as default raises 404"""
        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.set_default("nonexistent-id")

        assert exc_info.value.status_code == 404
