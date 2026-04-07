"""Script to seed default providers into the database"""

from src.core.logging import get_logger
from src.core.persistence import SessionLocal
from src.provider.models import PROVIDER_CONFIGS, Provider, ProviderType
from src.provider.repository import ProviderRepository

logger = get_logger(__name__)


def seed_providers(repo: ProviderRepository) -> None:
    """
    Seed default providers into the database using the repository.

    Args:
        repo: The provider repository instance.
    """
    logger.info("seeding_providers")
    for provider_type, config in PROVIDER_CONFIGS.items():
        if provider_type == ProviderType.CUSTOM:
            continue

        existing = repo.find_by_type(provider_type)

        if not existing:
            provider = Provider(
                name=config.display_name,
                provider_type=provider_type,
                base_url=config.default_base_url,
                api_key_env_var=config.env_var_name,
                enabled=True,
            )
            # Create method in BaseRepository usually adds to session
            _ = repo.create(provider)
            logger.info("provider_created", name=config.display_name)
        else:
            # Update existing provider
            existing.base_url = config.default_base_url
            existing.api_key_env_var = config.env_var_name
            repo.update(existing)
            logger.info("provider_updated", name=config.display_name)

    repo.commit()
    logger.info("seeding_providers_completed")


def main():
    """Main function to run seeding"""
    db = SessionLocal()
    try:
        repo = ProviderRepository(db)
        seed_providers(repo)
    finally:
        db.close()


if __name__ == "__main__":
    main()
