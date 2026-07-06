"""Tests for fixtures service"""

from sqlalchemy.orm import Session
from src.fixtures.service import seed_database
from src.model_family.models import ModelFamily
from src.prompt_template.models import PromptTemplate
from src.provider.models import Provider


def test_seed_database(db: Session) -> None:
    """Test full database seeding"""
    # Verify initial state (empty for these tables in test DB usually,
    # unless conftest seeds them. conftest seeded_providers fixture is not used here yet)
    # The 'db' fixture gives a clean session but conftest creates tables.

    # Run seeding
    seed_database(db)

    # Verify Providers
    providers = db.query(Provider).all()
    assert len(providers) > 0
    # Check specific provider
    openai = db.query(Provider).filter(Provider.provider_type == "openai").first()
    assert openai is not None
    assert openai.name == "OpenAI"

    # Verify Model Families
    families = db.query(ModelFamily).all()
    assert len(families) > 0
    gpt4o = db.query(ModelFamily).filter(ModelFamily.name == "OpenAI GPT-4o").first()
    assert gpt4o is not None

    # Verify Prompt Templates
    templates = db.query(PromptTemplate).all()
    assert len(templates) > 0
    default_template = db.query(PromptTemplate).filter(PromptTemplate.is_default).first()
    assert default_template is not None
