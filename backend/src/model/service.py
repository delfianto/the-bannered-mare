"""Canonical-model (registry) + route business logic."""

from typing import TYPE_CHECKING, Any

from src.core.base_service import get_or_404
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.core.persistence import UnitOfWork
from src.model import parameter_validation
from src.model.lineage import normalize_slug, resolve_family
from src.model.models import ModelRegistry, ModelRoute
from src.model.repository import ModelRepository
from src.model_family.models import ModelFamily
from src.model_family.repository import ModelFamilyRepository

if TYPE_CHECKING:
    from src.chat_session.model_snapshot import ChatModelSnapshotService
    from src.provider.models import Provider
    from src.provider.repository import ProviderRepository


class ModelService:
    """Service for canonical-model + route business logic."""

    def __init__(
        self,
        model_repo: ModelRepository,
        provider_repo: ProviderRepository,
        family_repo: ModelFamilyRepository,
        chat_snapshot: ChatModelSnapshotService,
        uow: UnitOfWork | None = None,
    ):
        self.model_repo = model_repo
        self.provider_repo = provider_repo
        self.family_repo = family_repo
        self.chat_snapshot = chat_snapshot
        # The unit of work owns the transaction boundary; it wraps the same session
        # the repos share. Fallback keeps direct `ModelService(...)` construction
        # (tests) valid — the DI factory injects the request-scoped UoW.
        self.uow = uow or UnitOfWork(model_repo.db)

    def list_all(self) -> list[ModelRegistry]:
        """List all canonical models."""
        return self.model_repo.find_all()

    def list_paginated(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[ModelRegistry], int]:
        """List canonical models with pagination and filtering."""
        return self.model_repo.find_paginated_with_count(limit, offset, filters=filters)

    def get_by_id(self, model_id: str) -> ModelRegistry:
        """Get a canonical model by ID, raise 404 if not found."""
        return get_or_404(self.model_repo, model_id, "Model")

    # ── Validation ───────────────────────────────────────────
    def _get_family(self, model_family_id: str) -> ModelFamily:
        return get_or_404(self.family_repo, model_family_id, "Model family")

    def _validate_route(
        self, provider_id: str, model_identifier: str, family: ModelFamily
    ) -> Provider:
        """A route's provider must exist, be keyed, serve the family, and be unique."""
        provider = get_or_404(self.provider_repo, provider_id, "Provider")
        if not provider.has_api_key():
            raise ValidationError(
                f"Cannot add route: Provider '{provider.name}' requires "
                f"{provider.get_env_var_name()} environment variable."
            )
        if provider.provider_type.value not in family.provider_types:
            raise ValidationError(
                f"Provider '{provider.name}' ({provider.provider_type.value}) cannot serve "
                f"model family '{family.name}'. "
                f"Supported: {', '.join(family.provider_types) or 'none'}."
            )
        existing = self.model_repo.find_route_by_provider_identifier(provider_id, model_identifier)
        if existing:
            raise ConflictError(
                f"A route already exists for '{model_identifier}' on provider '{provider.name}'."
            )
        return provider

    # ── Registry CRUD ────────────────────────────────────────
    def create(
        self,
        display_name: str,
        model_family_id: str,
        routes: list[dict[str, Any]] | None = None,
        slug: str | None = None,
        original_identifier: str | None = None,
        template_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        enabled: bool = True,
        active_provider_id: str | None = None,
    ) -> ModelRegistry:
        """Create a canonical model plus its initial route(s)."""
        parameters = parameters or {}
        routes = routes or []

        family = self._get_family(model_family_id)
        parameter_validation.validate_parameters(parameters, family)

        # Derive identity from the first route when not given explicitly.
        first_identifier = routes[0]["model_identifier"] if routes else None
        if not original_identifier:
            original_identifier = first_identifier
        if not slug and first_identifier:
            slug = normalize_slug(first_identifier)
        if not slug:
            raise ValidationError("A slug or at least one route is required to create a model.")
        if not original_identifier:
            original_identifier = slug

        if self.model_repo.find_by_slug(slug):
            raise ConflictError(f"A model with slug '{slug}' already exists.")

        # Validate every route up front so we never half-create. A model has at
        # most one route per provider.
        seen_providers: set[str] = set()
        for route in routes:
            if route["provider_id"] in seen_providers:
                raise ValidationError("A model can have at most one route per provider.")
            seen_providers.add(route["provider_id"])
            self._validate_route(route["provider_id"], route["model_identifier"], family)

        registry = ModelRegistry(
            slug=slug,
            display_name=display_name,
            original_identifier=original_identifier,
            model_family_id=model_family_id,
            template_id=template_id,
            parameters=parameters,
            enabled=enabled,
        )
        registry = self.model_repo.create(registry)

        created_routes: list[ModelRoute] = []
        for route in routes:
            created_routes.append(
                self.model_repo.add_route(
                    ModelRoute(
                        model_registry_id=registry.id,
                        provider_id=route["provider_id"],
                        model_identifier=route["model_identifier"],
                        enabled=route.get("enabled", True),
                    )
                )
            )

        if created_routes:
            active = next(
                (r for r in created_routes if r.provider_id == active_provider_id),
                created_routes[0],
            )
            registry.active_route_id = active.id

        self.uow.commit()
        self.model_repo.refresh(registry)
        return registry

    def persist_discovered_model(self, provider_id: str, model_identifier: str) -> ModelRegistry:
        """Persist a discovered model: attach a route to the matching (or new) canonical model.

        If a route already exists for ``(provider, identifier)`` its canonical model is
        returned. Otherwise the identifier is matched to an existing canonical model by
        its provider-independent slug (adding this provider as a new route), or a new
        canonical model is created with a best-effort family guess — the user can correct
        the family/slug afterward.
        """
        # Already routed on this provider → return the owning canonical model.
        existing_route = self.model_repo.find_route_by_provider_identifier(
            provider_id, model_identifier
        )
        if existing_route:
            return self.get_by_id(existing_route.model_registry_id)

        # Same canonical model reached through another provider → add this route to it.
        slug = normalize_slug(model_identifier)
        registry = self.model_repo.find_by_slug(slug)
        if registry:
            return self.add_route(
                registry.id, provider_id=provider_id, model_identifier=model_identifier
            )

        # New canonical model: best-effort family match, else any configured family
        # (the user can correct it afterward).
        family = (
            resolve_family(self.family_repo.db, model_identifier) or self.family_repo.find_first()
        )
        if family is None:
            raise ConflictError(
                "Cannot persist a discovered model: no model families are configured."
            )
        friendly_name = (
            model_identifier.replace(":", " ").replace("-", " ").replace("/", " ").title()
        )
        return self.create(
            display_name=friendly_name,
            model_family_id=family.id,
            routes=[{"provider_id": provider_id, "model_identifier": model_identifier}],
            slug=slug,
            enabled=True,
        )

    def update(
        self,
        model_id: str,
        slug: str | None = None,
        display_name: str | None = None,
        original_identifier: str | None = None,
        model_family_id: str | None = None,
        template_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        enabled: bool | None = None,
    ) -> ModelRegistry:
        """Update canonical-model fields (routes are managed separately)."""
        model = self.get_by_id(model_id)

        # Validate EVERYTHING up front, before mutating anything, so a rejected
        # update never leaves a partial write. (Previously the display_name change
        # — plus the cross-domain chat rename — was committed before the slug /
        # family / parameter checks ran, so a later failure persisted the rename.)
        target_family = model.model_family
        family_changed = False
        if model_family_id is not None and model_family_id != model.model_family_id:
            target_family = self._get_family(model_family_id)
            family_changed = True

        if slug is not None and slug != model.slug and self.model_repo.find_by_slug(slug):
            raise ConflictError(f"A model with slug '{slug}' already exists.")

        # A family change can invalidate existing routes (provider no longer supported).
        if family_changed:
            for route in model.routes:
                if route.provider.provider_type.value not in target_family.provider_types:
                    raise ValidationError(
                        f"Route via '{route.provider.name}' "
                        f"({route.provider.provider_type.value}) is incompatible with family "
                        f"'{target_family.name}'. Remove it before changing family."
                    )

        new_parameters: dict[str, Any] | None = None
        if parameters is not None and (parameters != model.parameters or family_changed):
            parameter_validation.validate_parameters(parameters, target_family)
            new_parameters = parameters

        # All validation passed — now mutate and commit once (the shared session
        # covers the chat rename too).
        if display_name is not None:
            model.display_name = display_name
            # The chat domain owns its denormalized model_name snapshot; ask it to
            # refresh (shares this session, so the single commit below stays atomic).
            self.chat_snapshot.refresh_model_name(model.id, display_name)
        if slug is not None:
            model.slug = slug
        if original_identifier is not None:
            model.original_identifier = original_identifier
        if template_id is not None:
            model.template_id = template_id
        if enabled is not None:
            model.enabled = enabled
        if family_changed and model_family_id is not None:
            model.model_family_id = model_family_id
        if new_parameters is not None:
            # parameters is a MutableDict, so reassignment (and in-place mutation)
            # is tracked automatically — no flag_modified needed.
            model.parameters = new_parameters

        updated = self.model_repo.update(model)
        self.uow.commit()
        return updated

    def update_flags(self, model_id: str, enabled: bool | None = None) -> ModelRegistry:
        """Toggle the canonical model's enabled flag."""
        model = self.get_by_id(model_id)
        if enabled is not None:
            model.enabled = enabled
        updated = self.model_repo.update(model)
        self.uow.commit()
        return updated

    def delete(self, model_id: str) -> None:
        """Delete a canonical model (cascades to its routes)."""
        model = self.get_by_id(model_id)
        self.model_repo.delete(model)
        self.uow.commit()

    # ── Route management ─────────────────────────────────────
    def add_route(
        self, model_id: str, provider_id: str, model_identifier: str, enabled: bool = True
    ) -> ModelRegistry:
        """Add a provider route; make it active if the model had none."""
        model = self.get_by_id(model_id)
        if self.model_repo.find_route_by_registry_provider(model.id, provider_id):
            raise ConflictError("This model already has a route on that provider.")
        self._validate_route(provider_id, model_identifier, model.model_family)

        route = self.model_repo.add_route(
            ModelRoute(
                model_registry_id=model.id,
                provider_id=provider_id,
                model_identifier=model_identifier,
                enabled=enabled,
            )
        )
        if model.active_route_id is None:
            model.active_route_id = route.id

        self.uow.commit()
        self.model_repo.refresh(model)
        return model

    def delete_route(self, model_id: str, route_id: str) -> ModelRegistry:
        """Remove a route; repoint the active route if it was the one removed."""
        model = self.get_by_id(model_id)
        route = self.model_repo.find_route_by_id(route_id)
        if not route or route.model_registry_id != model.id:
            raise NotFoundError(f"Route '{route_id}' not found for this model.")

        if model.active_route_id == route.id:
            remaining = [r for r in model.routes if r.id != route.id]
            model.active_route_id = remaining[0].id if remaining else None
            self.model_repo.update(model)

        self.model_repo.delete_route(route)
        self.uow.commit()
        self.model_repo.refresh(model)
        return model

    def set_active_route(self, model_id: str, route_id: str) -> ModelRegistry:
        """Flip which route the model resolves to (redirects every chat using it)."""
        model = self.get_by_id(model_id)
        route = self.model_repo.find_route_by_id(route_id)
        if not route or route.model_registry_id != model.id:
            raise NotFoundError(f"Route '{route_id}' not found for this model.")
        model.active_route_id = route.id
        self.model_repo.update(model)
        self.uow.commit()
        self.model_repo.refresh(model)
        return model
