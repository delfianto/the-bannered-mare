"""Service for database seeding and fixture management"""

from sqlalchemy.orm import Session

from src.core.logging import get_logger
from src.fixtures.seed_model_families import seed_model_families
from src.fixtures.seed_models import seed_models
from src.fixtures.seed_prompt_templates import seed_prompt_templates
from src.fixtures.seed_providers import seed_providers
from src.model.repository import ModelRepository
from src.model_family.repository import ModelFamilyRepository
from src.prompt_template.repository import PromptTemplateRepository
from src.provider.repository import ProviderRepository

logger = get_logger(__name__)


class FixtureService:
    """Service to handle database seeding and fixture management"""

    def __init__(self, db: Session):
        self.db = db
        self.provider_repo = ProviderRepository(db)
        self.family_repo = ModelFamilyRepository(db)
        self.template_repo = PromptTemplateRepository(db)
        self.model_repo = ModelRepository(db)

    def seed_database(self) -> None:
        """Seed the database with all default data"""
        logger.info("starting_database_seeding")

        # Seed Providers
        seed_providers(self.provider_repo)

        # Seed Model Families
        seed_model_families(self.family_repo)

        # Seed Models
        seed_models(self.model_repo, self.family_repo, self.provider_repo)

        # Seed Prompt Templates
        seed_prompt_templates(self.template_repo)

        logger.info("database_seeding_completed")
        self._log_provider_status()

    def _log_provider_status(self) -> None:
        """Log the configuration status of providers"""
        providers = self.provider_repo.find_all()
        for p in providers:
            env_var = p.get_env_var_name() or "none"
            logger.info(
                "provider_status",
                provider=p.name,
                configured=p.has_api_key(),
                env_var=env_var,
            )


def seed_database(db: Session | None = None) -> None:
    """
    Helper function to seed database using the service.

    Handles session creation if not provided and suppresses exceptions
    to prevent application startup failure.
    """
    should_close = False
    if db is None:
        from src.core.persistence import SessionLocal

        db = SessionLocal()
        should_close = True

    try:
        service = FixtureService(db)
        service.seed_database()
    except Exception as e:
        logger.error("seeding_failed", error=str(e))
        logger.warning(
            "seeding_failed_warning",
            message="Database seeding failed. Application data might be incomplete.",
        )
    finally:
        if should_close:
            db.close()
