"""Unit tests for ModelFamilyRepository"""

import pytest
from sqlalchemy.orm import Session
from src.model_family.models import ModelFamily
from src.model_family.repository import ModelFamilyRepository


@pytest.fixture
def family_repo(db_session: Session) -> ModelFamilyRepository:
    """Fixture for ModelFamilyRepository"""
    return ModelFamilyRepository(db_session)


def test_search_by_name_exact_match(family_repo: ModelFamilyRepository, db_session: Session):
    """Test search_by_name with exact match"""
    # Create test model families
    family1 = ModelFamily(
        name="GPT-4",
        family_identifier="gpt-4",
        description="GPT-4 family",
        provider_types=["openai"],
        parameters={},
    )
    family2 = ModelFamily(
        name="Claude 3",
        family_identifier="claude-3",
        description="Claude 3 family",
        provider_types=["anthropic"],
        parameters={},
    )
    family_repo.create(family1)
    family_repo.create(family2)
    family_repo.db.commit()

    # Search for exact match
    results = family_repo.search_by_name("GPT-4")
    assert len(results) == 1
    assert results[0].name == "GPT-4"


def test_search_by_name_partial_match(family_repo: ModelFamilyRepository, db_session: Session):
    """Test search_by_name with partial match"""
    # Create test model families
    family1 = ModelFamily(
        name="GPT-4",
        family_identifier="gpt-4",
        description="GPT-4 family",
        provider_types=["openai"],
        parameters={},
    )
    family2 = ModelFamily(
        name="GPT-3.5",
        family_identifier="gpt-3.5",
        description="GPT-3.5 family",
        provider_types=["openai"],
        parameters={},
    )
    family3 = ModelFamily(
        name="Claude 3",
        family_identifier="claude-3",
        description="Claude 3 family",
        provider_types=["anthropic"],
        parameters={},
    )
    family_repo.create(family1)
    family_repo.create(family2)
    family_repo.create(family3)
    family_repo.db.commit()

    # Search for partial match
    results = family_repo.search_by_name("GPT")
    assert len(results) == 2
    names = [f.name for f in results]
    assert "GPT-4" in names
    assert "GPT-3.5" in names


def test_search_by_name_case_insensitive(family_repo: ModelFamilyRepository, db_session: Session):
    """Test search_by_name with case-insensitive match"""
    # Create test model families
    family1 = ModelFamily(
        name="GPT-4",
        family_identifier="gpt-4",
        description="GPT-4 family",
        provider_types=["openai"],
        parameters={},
    )
    family_repo.create(family1)
    family_repo.db.commit()

    # Search for match with different case
    results = family_repo.search_by_name("gpt")
    assert len(results) == 1
    assert results[0].name == "GPT-4"


def test_search_by_name_no_match(family_repo: ModelFamilyRepository, db_session: Session):
    """Test search_by_name with no match"""
    # Create test model families
    family1 = ModelFamily(
        name="GPT-4",
        family_identifier="gpt-4",
        description="GPT-4 family",
        provider_types=["openai"],
        parameters={},
    )
    family_repo.create(family1)
    family_repo.db.commit()

    # Search for non-existent name
    results = family_repo.search_by_name("NonExistent")
    assert len(results) == 0
