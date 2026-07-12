"""Applying a profile onto a chat copies its non-null axes (via ChatService)."""

from typing import Any

import pytest
from sqlalchemy.orm import Session
from src.character import CharacterRepository
from src.chat_session import ChatRepository, ChatService
from src.core.exceptions import BanneredMareException
from src.core.persistence import Preset, PromptTemplate
from src.model import ModelRegistry, ModelRepository, ModelRoute
from src.persona.repository import PersonaRepository
from src.preset.repository import PresetRepository
from src.profile.repository import ProfileRepository
from src.profile.service import ProfileService
from src.prompt_template.repository import PromptTemplateRepository


def _chat_service(db: Session) -> ChatService:
    return ChatService(
        ChatRepository(db), CharacterRepository(db), ModelRepository(db), ProfileRepository(db)
    )


def _profile_service(db: Session) -> ProfileService:
    return ProfileService(
        profile_repo=ProfileRepository(db),
        template_repo=PromptTemplateRepository(db),
        preset_repo=PresetRepository(db),
        persona_repo=PersonaRepository(db),
        model_repo=ModelRepository(db),
    )


class TestApplyProfile:
    def test_create_chat_applies_profile(
        self, db: Session, sample_character: Any, sample_model: Any, sample_persona: Any
    ) -> None:
        tmpl = PromptTemplate(name="T", system_template="x")
        preset = Preset(name="P", parameters={})
        db.add_all([tmpl, preset])
        db.commit()
        db.refresh(tmpl)
        db.refresh(preset)

        profile = _profile_service(db).create(
            name="Full Loadout",
            prompt_template_id=tmpl.id,
            preset_id=preset.id,
            persona_id=sample_persona.id,
            model_id=sample_model.id,
        )

        chat = _chat_service(db).create(character_id=sample_character.id, profile_id=profile.id)

        assert chat.template_id == tmpl.id
        assert chat.preset_id == preset.id
        assert chat.persona_id == sample_persona.id
        assert chat.model_id == sample_model.id
        assert chat.model_name == sample_model.display_name  # snapshot
        # Provenance name snapshots (not FKs).
        assert chat.initial_profile_name == "Full Loadout"
        assert chat.last_profile_name == "Full Loadout"

    def test_explicit_model_overrides_profile(
        self,
        db: Session,
        sample_character: Any,
        sample_model: Any,
        sample_provider: Any,
        sample_family: Any,
    ) -> None:
        model2 = ModelRegistry(
            slug="gpt-3.5-turbo",
            display_name="GPT-3.5",
            original_identifier="gpt-3.5-turbo",
            model_family_id=sample_family.id,
        )
        db.add(model2)
        db.flush()
        route2 = ModelRoute(
            model_registry_id=model2.id,
            provider_id=sample_provider.id,
            model_identifier="gpt-3.5-turbo",
        )
        db.add(route2)
        db.flush()
        model2.active_route_id = route2.id
        db.commit()
        db.refresh(model2)

        profile = _profile_service(db).create(name="Loadout", model_id=sample_model.id)

        chat = _chat_service(db).create(
            character_id=sample_character.id, model_id=model2.id, profile_id=profile.id
        )

        assert chat.model_id == model2.id
        assert chat.model_name == model2.display_name

    def test_create_chat_with_missing_profile_raises_404(
        self, db: Session, sample_character: Any
    ) -> None:
        with pytest.raises(BanneredMareException) as exc_info:
            _chat_service(db).create(character_id=sample_character.id, profile_id="nonexistent")
        assert exc_info.value.status_code == 404
        assert "Profile" in exc_info.value.message

    def test_apply_profile_to_existing_chat(
        self, db: Session, sample_character: Any, sample_persona: Any
    ) -> None:
        chat_service = _chat_service(db)
        chat = chat_service.create(character_id=sample_character.id)
        assert chat.persona_id is None
        assert chat.initial_profile_name is None  # created bare

        profile = _profile_service(db).create(name="Later", persona_id=sample_persona.id)
        updated = chat_service.apply_profile(chat.id, profile.id)

        assert updated.persona_id == sample_persona.id
        assert updated.last_profile_name == "Later"
        # initial stays None: the chat was not born from a profile.
        assert updated.initial_profile_name is None
