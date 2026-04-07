"""Script to seed prompt templates into the database"""

from src.core.logging import get_logger
from src.core.persistence import SessionLocal
from src.fixtures.prompt_templates import PROMPT_TEMPLATES_SEED_DATA
from src.prompt_template.models import PromptTemplate
from src.prompt_template.repository import PromptTemplateRepository

logger = get_logger(__name__)


def seed_prompt_templates(repo: PromptTemplateRepository) -> None:
    """
    Seed prompt templates into the database using the repository.

    Args:
        repo: The prompt template repository instance.
    """
    logger.info("seeding_prompt_templates")

    for template_data in PROMPT_TEMPLATES_SEED_DATA:
        # Check if template already exists
        existing = repo.find_by_name(template_data["name"])

        if existing:
            logger.info(
                "prompt_template_skipped", name=template_data["name"], reason="already_exists"
            )
            continue

        # Create new prompt template
        template = PromptTemplate(**template_data)
        _ = repo.create(template)
        logger.info("prompt_template_created", name=template_data["name"])

    repo.commit()
    logger.info("seeding_prompt_templates_completed")


def main():
    """Main function to run seeding"""
    db = SessionLocal()
    try:
        repo = PromptTemplateRepository(db)
        seed_prompt_templates(repo)
    finally:
        db.close()


if __name__ == "__main__":
    main()
