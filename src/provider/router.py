"""Provider CRUD API endpoints"""

from fastapi import APIRouter, status

from src.provider.dependencies import ProviderServiceDep
from src.provider.schemas import (
    ProviderCreate,
    ProviderFlagsUpdate,
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
    )


@router.patch("/{provider_id}/flags", response_model=ProviderResponse)
def update_provider_flags(
    provider_id: str, flag_data: ProviderFlagsUpdate, service: ProviderServiceDep
):
    """Enable or disable a provider"""
    return service.update_flags(provider_id, **flag_data.model_dump())
