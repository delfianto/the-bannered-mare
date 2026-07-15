"""Isolated tests for the sync ``ModelRepository``.

Focus: the eager-load option set on ``find_paginated_with_count`` (the registry
listing). A dropped ``joinedload`` there would silently turn the list endpoint
into an N+1, or — behind the async session — a ``MissingGreenlet``. These pin the
loaded relations so that regression is caught at the repository layer.
"""

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from src.model import ModelRegistry, ModelRepository
from src.provider import ProviderType


def test_find_paginated_with_count_eager_loads_routes_and_active_provider(
    db: Session, sample_model: ModelRegistry
):
    """``routes`` and ``active_route -> provider`` come back eagerly loaded."""
    repo = ModelRepository(db)

    items, total = repo.find_paginated_with_count()

    assert total == 1
    (registry,) = items

    # Detach everything so a *missing* joinedload would surface as a
    # DetachedInstanceError on access instead of a silent lazy SELECT — proving
    # the relations were populated by the query itself.
    db.expunge_all()

    assert "routes" not in inspect(registry).unloaded
    assert "active_route" not in inspect(registry).unloaded
    assert len(registry.routes) == 1

    route = registry.active_route
    assert route is not None
    assert "provider" not in inspect(route).unloaded
    assert route.provider.provider_type == ProviderType.OPENAI


def test_find_paginated_with_count_filter_by_provider(db: Session, sample_model: ModelRegistry):
    """The ``provider_id`` filter matches on 'has a route on this provider'."""
    repo = ModelRepository(db)
    active_route = sample_model.active_route
    assert active_route is not None
    provider_id = active_route.provider_id

    matched, total = repo.find_paginated_with_count(filters={"provider_id": provider_id})
    assert total == 1
    assert [r.id for r in matched] == [sample_model.id]

    none, none_total = repo.find_paginated_with_count(filters={"provider_id": "does-not-exist"})
    assert none_total == 0
    assert none == []
