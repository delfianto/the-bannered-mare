"""Tests for PromptTemplateService"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import BanneredMareException, NotFoundError
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_fragment.service import FragmentService
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

        with pytest.raises(NotFoundError) as exc_info:
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
            pytest.raises(BanneredMareException) as exc_info,
        ):
            _ = service.create(
                name="Test Template",
                system_template="Invalid {{template",
            )

        assert exc_info.value.status_code == 422
        assert "Invalid" in exc_info.value.message
        assert "syntax" in exc_info.value.message

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
            pytest.raises(BanneredMareException) as exc_info,
        ):
            _ = service.update(
                template.id,
                system_template="Invalid {{template",
            )

        assert exc_info.value.status_code == 422

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

        with pytest.raises(NotFoundError) as exc_info:
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

        with pytest.raises(NotFoundError) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_delete_template_cleans_up_orphaned_fragment(self, db: Session) -> None:
        """A private (non-global) fragment left unattached after deletion is removed too"""
        template = PromptTemplate(name="Imported", system_template="You are {{char}}")
        db.add(template)
        db.commit()
        db.refresh(template)

        fragment_service = FragmentService(FragmentRepository(db), TemplateFragmentRepository(db))
        fragment = fragment_service.create(name="One-off", content="private instructions")
        fragment_service.attach_to_template(template.id, fragment.id)
        fragment_id = fragment.id

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo, fragment_service)
        service.delete(template.id)

        assert FragmentRepository(db).find_by_id(fragment_id) is None

    def test_delete_template_keeps_global_fragment(self, db: Session) -> None:
        """A global fragment survives even if its last template attachment is deleted"""
        template = PromptTemplate(name="Imported", system_template="You are {{char}}")
        db.add(template)
        db.commit()
        db.refresh(template)

        fragment_service = FragmentService(FragmentRepository(db), TemplateFragmentRepository(db))
        fragment = fragment_service.create(
            name="Shared Library Entry", content="reusable", is_global=True
        )
        fragment_service.attach_to_template(template.id, fragment.id)
        fragment_id = fragment.id

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo, fragment_service)
        service.delete(template.id)

        assert FragmentRepository(db).find_by_id(fragment_id) is not None

    def test_delete_template_keeps_fragment_shared_with_another_template(self, db: Session) -> None:
        """A fragment still attached to a different template is not deleted"""
        template_a = PromptTemplate(name="A", system_template="A")
        template_b = PromptTemplate(name="B", system_template="B")
        db.add_all([template_a, template_b])
        db.commit()
        db.refresh(template_a)
        db.refresh(template_b)

        fragment_service = FragmentService(FragmentRepository(db), TemplateFragmentRepository(db))
        fragment = fragment_service.create(name="Shared", content="reused")
        fragment_service.attach_to_template(template_a.id, fragment.id)
        fragment_service.attach_to_template(template_b.id, fragment.id)
        fragment_id = fragment.id

        repo = PromptTemplateRepository(db)
        service = PromptTemplateService(repo, fragment_service)
        service.delete(template_a.id)

        assert FragmentRepository(db).find_by_id(fragment_id) is not None

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

        with pytest.raises(NotFoundError) as exc_info:
            _ = service.set_default("nonexistent-id")

        assert exc_info.value.status_code == 404
