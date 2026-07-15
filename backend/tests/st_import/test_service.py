"""Integration tests for STImportService against a real (SQLite) session."""

import json
from typing import Any

import pytest
from sqlalchemy.orm import Session
from src.core.persistence import Preset, PromptFragment, PromptTemplate
from src.preset.repository import PresetRepository
from src.profile.repository import ProfileRepository
from src.prompt_fragment.repository import FragmentRepository, TemplateFragmentRepository
from src.prompt_template.repository import PromptTemplateRepository

from tests.st_import.factories import (
    make_service,
    make_upload,
    preset_dict,
    st_marker,
    st_prompt,
)


def _json(prompts, order_items, **kw) -> str:
    return json.dumps(preset_dict(prompts, order_items, **kw))


async def _import(db: Session, prompts, order_items, *, filename="Preset.json", **kw):
    service = make_service(db)
    return await service.import_preset(make_upload(_json(prompts, order_items, **kw), filename))


class TestImportCreatesEntities:
    async def test_both_template_and_preset_created(self, db: Session) -> None:
        result = await _import(
            db,
            [
                st_prompt("main", system_prompt=True, content="Be {{char}}."),
                st_prompt("rules", content="Follow the rules."),
                st_marker("chatHistory"),
            ],
            ["main", "rules", "chatHistory"],
            filename="Adventure.json",
            samplers={"temperature": 0.8},
        )
        assert result.template_name == "Adventure"
        assert result.preset_id is not None
        assert len(result.fragment_ids) == 1

        tmpl = PromptTemplateRepository(db).find_by_name("Adventure")
        assert tmpl is not None
        assert tmpl.system_template == "Be {{char}}."
        links = TemplateFragmentRepository(db).find_by_template_id(tmpl.id)
        assert len(links) == 1
        assert links[0].fragment_id == result.fragment_ids[0]
        assert PresetRepository(db).find_by_name("Adventure") is not None

        # A profile ties the template + preset into one selectable unit.
        assert result.profile_id is not None
        assert result.profile_name == "Adventure"
        profile = ProfileRepository(db).find_by_name("Adventure")
        assert profile is not None
        assert profile.prompt_template_id == result.template_id
        assert profile.preset_id == result.preset_id
        assert profile.source == "sillytavern"
        assert profile.source_filename == "Adventure.json"

    async def test_prompts_only_creates_no_preset(self, db: Session) -> None:
        result = await _import(
            db, [st_prompt("rules", content="x")], ["rules"], filename="PromptsOnly.json"
        )
        assert result.preset_id is None
        assert PresetRepository(db).find_by_name("PromptsOnly") is None
        assert any("No sampler settings" in w for w in result.warnings)

        # A profile is still created (template only, preset unset).
        assert result.profile_id is not None
        profile = ProfileRepository(db).find_by_name("PromptsOnly")
        assert profile is not None
        assert profile.prompt_template_id == result.template_id
        assert profile.preset_id is None

    async def test_at_depth_depth_persisted(self, db: Session) -> None:
        result = await _import(
            db,
            [
                st_prompt(
                    "deep", content="stay in character", injection_position=1, injection_depth=6
                )
            ],
            ["deep"],
            filename="Deep.json",
        )
        link = TemplateFragmentRepository(db).find_by_template_id(result.template_id)[0]
        assert link.position == "at_depth"
        assert link.depth == 6

    async def test_empty_builtin_not_persisted(self, db: Session) -> None:
        result = await _import(
            db,
            [
                st_prompt("nsfw", system_prompt=True, content=""),
                st_prompt("rules", content="real"),
            ],
            ["nsfw", "rules"],
        )
        assert len(result.fragment_ids) == 1
        assert FragmentRepository(db).find_by_name("nsfw") is None

    async def test_non_jinja_macro_content_persists_without_error(self, db: Session) -> None:
        result = await _import(db, [st_prompt("dice", content="Roll {{roll:1d6}} now")], ["dice"])
        frag = FragmentRepository(db).find_by_id(result.fragment_ids[0])
        assert frag is not None
        assert frag.content == "Roll {{roll:1d6}} now"


class TestCollisionAutoSuffix:
    async def test_template_name_collision(self, db: Session) -> None:
        db.add(PromptTemplate(name="Dup", system_template="x"))
        db.commit()
        result = await _import(db, [st_prompt("c", content="x")], ["c"], filename="Dup.json")
        assert result.template_name == "Dup (2)"

    async def test_fragment_name_collision(self, db: Session) -> None:
        db.add(PromptFragment(name="rules", fragment_type="instruction", content="seed"))
        db.commit()
        result = await _import(
            db, [st_prompt("rules", name="rules", content="x")], ["rules"], filename="P.json"
        )
        frag = FragmentRepository(db).find_by_id(result.fragment_ids[0])
        assert frag is not None
        assert frag.name == "rules (2)"

    async def test_preset_name_collision(self, db: Session) -> None:
        db.add(Preset(name="Dup", parameters={}))
        db.commit()
        result = await _import(
            db,
            [st_prompt("c", content="x")],
            ["c"],
            filename="Dup.json",
            samplers={"temperature": 0.5},
        )
        # Template name "Dup" is free; only the preset collides.
        assert result.template_name == "Dup"
        assert result.preset_name == "Dup (2)"

    async def test_repeated_import_suffixes(self, db: Session) -> None:
        first = await _import(db, [st_prompt("f", content="x")], ["f"], filename="Repeat.json")
        second = await _import(db, [st_prompt("f", content="x")], ["f"], filename="Repeat.json")
        third = await _import(db, [st_prompt("f", content="x")], ["f"], filename="Repeat.json")
        assert first.template_name == "Repeat"
        assert second.template_name == "Repeat (2)"
        assert third.template_name == "Repeat (3)"

    async def test_intra_import_fragment_collision(self, db: Session) -> None:
        result = await _import(
            db,
            [
                st_prompt("a", name="Same", content="A"),
                st_prompt("b", name="Same", content="B"),
            ],
            ["a", "b"],
        )
        names = {
            f.name
            for f in (FragmentRepository(db).find_by_id(i) for i in result.fragment_ids)
            if f is not None
        }
        assert names == {"Same", "Same (2)"}

    async def test_reimport_same_content_reuses_fragment(self, db: Session) -> None:
        """Reimporting the same preset should reuse fragments by content, not duplicate them."""
        first = await _import(
            db, [st_prompt("f", content="identical")], ["f"], filename="Reuse.json"
        )
        second = await _import(
            db, [st_prompt("f", content="identical")], ["f"], filename="Reuse.json"
        )

        assert second.template_name == "Reuse (2)"  # the template is still a fresh one
        assert second.fragment_ids == first.fragment_ids  # but the fragment is reused
        assert len(FragmentRepository(db).find_all_ordered()) == 1

    async def test_name_truncation_with_suffix_fits(self, db: Session) -> None:
        long_name = "A" * 100
        db.add(PromptTemplate(name=long_name, system_template="x"))
        db.commit()
        result = await _import(
            db, [st_prompt("c", content="x")], ["c"], filename=f"{long_name}.json"
        )
        assert len(result.template_name) <= 100
        assert result.template_name.endswith(" (2)")


class TestAtomicity:
    async def test_failure_mid_persist_rolls_back(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = make_service(db)

        def _boom(_entity: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(service.preset_service.preset_repo, "create", _boom)

        data = _json(
            [st_prompt("main", system_prompt=True, content="X"), st_prompt("r", content="y")],
            ["main", "r"],
            samplers={"temperature": 0.7},
        )
        with pytest.raises(RuntimeError):
            await service.import_preset(make_upload(data, "Boom.json"))

        # Nothing committed: template + fragments + profile rolled back.
        assert PromptTemplateRepository(db).find_all() == []
        assert FragmentRepository(db).find_all() == []
        assert PresetRepository(db).find_all() == []
        assert ProfileRepository(db).find_all() == []


class TestBadFiles:
    async def test_wrong_extension_raises_400(self, db: Session) -> None:
        from src.core.exceptions import BanneredMareException

        service = make_service(db)
        with pytest.raises(BanneredMareException) as exc:
            await service.import_preset(make_upload(b"{}", "preset.png"))
        assert exc.value.status_code == 422

    async def test_invalid_json_raises_400(self, db: Session) -> None:
        from src.core.exceptions import BanneredMareException

        service = make_service(db)
        with pytest.raises(BanneredMareException) as exc:
            await service.import_preset(make_upload(b"{nope", "preset.json"))
        assert exc.value.status_code == 422
