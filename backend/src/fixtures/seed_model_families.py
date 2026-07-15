"""Script to seed model families into the database"""

from src.core.logging import get_logger
from src.core.persistence import SessionLocal
from src.core.utils.validators import validate_identifier
from src.fixtures.families import MODEL_FAMILIES_SEED_DATA
from src.model_family.models import ModelFamily
from src.model_family.repository import ModelFamilyRepository

logger = get_logger(__name__)


def seed_model_families(repo: ModelFamilyRepository) -> None:
    """
    Seed model families into the database using the repository.

    Args:
        repo: The model family repository instance.
    """
    logger.info("seeding_model_families")

    for family_data in MODEL_FAMILIES_SEED_DATA:
        # Validate identifier format
        try:
            validate_identifier(family_data["family_identifier"], "family_identifier")
        except ValueError as e:
            logger.error(
                "invalid_family_identifier",
                name=family_data["name"],
                identifier=family_data.get("family_identifier"),
                error=str(e),
            )
            continue

        existing = repo.find_by_identifier(family_data["family_identifier"])

        if existing:
            existing.name = family_data["name"]
            existing.description = family_data.get("description")
            existing.provider_types = family_data.get("provider_types", [])
            existing.parameters = family_data.get("parameters", {})
            existing.unsupported_parameters = family_data.get("unsupported_parameters", [])
            existing.extra_metadata = family_data.get("extra_metadata")
            repo.update(existing)
            logger.info(
                "model_family_updated",
                name=family_data["name"],
                identifier=family_data["family_identifier"],
            )
            continue

        family = ModelFamily(
            name=family_data["name"],
            family_identifier=family_data["family_identifier"],
            description=family_data.get("description"),
            provider_types=family_data.get("provider_types", []),
            parameters=family_data.get("parameters", {}),
            unsupported_parameters=family_data.get("unsupported_parameters", []),
            extra_metadata=family_data.get("extra_metadata"),
        )

        _ = repo.create(family)
        logger.info(
            "model_family_created",
            name=family_data["name"],
            identifier=family_data["family_identifier"],
        )

    repo.db.commit()
    logger.info("seeding_model_families_completed")


def main():
    """Main function to run seeding"""
    # Startup/CLI seeding runs outside the request/DI lifecycle, so it opens a
    # Session directly rather than receiving one via FastAPI Depends.
    db = SessionLocal()
    try:
        repo = ModelFamilyRepository(db)
        seed_model_families(repo)
    finally:
        db.close()


if __name__ == "__main__":
    main()
