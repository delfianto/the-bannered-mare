"""Tests for FragmentService"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.core.persistence import PromptTemplate, gen_id
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_fragment.service import FragmentService


def _make_service(db: Session) -> FragmentService:
    return FragmentService(FragmentRepository(db), TemplateFragmentRepository(db))


def _make_template(db: Session, name: str = "Default") -> PromptTemplate:
    tpl = PromptTemplate(
        id=gen_id(),
        name=name,
        system_template="You are {{char}}.",
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


class TestFragmentCRUD:
    def test_create_fragment(self, db: Session) -> None:
        service = _make_service(db)

        fragment = service.create(
            name="NSFW Rules",
            content="Always stay in character.",
            description="Basic NSFW instructions",
            fragment_type="nsfw",
            is_global=True,
        )

        assert fragment.id is not None
        assert fragment.name == "NSFW Rules"
        assert fragment.content == "Always stay in character."
        assert fragment.description == "Basic NSFW instructions"
        assert fragment.fragment_type == "nsfw"
        assert fragment.is_global is True

    def test_create_fragment_jinja2_validation_error(self, db: Session) -> None:
        service = _make_service(db)

        with pytest.raises(HTTPException) as exc_info:
            service.create(
                name="Bad Template",
                content="{% if foo %}missing end",
            )
        assert exc_info.value.status_code == 400
        assert "Invalid Jinja2 content" in str(exc_info.value.detail)

    def test_create_fragment_valid_jinja2(self, db: Session) -> None:
        service = _make_service(db)

        fragment = service.create(
            name="Conditional Fragment",
            content="{% if char %}Hello, {{char}}!{% endif %}",
        )
        assert fragment.content == "{% if char %}Hello, {{char}}!{% endif %}"

    def test_update_fragment(self, db: Session) -> None:
        service = _make_service(db)

        fragment = service.create(name="Original", content="Old content")
        updated = service.update(
            fragment.id,
            name="Renamed",
            content="New content",
            description="Now with a description",
            fragment_type="jailbreak",
            is_global=True,
        )

        assert updated.name == "Renamed"
        assert updated.content == "New content"
        assert updated.description == "Now with a description"
        assert updated.fragment_type == "jailbreak"
        assert updated.is_global is True

    def test_update_fragment_partial(self, db: Session) -> None:
        service = _make_service(db)

        fragment = service.create(
            name="Keep Most",
            content="Keep this",
            fragment_type="instruction",
            is_global=False,
        )
        updated = service.update(fragment.id, name="Only Name Changed")

        assert updated.name == "Only Name Changed"
        assert updated.content == "Keep this"
        assert updated.fragment_type == "instruction"
        assert updated.is_global is False

    def test_update_fragment_jinja2_validation_error(self, db: Session) -> None:
        service = _make_service(db)

        fragment = service.create(name="Good", content="Valid content")
        with pytest.raises(HTTPException) as exc_info:
            service.update(fragment.id, content="{% if broken %}no end")
        assert exc_info.value.status_code == 400

    def test_delete_fragment(self, db: Session) -> None:
        service = _make_service(db)

        fragment = service.create(name="ToDelete", content="Bye")
        service.delete(fragment.id)

        with pytest.raises(HTTPException) as exc_info:
            service.get_by_id(fragment.id)
        assert exc_info.value.status_code == 404

    def test_get_by_id_not_found(self, db: Session) -> None:
        service = _make_service(db)

        with pytest.raises(HTTPException) as exc_info:
            service.get_by_id("nonexistent")
        assert exc_info.value.status_code == 404


class TestFragmentListing:
    def test_list_all(self, db: Session) -> None:
        service = _make_service(db)

        service.create(name="Fragment A", content="A")
        service.create(name="Fragment B", content="B")

        fragments = service.list_all()
        assert len(fragments) == 2

    def test_list_by_type(self, db: Session) -> None:
        service = _make_service(db)

        service.create(name="NSFW 1", content="A", fragment_type="nsfw")
        service.create(name="NSFW 2", content="B", fragment_type="nsfw")
        service.create(name="Instruction 1", content="C", fragment_type="instruction")

        nsfw = service.list_all(fragment_type="nsfw")
        assert len(nsfw) == 2
        assert all(f.fragment_type == "nsfw" for f in nsfw)

        instructions = service.list_all(fragment_type="instruction")
        assert len(instructions) == 1

    def test_list_global(self, db: Session) -> None:
        service = _make_service(db)

        service.create(name="Global 1", content="A", is_global=True)
        service.create(name="Global 2", content="B", is_global=True)
        service.create(name="Local 1", content="C", is_global=False)

        global_fragments = service.list_all(is_global=True)
        assert len(global_fragments) == 2
        assert all(f.is_global is True for f in global_fragments)

    def test_list_all_no_filter(self, db: Session) -> None:
        service = _make_service(db)

        service.create(name="F1", content="A", fragment_type="nsfw", is_global=True)
        service.create(name="F2", content="B", fragment_type="instruction", is_global=False)

        all_fragments = service.list_all()
        assert len(all_fragments) == 2


class TestTemplateFragmentAttachment:
    def test_attach_fragment_to_template(self, db: Session) -> None:
        service = _make_service(db)
        template = _make_template(db)
        fragment = service.create(name="Attached", content="Inject me")

        tf = service.attach_to_template(
            template_id=template.id,
            fragment_id=fragment.id,
            position="after_system",
            ordinal=0,
        )

        assert tf.template_id == template.id
        assert tf.fragment_id == fragment.id
        assert tf.position == "after_system"
        assert tf.ordinal == 0

    def test_duplicate_attachment_fails(self, db: Session) -> None:
        service = _make_service(db)
        template = _make_template(db)
        fragment = service.create(name="Once Only", content="One shot")

        service.attach_to_template(template.id, fragment.id)

        with pytest.raises(HTTPException) as exc_info:
            service.attach_to_template(template.id, fragment.id)
        assert exc_info.value.status_code == 409
        assert "already attached" in str(exc_info.value.detail)

    def test_attach_nonexistent_fragment_fails(self, db: Session) -> None:
        service = _make_service(db)
        template = _make_template(db)

        with pytest.raises(HTTPException) as exc_info:
            service.attach_to_template(template.id, "nonexistent")
        assert exc_info.value.status_code == 404

    def test_detach_fragment_from_template(self, db: Session) -> None:
        service = _make_service(db)
        template = _make_template(db)
        fragment = service.create(name="Detachable", content="Remove me")

        service.attach_to_template(template.id, fragment.id)
        service.detach_from_template(template.id, fragment.id)

        fragments = service.list_template_fragments(template.id)
        assert len(fragments) == 0

    def test_detach_nonexistent_attachment_fails(self, db: Session) -> None:
        service = _make_service(db)
        template = _make_template(db)
        fragment = service.create(name="Never Attached", content="Nope")

        with pytest.raises(HTTPException) as exc_info:
            service.detach_from_template(template.id, fragment.id)
        assert exc_info.value.status_code == 404
        assert "not attached" in str(exc_info.value.detail)

    def test_list_template_fragments_ordered(self, db: Session) -> None:
        service = _make_service(db)
        template = _make_template(db)

        f1 = service.create(name="Third", content="C")
        f2 = service.create(name="First", content="A")
        f3 = service.create(name="Second", content="B")

        service.attach_to_template(template.id, f1.id, position="post_history", ordinal=0)
        service.attach_to_template(template.id, f2.id, position="after_system", ordinal=0)
        service.attach_to_template(template.id, f3.id, position="after_system", ordinal=1)

        ordered = service.list_template_fragments(template.id)
        assert len(ordered) == 3
        assert ordered[0].fragment_id == f2.id
        assert ordered[1].fragment_id == f3.id
        assert ordered[2].fragment_id == f1.id
