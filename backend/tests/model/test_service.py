"""Tests for ModelService (canonical registry + provider routes)."""

from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session
from src.chat_session import Chat, ChatRepository
from src.chat_session.model_snapshot import ChatModelSnapshotService
from src.core.exceptions import BanneredMareException
from src.model import ModelRegistry, ModelRepository, ModelRoute, ModelService
from src.model_family import ModelFamily, ModelFamilyRepository
from src.provider import Provider, ProviderRepository, ProviderType


def _service(db: Session) -> ModelService:
    return ModelService(
        ModelRepository(db),
        ProviderRepository(db),
        ModelFamilyRepository(db),
        ChatModelSnapshotService(ChatRepository(db)),
    )


def _bare_registry(
    db: Session,
    family_id: str,
    *,
    slug: str = "reg",
    display_name: str = "Reg",
    identifier: str | None = None,
) -> ModelRegistry:
    """Persist a routeless canonical model directly (bypasses route validation)."""
    registry = ModelRegistry(
        slug=slug,
        display_name=display_name,
        original_identifier=identifier or slug,
        model_family_id=family_id,
    )
    db.add(registry)
    db.commit()
    db.refresh(registry)
    return registry


class TestModelServiceQueries:
    """list / get read paths."""

    def test_list_all(self, db: Session, sample_family: Any) -> None:
        _bare_registry(db, sample_family.id, slug="gpt-4", display_name="GPT-4")
        _bare_registry(db, sample_family.id, slug="gpt-3-5", display_name="GPT-3.5")

        models = _service(db).list_all()

        assert len(models) == 2
        assert {m.display_name for m in models} == {"GPT-4", "GPT-3.5"}

    def test_list_paginated_orders_by_name_case_insensitive(
        self, db: Session, sample_family: Any
    ) -> None:
        """list_paginated returns models alphabetically by display name, ignoring case."""
        for i, name in enumerate(["Zeta", "apex", "Mango", "banana"]):
            _bare_registry(db, sample_family.id, slug=f"slug-{i}", display_name=name)

        models, total = _service(db).list_paginated(limit=10, offset=0)

        assert total == 4
        assert [m.display_name for m in models] == ["apex", "banana", "Mango", "Zeta"]

    def test_list_paginated_filters_by_model_family(self, db: Session, sample_family: Any) -> None:
        """The model_family_id filter returns only that family's models."""
        other = ModelFamily(name="Other Family", family_identifier="test.other-family")
        db.add(other)
        db.commit()
        db.refresh(other)
        _bare_registry(db, sample_family.id, slug="in-fam", display_name="In Family")
        _bare_registry(db, other.id, slug="other", display_name="Other")

        models, total = _service(db).list_paginated(filters={"model_family_id": sample_family.id})

        assert total == 1
        assert [m.display_name for m in models] == ["In Family"]

    def test_list_paginated_filters_by_provider_route(
        self, db: Session, sample_model: Any, sample_provider: Any, sample_family: Any
    ) -> None:
        """provider_id filter keeps only models that have a route on that provider."""
        # sample_model has a route on sample_provider; this one has none.
        _bare_registry(db, sample_family.id, slug="unrouted", display_name="Unrouted")

        models, total = _service(db).list_paginated(filters={"provider_id": sample_provider.id})

        assert total == 1
        assert models[0].id == sample_model.id

    def test_get_by_id_success(self, db: Session, sample_model: Any) -> None:
        result = _service(db).get_by_id(sample_model.id)

        assert result.id == sample_model.id
        assert result.display_name == "GPT-4"
        assert result.slug == "gpt-4"
        assert result.active_route is not None
        assert result.active_route.model_identifier == "gpt-4"

    def test_get_by_id_not_found(self, db: Session) -> None:
        with pytest.raises(BanneredMareException) as exc_info:
            _ = _service(db).get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404


class TestModelServiceCreate:
    """create() + its route/slug/param validation."""

    def test_create_derives_slug_and_active_route_from_first_route(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """No slug given → derived from the (vendor-prefixed) route identifier."""
        with patch.object(Provider, "has_api_key", return_value=True):
            model = _service(db).create(
                display_name="DeepSeek V4 Pro",
                model_family_id=sample_family.id,
                routes=[
                    {
                        "provider_id": sample_provider.id,
                        "model_identifier": "deepseek/deepseek-v4-pro",
                    }
                ],
            )

        assert model.slug == "deepseek-v4-pro"
        assert model.original_identifier == "deepseek/deepseek-v4-pro"
        assert len(model.routes) == 1
        assert model.active_route_id == model.routes[0].id
        assert model.routes[0].model_identifier == "deepseek/deepseek-v4-pro"

    def test_create_with_explicit_slug(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        with patch.object(Provider, "has_api_key", return_value=True):
            model = _service(db).create(
                display_name="Custom",
                model_family_id=sample_family.id,
                slug="my-slug",
                routes=[{"provider_id": sample_provider.id, "model_identifier": "gpt-4-new"}],
            )

        assert model.slug == "my-slug"
        assert model.original_identifier == "gpt-4-new"

    def test_create_active_provider_id_selects_route(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """When several routes are given, active_provider_id picks the active one."""
        provider2 = Provider(name="OpenAI Alt", provider_type=ProviderType.OPENAI)
        db.add(provider2)
        db.commit()
        db.refresh(provider2)

        with patch.object(Provider, "has_api_key", return_value=True):
            model = _service(db).create(
                display_name="Multi",
                model_family_id=sample_family.id,
                slug="multi",
                routes=[
                    {"provider_id": sample_provider.id, "model_identifier": "gpt-4-a"},
                    {"provider_id": provider2.id, "model_identifier": "gpt-4-b"},
                ],
                active_provider_id=provider2.id,
            )

        active = next(r for r in model.routes if r.id == model.active_route_id)
        assert active.provider_id == provider2.id

    def test_create_requires_slug_or_route(self, db: Session, sample_family: Any) -> None:
        with pytest.raises(BanneredMareException) as exc:
            _service(db).create(display_name="X", model_family_id=sample_family.id)

        assert exc.value.status_code == 422
        assert "slug or at least one route" in exc.value.message

    def test_create_duplicate_slug_conflict(
        self, db: Session, sample_model: Any, sample_provider: Any, sample_family: Any
    ) -> None:
        """sample_model already owns slug 'gpt-4'."""
        with (
            patch.object(Provider, "has_api_key", return_value=True),
            pytest.raises(BanneredMareException) as exc,
        ):
            _service(db).create(
                display_name="Dup",
                model_family_id=sample_family.id,
                slug="gpt-4",
                routes=[{"provider_id": sample_provider.id, "model_identifier": "gpt-4-dup"}],
            )

        assert exc.value.status_code == 409
        assert "slug 'gpt-4'" in exc.value.message

    def test_create_rejects_invalid_parameter(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """temperature above the family max is a 400."""
        with (
            patch.object(Provider, "has_api_key", return_value=True),
            pytest.raises(BanneredMareException) as exc,
        ):
            _service(db).create(
                display_name="Hot",
                model_family_id=sample_family.id,
                slug="hot",
                parameters={"temperature": 3.0},  # family max_value is 2.0
                routes=[{"provider_id": sample_provider.id, "model_identifier": "gpt-4-hot"}],
            )

        assert exc.value.status_code == 422
        assert "greater than" in exc.value.message

    def test_create_rejects_unknown_parameter(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        with (
            patch.object(Provider, "has_api_key", return_value=True),
            pytest.raises(BanneredMareException) as exc,
        ):
            _service(db).create(
                display_name="Weird",
                model_family_id=sample_family.id,
                slug="weird",
                parameters={"made_up": 1},
                routes=[{"provider_id": sample_provider.id, "model_identifier": "gpt-4-weird"}],
            )

        assert exc.value.status_code == 422
        assert "not defined in model family" in exc.value.message

    def test_create_route_uniqueness_conflict(
        self, db: Session, sample_model: Any, sample_provider: Any, sample_family: Any
    ) -> None:
        """A (provider, identifier) already routed elsewhere is a 409."""
        # sample_model routes (sample_provider, 'gpt-4') already.
        with (
            patch.object(Provider, "has_api_key", return_value=True),
            pytest.raises(BanneredMareException) as exc,
        ):
            _service(db).create(
                display_name="Clash",
                model_family_id=sample_family.id,
                slug="clash",
                routes=[{"provider_id": sample_provider.id, "model_identifier": "gpt-4"}],
            )

        assert exc.value.status_code == 409
        assert "already exists" in exc.value.message

    def test_create_route_provider_not_found(self, db: Session, sample_family: Any) -> None:
        with pytest.raises(BanneredMareException) as exc:
            _service(db).create(
                display_name="Ghost",
                model_family_id=sample_family.id,
                slug="ghost",
                routes=[{"provider_id": "nope", "model_identifier": "x"}],
            )

        assert exc.value.status_code == 404
        assert "Provider" in exc.value.message

    def test_create_rejects_provider_type_not_in_family(self, db: Session) -> None:
        """A family that can't run on the chosen provider type is a 400."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        family = ModelFamily(
            name="Ollama-only Fam",
            family_identifier="test/ollama-only",
            provider_types=["ollama"],
        )
        db.add_all([provider, family])
        db.commit()

        with pytest.raises(BanneredMareException) as exc:
            _service(db).create(
                display_name="X",
                model_family_id=family.id,
                slug="x",
                routes=[{"provider_id": provider.id, "model_identifier": "x"}],
            )

        assert exc.value.status_code == 422
        assert "cannot serve" in exc.value.message

    def test_create_allows_provider_type_in_family(self, db: Session) -> None:
        """LM Studio (keyless) is allowed once the family lists it."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        family = ModelFamily(
            name="Local Fam",
            family_identifier="test/local",
            provider_types=["ollama", "lmstudio"],
        )
        db.add_all([provider, family])
        db.commit()

        created = _service(db).create(
            display_name="X",
            model_family_id=family.id,
            slug="x",
            routes=[{"provider_id": provider.id, "model_identifier": "x"}],
        )

        assert created.id
        assert created.active_route_id is not None


class TestModelServiceRoutes:
    """add_route / delete_route / set_active_route."""

    def test_add_route_keeps_existing_active(
        self, db: Session, sample_model: Any, sample_family: Any
    ) -> None:
        provider2 = Provider(name="OpenAI Alt", provider_type=ProviderType.OPENAI)
        db.add(provider2)
        db.commit()
        db.refresh(provider2)
        original_active = sample_model.active_route_id

        with patch.object(Provider, "has_api_key", return_value=True):
            model = _service(db).add_route(
                sample_model.id, provider_id=provider2.id, model_identifier="gpt-4-alt"
            )

        assert len(model.routes) == 2
        # Adding a route to a model that already had one does not steal active.
        assert model.active_route_id == original_active

    def test_add_route_sets_active_when_none(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        registry = _bare_registry(db, sample_family.id, slug="lonely")
        assert registry.active_route_id is None

        with patch.object(Provider, "has_api_key", return_value=True):
            model = _service(db).add_route(
                registry.id, provider_id=sample_provider.id, model_identifier="gpt-4-lonely"
            )

        assert model.active_route_id == model.routes[0].id

    def test_add_route_uniqueness_conflict(self, db: Session, sample_model: Any) -> None:
        """Re-adding the same (provider, identifier) is a 409."""
        with (
            patch.object(Provider, "has_api_key", return_value=True),
            pytest.raises(BanneredMareException) as exc,
        ):
            _service(db).add_route(
                sample_model.id,
                provider_id=sample_model.active_route.provider_id,
                model_identifier="gpt-4",
            )

        assert exc.value.status_code == 409

    def test_delete_route_repoints_active(
        self, db: Session, sample_model: Any, sample_family: Any
    ) -> None:
        provider2 = Provider(name="OpenAI Alt", provider_type=ProviderType.OPENAI)
        db.add(provider2)
        db.commit()
        db.refresh(provider2)
        first_route_id = sample_model.active_route_id

        with patch.object(Provider, "has_api_key", return_value=True):
            service = _service(db)
            model = service.add_route(
                sample_model.id, provider_id=provider2.id, model_identifier="gpt-4-alt"
            )
            second_route_id = next(r.id for r in model.routes if r.id != first_route_id)

            # Deleting the active (first) route repoints active to the survivor.
            model = service.delete_route(sample_model.id, first_route_id)

        assert len(model.routes) == 1
        assert model.active_route_id == second_route_id

    def test_delete_last_route_clears_active(self, db: Session, sample_model: Any) -> None:
        route_id = sample_model.active_route_id

        model = _service(db).delete_route(sample_model.id, route_id)

        assert model.routes == []
        assert model.active_route_id is None

    def test_delete_route_not_belonging_404(
        self, db: Session, sample_model: Any, sample_family: Any
    ) -> None:
        other = _bare_registry(db, sample_family.id, slug="other-reg")
        other_route = ModelRoute(
            model_registry_id=other.id,
            provider_id=sample_model.active_route.provider_id,
            model_identifier="foreign",
        )
        db.add(other_route)
        db.commit()
        db.refresh(other_route)

        with pytest.raises(BanneredMareException) as exc:
            _service(db).delete_route(sample_model.id, other_route.id)

        assert exc.value.status_code == 404

    def test_set_active_route_flip(
        self, db: Session, sample_model: Any, sample_family: Any
    ) -> None:
        provider2 = Provider(name="OpenAI Alt", provider_type=ProviderType.OPENAI)
        db.add(provider2)
        db.commit()
        db.refresh(provider2)
        first_route_id = sample_model.active_route_id

        with patch.object(Provider, "has_api_key", return_value=True):
            service = _service(db)
            model = service.add_route(
                sample_model.id, provider_id=provider2.id, model_identifier="gpt-4-alt"
            )
            second_route_id = next(r.id for r in model.routes if r.id != first_route_id)

            model = service.set_active_route(sample_model.id, second_route_id)

        assert model.active_route_id == second_route_id

    def test_set_active_route_not_belonging_404(self, db: Session, sample_model: Any) -> None:
        with pytest.raises(BanneredMareException) as exc:
            _service(db).set_active_route(sample_model.id, "not-a-route")

        assert exc.value.status_code == 404


class TestModelServiceUpdate:
    """update / update_flags / delete."""

    def test_update_fields(self, db: Session, sample_model: Any) -> None:
        updated = _service(db).update(
            sample_model.id,
            display_name="GPT-4 Turbo",
            slug="gpt-4-turbo",
            original_identifier="gpt-4-turbo-2024",
        )

        assert updated.display_name == "GPT-4 Turbo"
        assert updated.slug == "gpt-4-turbo"
        assert updated.original_identifier == "gpt-4-turbo-2024"

    def test_update_display_name_snapshots_onto_chats(
        self, db: Session, sample_model: Any, sample_character: Any
    ) -> None:
        chat = Chat(
            title="C",
            character_id=sample_character.id,
            model_id=sample_model.id,
            model_name="GPT-4",
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)

        _service(db).update(sample_model.id, display_name="Renamed GPT-4")

        db.expire_all()
        refreshed = db.query(Chat).filter(Chat.id == chat.id).first()
        assert refreshed is not None
        assert refreshed.model_name == "Renamed GPT-4"

    def test_update_duplicate_slug_conflict(
        self, db: Session, sample_model: Any, sample_family: Any
    ) -> None:
        _bare_registry(db, sample_family.id, slug="taken", display_name="Taken")

        with pytest.raises(BanneredMareException) as exc:
            _service(db).update(sample_model.id, slug="taken")

        assert exc.value.status_code == 409

    def test_update_does_not_partial_write_when_later_validation_fails(
        self, db: Session, sample_model: Any, sample_family: Any, sample_character: Any
    ) -> None:
        """A display_name change (and its cross-domain chat rename) must NOT persist
        when a later check in the same update — here a slug conflict — fails."""
        original_name = sample_model.display_name
        chat = Chat(
            title="C",
            character_id=sample_character.id,
            model_id=sample_model.id,
            model_name=original_name,
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)

        _bare_registry(db, sample_family.id, slug="taken", display_name="Taken")

        with pytest.raises(BanneredMareException) as exc:
            _service(db).update(sample_model.id, display_name="Should Not Persist", slug="taken")
        assert exc.value.status_code == 409

        db.expire_all()
        model = db.query(ModelRegistry).filter(ModelRegistry.id == sample_model.id).first()
        assert model is not None and model.display_name == original_name
        refreshed_chat = db.query(Chat).filter(Chat.id == chat.id).first()
        assert refreshed_chat is not None and refreshed_chat.model_name == original_name

    def test_update_family_change_revalidates_parameters(
        self, db: Session, sample_model: Any
    ) -> None:
        """A param valid under the old family but invalid under the new one is a 400."""
        strict = ModelFamily(
            name="Strict",
            family_identifier="test.strict",
            provider_types=["openai"],
            parameters={
                "temperature": {"type": "float", "default": 0.5, "min_value": 0.0, "max_value": 1.0}
            },
        )
        db.add(strict)
        db.commit()
        db.refresh(strict)

        with pytest.raises(BanneredMareException) as exc:
            _service(db).update(
                sample_model.id,
                model_family_id=strict.id,
                parameters={"temperature": 1.8},  # ok under GPT (max 2.0), not under Strict
            )

        assert exc.value.status_code == 422
        assert "greater than" in exc.value.message

    def test_update_rejects_family_change_incompatible_with_existing_route(
        self, db: Session, sample_model: Any
    ) -> None:
        """Switching to a family the model's existing route provider can't serve is a 400."""
        cloud = ModelFamily(
            name="Anthropic Only",
            family_identifier="test.anthropic-only",
            provider_types=["anthropic"],
        )
        db.add(cloud)
        db.commit()
        db.refresh(cloud)

        with pytest.raises(BanneredMareException) as exc:
            # sample_model's route is on an OpenAI provider.
            _service(db).update(sample_model.id, model_family_id=cloud.id)

        assert exc.value.status_code == 422
        assert "incompatible" in exc.value.message

    def test_update_flags(self, db: Session, sample_model: Any) -> None:
        updated = _service(db).update_flags(sample_model.id, enabled=False)
        assert updated.enabled is False

        updated = _service(db).update_flags(sample_model.id, enabled=True)
        assert updated.enabled is True

    def test_delete_model(self, db: Session, sample_model: Any) -> None:
        model_id = sample_model.id
        _service(db).delete(model_id)

        assert db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first() is None

    def test_delete_model_in_use_unlinks_chat(
        self, db: Session, sample_model: Any, sample_character: Any
    ) -> None:
        chat = Chat(title="C", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        _service(db).delete(sample_model.id)

        db.expire_all()
        refreshed = db.query(Chat).filter(Chat.id == chat.id).first()
        assert refreshed is not None
        assert refreshed.model_id is None

    def test_delete_model_not_found(self, db: Session) -> None:
        with pytest.raises(BanneredMareException) as exc_info:
            _service(db).delete("nonexistent-id")

        assert exc_info.value.status_code == 404
