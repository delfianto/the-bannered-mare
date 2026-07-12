"""Build ProviderGateways for a chat's main + task models.

Extracted from ChatMessageService: resolving a canonical model's active route,
validating the provider key, and constructing the gateway are transport/config
concerns independent of message business logic. Kept as module functions (they
are stateless — everything comes from the eager-loaded ``Chat``).
"""

from fastapi import HTTPException, status

from src.chat_session.models import Chat
from src.model.models import ModelRegistry, ModelRoute
from src.provider.gateway import ProviderGateway


def resolve_active_route(model: ModelRegistry) -> ModelRoute:
    """The route a canonical model currently resolves to (provider + identifier)."""
    route = model.active_route
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model.display_name}' has no active route configured.",
        )
    return route


def validate_model_and_key(chat: Chat) -> None:
    """Validate that the chat has a model whose active route's provider is keyed."""
    if not chat.model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat does not have a valid model assigned.",
        )
    provider = resolve_active_route(chat.model).provider
    if not provider.has_api_key():
        env_var_name = provider.get_env_var_name()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key not configured for provider '{provider.name}'. Set {env_var_name}",
        )


def build_gateway(chat: Chat) -> ProviderGateway:
    """Gateway from the main model's active route + optional preset params."""
    if chat.model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat does not have a valid model assigned.",
        )
    route = resolve_active_route(chat.model)
    preset_params = chat.preset.parameters if chat.preset else None
    return ProviderGateway(
        route.provider, chat.model, route.model_identifier, preset_parameters=preset_params
    )


def build_task_gateway(chat: Chat, *, minimize_reasoning: bool = False) -> ProviderGateway:
    """Gateway for auxiliary calls (titles, suggestions). Uses the chat's task
    model, falling back to the main model, at model defaults (no RP preset).

    ``minimize_reasoning`` suppresses reasoning tokens for throwaway calls; it is
    a no-op unless the task model's family is reasoning-capable.
    """
    model = chat.task_model or chat.model
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat does not have a valid model assigned.",
        )
    route = resolve_active_route(model)
    provider = route.provider
    if not provider.has_api_key():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"API key not configured for provider '{provider.name}'. "
                f"Set {provider.get_env_var_name()}"
            ),
        )
    return ProviderGateway(
        route.provider,
        model,
        route.model_identifier,
        preset_parameters=None,
        minimize_reasoning=minimize_reasoning,
    )
