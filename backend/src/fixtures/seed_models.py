"""Script to seed models into the database with env flag controls"""

import os

from src.core.logging import get_logger
from src.core.persistence import SessionLocal
from src.core.utils.validators import validate_identifier
from src.fixtures.models import ALL_MODELS
from src.model.models import Model
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
    """Seed models based on env flag configuration"""

    # Check if seeding is enabled globally
    if not str_to_bool(os.getenv("SEED_MODELS", "false")):
        logger.info("model_seeding_disabled_globally")
        return

    # Check if table is empty
    if model_repo.count() > 0:
        logger.warning(
            "model_seeding_skipped",
            message="Models table is not empty. Skipping seeding.",
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

        logger.info("seeding_provider_models", provider=provider_type, count=len(models))

        # Get provider
        provider = provider_repo.find_by_type(provider_type)
        if not provider:
            logger.error("provider_not_found", provider_type=provider_type)
            continue

        for model_data in models:
            # Validate identifiers
            try:
                validate_identifier(model_data["model_identifier"], "model_identifier")
                validate_identifier(model_data["family_identifier"], "family_identifier")
            except ValueError as e:
                logger.error(
                    "invalid_identifier",
                    model_name=model_data["name"],
                    error=str(e),
                )
                continue

            # Get family by identifier
            family = family_repo.find_by_identifier(model_data["family_identifier"])
            if not family:
                logger.error(
                    "model_family_not_found",
                    identifier=model_data["family_identifier"],
                    model_name=model_data["name"],
                )
                continue

            # Check if model exists
            existing = model_repo.find_by_identifier(provider.id, model_data["model_identifier"])

            if existing:
                # Update existing model
                existing.name = model_data["name"]
                existing.parameters = model_data["parameters"]
                existing.enabled = model_data["enabled"]
                existing.model_family_id = family.id
                model_repo.update(existing)
                logger.info("model_updated", identifier=model_data["model_identifier"])
            else:
                # Create new model
                model = Model(
                    provider_id=provider.id,
                    model_family_id=family.id,
                    name=model_data["name"],
                    model_identifier=model_data["model_identifier"],
                    parameters=model_data["parameters"],
                    enabled=model_data["enabled"],
                )
                model_repo.create(model)
                logger.info("model_created", identifier=model_data["model_identifier"])

        model_repo.commit()

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
