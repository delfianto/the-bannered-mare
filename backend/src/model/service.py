"""Model business logic service"""

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status
from sqlalchemy.orm.attributes import flag_modified

from src.model.models import Model
from src.model.repository import ModelRepository
from src.model_family.models import ModelFamily
from src.model_family.repository import ModelFamilyRepository
from src.provider.models import Provider, ProviderType
from src.provider.repository import ProviderRepository

if TYPE_CHECKING:
    from src.chat_session.repository import ChatRepository


class ModelService:
    """Service for model-related business logic"""

    def __init__(
        self,
        model_repo: ModelRepository,
        provider_repo: ProviderRepository,
        family_repo: ModelFamilyRepository,
        chat_repo: ChatRepository,
    ):
        self.model_repo = model_repo
        self.provider_repo = provider_repo
        self.family_repo = family_repo
        self.chat_repo = chat_repo

    def list_all(self) -> list[Model]:
        """List all model definitions"""
        return self.model_repo.find_all()

    def list_paginated(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Model], int]:
        """List models with pagination and filtering"""
        return self.model_repo.find_paginated_with_count(limit, offset, filters=filters)

    def get_by_id(self, model_id: str) -> Model:
        """Get model definition by ID, raise 404 if not found"""
        model = self.model_repo.find_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID '{model_id}' not found",
            )
        return model

    def _validate_parameters(
        self, parameters: dict[str, Any], model_family: ModelFamily | None
    ) -> None:
        """
        Validates a dictionary of parameters against the ModelFamily constraints.
        """
        if not parameters or not model_family:
            return

        family_params = model_family.parameters or {}
        unsupported = model_family.unsupported_parameters or []

        for param_name, value in parameters.items():
            if param_name in unsupported:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{param_name}' is explicitly unsupported by model family '{model_family.name}'.",
                )

            if param_name not in family_params:
                supported_list = sorted(family_params.keys())
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{param_name}' is not defined in model family '{model_family.name}'. Supported: {', '.join(supported_list)}",
                )

            rule = family_params[param_name]
            self._validate_single_parameter(param_name, value, rule)

    def _validate_single_parameter(self, name: str, value: Any, rule: dict[str, Any]) -> None:
        """Helper to validate a single value against a rule dict based on new schema"""
        param_type = rule.get("type")

        if param_type == "int":
            if not isinstance(value, int):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' must be an integer.",
                )
        elif param_type == "float":
            if not isinstance(value, (int, float)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' must be a number (float/int).",
                )
        elif param_type == "string":
            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' must be a string.",
                )
        elif param_type == "boolean":
            if not isinstance(value, bool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' must be a boolean.",
                )
        elif param_type == "enum":
            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' (enum) must be a string.",
                )
        elif param_type == "list":
            if not isinstance(value, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' must be a list.",
                )
        elif param_type == "object" and not isinstance(value, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parameter '{name}' must be an object (dict).",
            )

        if param_type in ("int", "float"):
            if "min_value" in rule and rule["min_value"] is not None and value < rule["min_value"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' cannot be less than {rule['min_value']}.",
                )
            if "max_value" in rule and rule["max_value"] is not None and value > rule["max_value"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' cannot be greater than {rule['max_value']}.",
                )

        if param_type == "enum" and "str_values" in rule:
            allowed = rule["str_values"]
            if value not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parameter '{name}' must be one of: {', '.join(map(str, allowed))}.",
                )

    def create(
        self,
        name: str,
        provider_id: str,
        model_identifier: str,
        model_family_id: str,
        openrouter_identifier: str | None = None,
        use_openrouter: bool = False,
        template_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> Model:
        """Create a new model definition with parameter validation"""
        if parameters is None:
            parameters = {}

        provider = self.provider_repo.find_by_id(provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider with ID '{provider_id}' not found",
            )

        if not provider.has_api_key():
            env_var_name = provider.get_env_var_name()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create model: Provider '{provider.name}' requires {env_var_name} environment variable.",
            )

        model_family = self.family_repo.find_by_id(model_family_id)
        if not model_family:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model Family with ID '{model_family_id}' not found",
            )

        # The model's own provider must be one the family can actually run on.
        if provider.provider_type.value not in model_family.provider_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Provider '{provider.name}' ({provider.provider_type.value}) cannot serve "
                    f"model family '{model_family.name}'. "
                    f"Supported: {', '.join(model_family.provider_types) or 'none'}."
                ),
            )

        # Validate OpenRouter routing
        if use_openrouter:
            if "openrouter" not in model_family.provider_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model family '{model_family.name}' does not support OpenRouter routing",
                )
            if not openrouter_identifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenRouter identifier is required when use_openrouter is True",
                )

        self._validate_parameters(parameters, model_family)

        model = Model(
            name=name,
            provider_id=provider_id,
            model_identifier=model_identifier,
            openrouter_identifier=openrouter_identifier,
            use_openrouter=use_openrouter,
            model_family_id=model_family_id,
            template_id=template_id,
            parameters=parameters,
            enabled=enabled,
        )
        created = self.model_repo.create(model)
        self.model_repo.commit()
        return created

    def update(
        self,
        model_id: str,
        name: str | None = None,
        provider_id: str | None = None,
        model_identifier: str | None = None,
        openrouter_identifier: str | None = None,
        use_openrouter: bool | None = None,
        model_family_id: str | None = None,
        template_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        enabled: bool | None = None,
    ) -> Model:
        """Update model definition."""
        model = self.get_by_id(model_id)

        if name is not None:
            model.name = name
            # [NEW HOOK] Update all chats using this model
            self.chat_repo.update_model_name_for_model_id(model.id, name)
            self.chat_repo.commit()

        if model_identifier is not None:
            model.model_identifier = model_identifier
        if openrouter_identifier is not None:
            model.openrouter_identifier = openrouter_identifier
        if template_id is not None:
            model.template_id = template_id
        if enabled is not None:
            model.enabled = enabled

        if provider_id is not None and provider_id != model.provider_id:
            provider = self.provider_repo.find_by_id(provider_id)
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Provider with ID '{provider_id}' not found",
                )
            model.provider_id = provider_id

        target_family = model.model_family
        family_changed = False

        if model_family_id is not None and model_family_id != model.model_family_id:
            new_family = self.family_repo.find_by_id(model_family_id)
            if not new_family:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model Family with ID '{model_family_id}' not found",
                )
            target_family = new_family
            model.model_family_id = model_family_id
            family_changed = True

        # Re-validate the primary provider whenever the provider or family changes.
        if provider_id is not None or family_changed:
            eff_provider = self.provider_repo.find_by_id(model.provider_id)
            if (
                eff_provider
                and eff_provider.provider_type.value not in target_family.provider_types
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Provider '{eff_provider.name}' ({eff_provider.provider_type.value}) "
                        f"cannot serve model family '{target_family.name}'. "
                        f"Supported: {', '.join(target_family.provider_types) or 'none'}."
                    ),
                )

        new_use_openrouter = use_openrouter if use_openrouter is not None else model.use_openrouter
        new_or_id = (
            openrouter_identifier
            if openrouter_identifier is not None
            else model.openrouter_identifier
        )

        if use_openrouter is not None or family_changed or openrouter_identifier is not None:
            if new_use_openrouter:
                if "openrouter" not in target_family.provider_types:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Model family '{target_family.name}' does not support OpenRouter routing",
                    )
                if not new_or_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="OpenRouter identifier is required when use_openrouter is True",
                    )
            model.use_openrouter = new_use_openrouter

        target_parameters = model.parameters
        params_changed = False

        if parameters is not None:
            if parameters != model.parameters:
                target_parameters = parameters
                params_changed = True
            elif family_changed:
                target_parameters = parameters

        should_validate = False
        if family_changed or params_changed:
            should_validate = True

        if should_validate:
            if target_parameters == {}:
                self._validate_parameters(target_parameters, target_family)
                model.parameters = {}
                flag_modified(model, "parameters")
            else:
                self._validate_parameters(target_parameters, target_family)
                model.parameters = target_parameters
                flag_modified(model, "parameters")

        updated = self.model_repo.update(model)
        self.model_repo.commit()
        return updated

    def update_flags(
        self,
        model_id: str,
        enabled: bool | None = None,
        use_openrouter: bool | None = None,
    ) -> Model:
        """Update model flags with validation"""
        model = self.get_by_id(model_id)

        if enabled is not None:
            model.enabled = enabled

        if use_openrouter is not None:
            # A model can route via OpenRouter iff it has an OpenRouter identifier
            # (that presence is exactly what can_use_openrouter now reflects).
            if use_openrouter and not model.openrouter_identifier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenRouter identifier must be set before enabling OpenRouter routing",
                )
            model.use_openrouter = use_openrouter

        updated = self.model_repo.update(model)
        self.model_repo.commit()
        return updated

    def get_openrouter_provider(self) -> Provider:
        """Helper to get OpenRouter provider"""
        provider = self.provider_repo.find_by_type(ProviderType.OPENROUTER)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenRouter provider not configured in database",
            )
        return provider

    def delete(self, model_id: str) -> None:
        """Delete model definition"""
        model = self.get_by_id(model_id)

        self.model_repo.delete(model)
        self.model_repo.commit()
