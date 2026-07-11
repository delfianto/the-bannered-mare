"""Provider CRUD API endpoints"""

from fastapi import APIRouter, Query, status

from src.core.persistence import DbSession
from src.model.schemas import ModelResponse
from src.provider.dependencies import ProviderServiceDep
from src.provider.schemas import (
    AvailableModelsResponse,
    ModelActionRequest,
    ModelActionResponse,
    ModelSearchResponse,
    ProviderCreate,
    ProviderFlagsUpdate,
    ProviderModelFilterUpdate,
    ProviderResponse,
    ProviderUpdate,
)

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderResponse])
def list_providers(service: ProviderServiceDep):
    """List configured model providers"""
    return service.list_all()


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider(provider_data: ProviderCreate, service: ProviderServiceDep):
    """Register a new model provider"""
    return service.create(
        name=provider_data.name,
        provider_type=provider_data.provider_type,
        base_url=provider_data.base_url,
        api_key_env_var=provider_data.api_key_env_var,
    )


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: str, service: ProviderServiceDep):
    """Get provider details by ID"""
    return service.get_by_id(provider_id)


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: str, provider_data: ProviderUpdate, service: ProviderServiceDep):
    """Update provider configuration"""
    return service.update(
        provider_id=provider_id,
        name=provider_data.name,
        base_url=provider_data.base_url,
        api_key_env_var=provider_data.api_key_env_var,
        enabled=provider_data.enabled,
    )


@router.patch("/{provider_id}/flags", response_model=ProviderResponse)
def update_provider_flags(
    provider_id: str, flag_data: ProviderFlagsUpdate, service: ProviderServiceDep
):
    """Enable or disable a provider"""
    return service.update_flags(provider_id, **flag_data.model_dump())


@router.get("/{provider_id}/models/available", response_model=AvailableModelsResponse)
def list_available_models(provider_id: str, service: ProviderServiceDep):
    """List models live-detected on a local provider (Ollama/LM Studio), cache-aware"""
    return service.list_available_models(provider_id)


@router.post("/{provider_id}/models/sync", response_model=AvailableModelsResponse)
def sync_provider_models(provider_id: str, service: ProviderServiceDep):
    """Force a live refresh of a provider's model list, bypassing the cache"""
    return service.sync_models(provider_id)


@router.get("/{provider_id}/models/search", response_model=ModelSearchResponse)
def search_provider_models(
    provider_id: str,
    service: ProviderServiceDep,
    q: str = Query(default="", description="Substring to match against model id or name"),
):
    """Search a provider's live model list by name, ignoring the allow-list filter"""
    return service.search_models(provider_id, q)


@router.put("/{provider_id}/models/filter", response_model=AvailableModelsResponse)
def set_provider_model_filter(
    provider_id: str, filter_data: ProviderModelFilterUpdate, service: ProviderServiceDep
):
    """Set the curated allow-list and return the newly-filtered available models"""
    return service.set_allowed_models(provider_id, filter_data.allowed_models)


@router.post("/{provider_id}/models/load", response_model=ModelActionResponse)
def load_provider_model(
    provider_id: str, action_data: ModelActionRequest, service: ProviderServiceDep
):
    """Load a model into memory on a local provider"""
    return service.load_model(provider_id, action_data.model_identifier)


@router.post("/{provider_id}/models/unload", response_model=ModelActionResponse)
def unload_provider_model(
    provider_id: str, action_data: ModelActionRequest, service: ProviderServiceDep
):
    """Unload a model from memory on a local provider"""
    return service.unload_model(provider_id, action_data.model_identifier)


@router.delete("/{provider_id}/models", response_model=ModelActionResponse)
def delete_provider_model(
    provider_id: str,
    service: ProviderServiceDep,
    model_identifier: str = Query(..., description="Provider-native model identifier"),
):
    """Delete/remove a model from a local provider's registry/filesystem"""
    return service.delete_model(provider_id, model_identifier)


@router.post("/{provider_id}/models/persist", response_model=ModelResponse)
def persist_provider_model(
    provider_id: str,
    action_data: ModelActionRequest,
    db: DbSession,
):
    """Persist a discovered model: attach a route to the matching (or new) canonical model.

    If a route already exists for ``(provider, identifier)`` its canonical model is
    returned. Otherwise the identifier is matched to an existing canonical model by
    its provider-independent slug (adding this provider as a new route), or a new
    canonical model is created with a best-effort family guess — the user can correct
    the family/slug afterward.
    """
    from src.chat_session.repository import ChatRepository
    from src.model.lineage import normalize_slug, resolve_family
    from src.model.repository import ModelRepository
    from src.model.service import ModelService
    from src.model_family.models import ModelFamily
    from src.model_family.repository import ModelFamilyRepository
    from src.provider.repository import ProviderRepository

    model_repo = ModelRepository(db)
    provider_repo = ProviderRepository(db)
    family_repo = ModelFamilyRepository(db)
    chat_repo = ChatRepository(db)
    model_service = ModelService(model_repo, provider_repo, family_repo, chat_repo)

    identifier = action_data.model_identifier

    # Already routed on this provider → return the owning canonical model.
    existing_route = model_repo.find_route_by_provider_identifier(provider_id, identifier)
    if existing_route:
        return model_service.get_by_id(existing_route.model_registry_id)

    # Same canonical model reached through another provider → add this route to it.
    slug = normalize_slug(identifier)
    registry = model_repo.find_by_slug(slug)
    if registry:
        return model_service.add_route(
            registry.id, provider_id=provider_id, model_identifier=identifier
        )

    # New canonical model: best-effort family, else any family (user can correct).
    family = resolve_family(db, identifier) or db.query(ModelFamily).first()
    friendly_name = identifier.replace(":", " ").replace("-", " ").replace("/", " ").title()
    return model_service.create(
        display_name=friendly_name,
        model_family_id=family.id if family else "gttl91cmw18b",
        routes=[{"provider_id": provider_id, "model_identifier": identifier}],
        slug=slug,
        enabled=True,
    )
