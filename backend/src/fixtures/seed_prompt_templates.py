"""Script to seed prompt templates into the database"""

from sqlalchemy import select

from src.core.logging import get_logger
from src.core.persistence import PromptFragment, SessionLocal, TemplateFragment
from src.fixtures.prompt_templates import PROMPT_TEMPLATES_SEED_DATA
from src.prompt_template.models import PromptTemplate
from src.prompt_template.repository import PromptTemplateRepository

logger = get_logger(__name__)

_DRIFT_REMINDER_NAME = "Stay in Character (drift reminder)"
_DRIFT_REMINDER_CONTENT = (
    "[Reminder: stay fully in character as {{char}}. Hold the established tone, tense, and "
    "POV. Do not speak or act for {{user}}, and do not break character or add "
    "out-of-character / meta commentary.]"
)


def seed_prompt_templates(repo: PromptTemplateRepository) -> None:
    """
    Seed prompt templates into the database using the repository.

    Args:
        repo: The prompt template repository instance.
    """
    logger.info("seeding_prompt_templates")

    for template_data in PROMPT_TEMPLATES_SEED_DATA:
        existing = repo.find_by_name(template_data["name"])

        if existing:
            logger.info(
                "prompt_template_skipped", name=template_data["name"], reason="already_exists"
            )
            continue

        template = PromptTemplate(**template_data)
        _ = repo.create(template)
        logger.info("prompt_template_created", name=template_data["name"])

    repo.db.commit()

    _seed_drift_reminder(repo)

    logger.info("seeding_prompt_templates_completed")


def _seed_drift_reminder(repo: PromptTemplateRepository) -> None:
    """Seed a global at-depth drift-prevention reminder linked to the default template.

    Demonstrates the at_depth fragment mechanism: a short in-character reminder spliced
    into the chat history near the generation point to counter long-chat drift.
    """
    default = repo.find_default()
    if not default:
        logger.info("drift_reminder_skipped", reason="no_default_template")
        return

    db = repo.db
    fragment = (
        db.execute(select(PromptFragment).where(PromptFragment.name == _DRIFT_REMINDER_NAME))
        .scalars()
        .first()
    )
    if not fragment:
        fragment = PromptFragment(
            name=_DRIFT_REMINDER_NAME,
            description="Depth-injected reminder countering character/format drift in long chats.",
            fragment_type="instruction",
            content=_DRIFT_REMINDER_CONTENT,
            is_global=True,
        )
        db.add(fragment)
        db.flush()
        logger.info("prompt_fragment_created", name=_DRIFT_REMINDER_NAME)

    link = (
        db.execute(
            select(TemplateFragment).where(
                TemplateFragment.template_id == default.id,
                TemplateFragment.fragment_id == fragment.id,
            )
        )
        .scalars()
        .first()
    )
    if not link:
        db.add(
            TemplateFragment(
                template_id=default.id,
                fragment_id=fragment.id,
                position="at_depth",
                depth=3,
            )
        )
        logger.info("template_fragment_linked", template=default.name, position="at_depth", depth=3)

    repo.db.commit()


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
