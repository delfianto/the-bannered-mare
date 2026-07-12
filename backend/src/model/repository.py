"""Data access layer for canonical models (registry) and their provider routes."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from src.core.persistence import BaseRepository
from src.model.models import ModelRegistry, ModelRoute


class ModelRepository(BaseRepository[ModelRegistry]):
    """Repository for canonical models (registry) + their routes."""

    def __init__(self, db: Session):
        super().__init__(db, ModelRegistry)

    # ── Registry ─────────────────────────────────────────────
    def find_paginated_with_count(
        self,
        limit: int = BaseRepository.DEFAULT_LIMIT,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelRegistry], int]:
        """Registries with pagination + filtering (name/family/enabled/has-route-on-provider)."""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        filters = dict(filters or {})
        # `provider_id` isn't a registry column — it means "has a route on this provider".
        provider_id = filters.pop("provider_id", None)
        # `name__ilike` targets the registry's display_name.
        name_ilike = filters.pop("name__ilike", None)

        stmt = select(ModelRegistry)
        if provider_id:
            stmt = stmt.where(ModelRegistry.routes.any(ModelRoute.provider_id == provider_id))
        if name_ilike:
            stmt = stmt.where(ModelRegistry.display_name.ilike(f"%{name_ilike}%"))
        stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = (
            stmt.options(
                joinedload(ModelRegistry.routes),
                joinedload(ModelRegistry.active_route).joinedload(ModelRoute.provider),
            )
            .order_by(func.lower(ModelRegistry.display_name), ModelRegistry.id)
            .limit(limit)
            .offset(offset)
        )
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def find_by_slug(self, slug: str) -> ModelRegistry | None:
        """Find a canonical model by its provider-independent slug."""
        stmt = select(ModelRegistry).where(ModelRegistry.slug == slug)
        return self.db.execute(stmt).scalars().first()

    def search_by_name(self, name: str) -> list[ModelRegistry]:
        """Search canonical models by display name (case-insensitive partial match)."""
        stmt = select(ModelRegistry).where(ModelRegistry.display_name.ilike(f"%{name}%"))
        return list(self.db.execute(stmt).scalars().all())

    # ── Routes ───────────────────────────────────────────────
    def find_route_by_id(self, route_id: str) -> ModelRoute | None:
        stmt = select(ModelRoute).where(ModelRoute.id == route_id)
        return self.db.execute(stmt).scalars().first()

    def find_route_by_provider_identifier(
        self, provider_id: str, model_identifier: str
    ) -> ModelRoute | None:
        """A route is globally unique by (provider, identifier)."""
        stmt = select(ModelRoute).where(
            ModelRoute.provider_id == provider_id,
            ModelRoute.model_identifier == model_identifier,
        )
        return self.db.execute(stmt).scalars().first()

    def find_route_by_registry_provider(
        self, model_registry_id: str, provider_id: str
    ) -> ModelRoute | None:
        """A model has at most one route per provider (uq_route_registry_provider)."""
        stmt = select(ModelRoute).where(
            ModelRoute.model_registry_id == model_registry_id,
            ModelRoute.provider_id == provider_id,
        )
        return self.db.execute(stmt).scalars().first()

    def add_route(self, route: ModelRoute) -> ModelRoute:
        self.db.add(route)
        self.db.flush()
        self.db.refresh(route)
        return route

    def delete_route(self, route: ModelRoute) -> None:
        self.db.delete(route)
        self.db.flush()
