"""Seed canonical models (registry) + provider routes, with env-flag controls.

Each per-provider seed entry is folded into a canonical model keyed by its
provider-independent slug (``normalize_slug``): the first provider to introduce a
slug creates the registry and its route becomes active; later providers with the
same slug just add another route. This is how one model ends up reachable through
several providers.
"""

import os

from src.core.logging import get_logger
from src.core.persistence import SessionLocal
from src.core.utils.validators import validate_identifier
from src.fixtures.models import ALL_MODELS
from src.model.lineage import normalize_slug
from src.model.models import ModelRegistry, ModelRoute
from src.model.repository import ModelRepository
from src.model_family.repository import ModelFamilyRepository
from src.provider.repository import ProviderRepository

logger = get_logger(__name__)


def str_to_bool(value: str) -> bool:
    """Convert string env var to bool"""
    return value.lower() in ("true", "1", "yes", "on")


def should_seed_provider(provider_type: str) -> bool:
    """Check if seeding is enabled for provider via env var"""
    env_var = f"SEED_MODELS_{provider_type.upper()}"
    return str_to_bool(os.getenv(env_var, "false"))


def seed_models(
    model_repo: ModelRepository,
    family_repo: ModelFamilyRepository,
    provider_repo: ProviderRepository,
) -> None:
    """Seed canonical models + routes based on env flag configuration."""
    if not str_to_bool(os.getenv("SEED_MODELS", "false")):
        logger.info("model_seeding_disabled_globally")
        return

    if model_repo.count() > 0:
        logger.warning(
            "model_seeding_skipped",
            message="Model registry is not empty. Skipping seeding.",
        )
        return

    logger.info("seeding_models_started")

    for provider_type, models in ALL_MODELS.items():
        if not should_seed_provider(provider_type):
            logger.info(
                "seeding_skipped_for_provider",
                provider=provider_type,
                env_var=f"SEED_MODELS_{provider_type.upper()}",
            )
            continue

        provider = provider_repo.find_by_type(provider_type)
        if not provider:
            logger.error("provider_not_found", provider_type=provider_type)
            continue

        logger.info("seeding_provider_models", provider=provider_type, count=len(models))

        for model_data in models:
            try:
                validate_identifier(model_data["model_identifier"], "model_identifier")
                validate_identifier(model_data["family_identifier"], "family_identifier")
            except ValueError as e:
                logger.error("invalid_identifier", model_name=model_data["name"], error=str(e))
                continue

            family = family_repo.find_by_identifier(model_data["family_identifier"])
            if not family:
                logger.error(
                    "model_family_not_found",
                    identifier=model_data["family_identifier"],
                    model_name=model_data["name"],
                )
                continue

            identifier = model_data["model_identifier"]
            # Alternate-provider routes declare the canonical slug explicitly so
            # they merge with the native registry despite naming divergence.
            slug = model_data.get("slug") or normalize_slug(identifier)

            # Canonical model: create on first sight of this slug.
            registry = model_repo.find_by_slug(slug)
            if not registry:
                registry = model_repo.create(
                    ModelRegistry(
                        slug=slug,
                        display_name=model_data["name"],
                        original_identifier=identifier,
                        model_family_id=family.id,
                        parameters=model_data["parameters"],
                        enabled=model_data["enabled"],
                    )
                )
                logger.info("model_registry_created", slug=slug)

            # A model has at most one route per provider — skip provider-variant
            # dupes (e.g. `kimi-k2.6` and `kimi-k2.6:free` collapse to one slug).
            if model_repo.find_route_by_registry_provider(registry.id, provider.id):
                logger.info("model_route_skipped_provider_dup", slug=slug, provider=provider_type)
                continue

            # Route: one per (provider, identifier).
            route = model_repo.find_route_by_provider_identifier(provider.id, identifier)
            if not route:
                route = model_repo.add_route(
                    ModelRoute(
                        model_registry_id=registry.id,
                        provider_id=provider.id,
                        model_identifier=identifier,
                        enabled=model_data["enabled"],
                    )
                )
                logger.info("model_route_created", provider=provider_type, identifier=identifier)

            if registry.active_route_id is None:
                registry.active_route_id = route.id

        model_repo.db.commit()

    logger.info("seeding_models_completed")


def main():
    """Main function to run model seeding"""
    db = SessionLocal()
    try:
        model_repo = ModelRepository(db)
        family_repo = ModelFamilyRepository(db)
        provider_repo = ProviderRepository(db)
        seed_models(model_repo, family_repo, provider_repo)
    finally:
        db.close()


if __name__ == "__main__":
    main()
