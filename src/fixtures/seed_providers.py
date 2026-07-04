"""Script to seed default providers into the database"""

from src.core.config import settings
from src.core.logging import get_logger
from src.core.persistence import SessionLocal
from src.provider.models import PROVIDER_CONFIGS, Provider, ProviderConfig, ProviderType
from src.provider.repository import ProviderRepository

logger = get_logger(__name__)


def _initial_base_url(provider_type: ProviderType, config: ProviderConfig) -> str:
    """Base URL to seed a provider with on first creation.

    OLLAMA_HOST/LMSTUDIO_HOST let a user point at a non-default (e.g. remote)
    instance without having to edit it in the UI after every fresh seed.
    """
    if provider_type == ProviderType.OLLAMA and settings.ollama_host:
        return settings.ollama_host
    if provider_type == ProviderType.LMSTUDIO and settings.lmstudio_host:
        return settings.lmstudio_host
    return config.default_base_url


def seed_providers(repo: ProviderRepository) -> None:
    """
    Seed default providers into the database using the repository.

    Only creates missing providers — never overwrites an existing row's
    base_url/api_key_env_var, since that would silently reset a user's
    customized host (e.g. a remote Ollama/LM Studio instance) on every
    application restart.

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
                base_url=_initial_base_url(provider_type, config),
                api_key_env_var=config.env_var_name,
                enabled=True,
            )
            # Create method in BaseRepository usually adds to session
            _ = repo.create(provider)
            logger.info("provider_created", name=config.display_name)

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
