"""API tests for the canonical-model (registry) + route endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.persistence import get_db
from src.main import app
from src.model import ModelRegistry, ModelRoute
from src.model_family import ModelFamily
from src.provider import Provider, ProviderType


@pytest.fixture
def client(db_session: Session):  # type: ignore[no-untyped-def]
    """Create a TestClient with the sync database dependency overridden."""

    def override_get_db():  # type: ignore[no-untyped-def]
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _lmstudio_family(db: Session) -> ModelFamily:
    """A keyless (LM Studio) family so route validation needs no API key env."""
    family = ModelFamily(
        name="Local Family",
        family_identifier="test.local",
        provider_types=["lmstudio"],
        parameters={"temperature": {"type": "float", "default": 0.7, "max_value": 2.0}},
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def _lmstudio_provider(db: Session) -> Provider:
    provider = Provider(name="LM Studio", provider_type=ProviderType.LMSTUDIO)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def _seed_registry(
    db: Session,
    provider: Provider,
    family: ModelFamily,
    *,
    slug: str,
    display_name: str,
    identifier: str,
) -> ModelRegistry:
    registry = ModelRegistry(
        slug=slug,
        display_name=display_name,
        original_identifier=identifier,
        model_family_id=family.id,
    )
    db.add(registry)
    db.flush()
    route = ModelRoute(
        model_registry_id=registry.id,
        provider_id=provider.id,
        model_identifier=identifier,
    )
    db.add(route)
    db.flush()
    registry.active_route_id = route.id
    db.commit()
    db.refresh(registry)
    return registry


def test_list_models_embeds_routes_not_family(client: TestClient, db_session: Session) -> None:
    """The list view embeds routes for the UI but omits the family + heavy fields."""
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    model = _seed_registry(
        db_session, provider, family, slug="gpt-4", display_name="GPT-4", identifier="gpt-4"
    )

    response = client.get("/api/models")

    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == model.id
    assert item["slug"] == "gpt-4"
    assert item["model_family_id"] == family.id
    assert item["active_route_id"] == model.active_route_id
    assert len(item["routes"]) == 1
    assert item["routes"][0]["model_identifier"] == "gpt-4"
    assert item["provider_enabled"] is True
    # List view stays lean.
    assert "model_family" not in item
    assert "parameters" not in item
    assert "template_id" not in item


def test_get_model_embeds_family(client: TestClient, db_session: Session) -> None:
    """The detail view embeds the family + full fields."""
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    model = _seed_registry(
        db_session,
        provider,
        family,
        slug="claude-3",
        display_name="Claude 3",
        identifier="claude-3-opus",
    )

    response = client.get(f"/api/models/{model.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == model.id
    assert data["slug"] == "claude-3"
    assert data["model_family_id"] == family.id
    assert data["model_family"]["id"] == family.id
    assert data["model_family"]["name"] == "Local Family"
    assert "parameters" in data
    assert "template_id" in data
    assert data["routes"][0]["model_identifier"] == "claude-3-opus"


def test_get_model_not_found(client: TestClient) -> None:
    assert client.get("/api/models/does-not-exist").status_code == 404


def test_list_models_with_name_filter(client: TestClient, db_session: Session) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    _seed_registry(
        db_session, provider, family, slug="gpt-4", display_name="GPT-4", identifier="gpt-4"
    )
    _seed_registry(
        db_session, provider, family, slug="gpt-35", display_name="GPT-3.5", identifier="gpt-3.5"
    )
    _seed_registry(
        db_session, provider, family, slug="claude", display_name="Claude", identifier="claude"
    )

    response = client.get("/api/models?name__ilike=gpt")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    assert {m["display_name"] for m in data["items"]} == {"GPT-4", "GPT-3.5"}

    response = client.get("/api/models?name__ilike=claude")
    assert response.status_code == 200
    assert response.json()["items"][0]["display_name"] == "Claude"


def test_create_model_attaches_route_and_derives_slug(
    client: TestClient, db_session: Session
) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)

    response = client.post(
        "/api/models",
        json={
            "display_name": "Local Llama",
            "model_family_id": family.id,
            "routes": [{"provider_id": provider.id, "model_identifier": "meta/llama-3.3-70b:free"}],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "llama-3.3-70b"  # vendor prefix + :variant stripped
    assert data["original_identifier"] == "meta/llama-3.3-70b:free"
    assert len(data["routes"]) == 1
    assert data["active_route_id"] == data["routes"][0]["id"]
    assert data["provider_enabled"] is True


def test_create_model_duplicate_slug_conflict(client: TestClient, db_session: Session) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    _seed_registry(
        db_session, provider, family, slug="taken", display_name="Taken", identifier="taken"
    )

    response = client.post(
        "/api/models",
        json={
            "display_name": "Dup",
            "model_family_id": family.id,
            "slug": "taken",
            "routes": [{"provider_id": provider.id, "model_identifier": "dup-id"}],
        },
    )

    assert response.status_code == 409


def test_add_route_endpoint(client: TestClient, db_session: Session) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    model = _seed_registry(
        db_session, provider, family, slug="m", display_name="M", identifier="m-id"
    )
    provider2 = Provider(name="LM Studio 2", provider_type=ProviderType.LMSTUDIO)
    db_session.add(provider2)
    db_session.commit()
    db_session.refresh(provider2)

    response = client.post(
        f"/api/models/{model.id}/routes",
        json={"provider_id": provider2.id, "model_identifier": "m-id-alt"},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["routes"]) == 2
    # The pre-existing active route is preserved.
    assert data["active_route_id"] == model.active_route_id


def test_delete_route_endpoint_repoints_active(client: TestClient, db_session: Session) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    model = _seed_registry(
        db_session, provider, family, slug="m", display_name="M", identifier="m-id"
    )
    first_route_id = model.active_route_id
    provider2 = Provider(name="LM Studio 2", provider_type=ProviderType.LMSTUDIO)
    db_session.add(provider2)
    db_session.commit()
    db_session.refresh(provider2)

    add = client.post(
        f"/api/models/{model.id}/routes",
        json={"provider_id": provider2.id, "model_identifier": "m-id-alt"},
    )
    second_route_id = next(r["id"] for r in add.json()["routes"] if r["id"] != first_route_id)

    response = client.delete(f"/api/models/{model.id}/routes/{first_route_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) == 1
    assert data["active_route_id"] == second_route_id


def test_set_active_route_endpoint(client: TestClient, db_session: Session) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    model = _seed_registry(
        db_session, provider, family, slug="m", display_name="M", identifier="m-id"
    )
    first_route_id = model.active_route_id
    provider2 = Provider(name="LM Studio 2", provider_type=ProviderType.LMSTUDIO)
    db_session.add(provider2)
    db_session.commit()
    db_session.refresh(provider2)

    add = client.post(
        f"/api/models/{model.id}/routes",
        json={"provider_id": provider2.id, "model_identifier": "m-id-alt"},
    )
    second_route_id = next(r["id"] for r in add.json()["routes"] if r["id"] != first_route_id)

    response = client.put(
        f"/api/models/{model.id}/active-route", json={"route_id": second_route_id}
    )

    assert response.status_code == 200
    assert response.json()["active_route_id"] == second_route_id


def test_update_flags_endpoint(client: TestClient, db_session: Session) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    model = _seed_registry(
        db_session, provider, family, slug="m", display_name="M", identifier="m-id"
    )

    response = client.patch(f"/api/models/{model.id}/flags", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_delete_model_endpoint(client: TestClient, db_session: Session) -> None:
    provider = _lmstudio_provider(db_session)
    family = _lmstudio_family(db_session)
    model = _seed_registry(
        db_session, provider, family, slug="m", display_name="M", identifier="m-id"
    )

    response = client.delete(f"/api/models/{model.id}")
    assert response.status_code == 204
    assert client.get(f"/api/models/{model.id}").status_code == 404
