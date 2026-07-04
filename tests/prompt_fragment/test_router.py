"""Tests for the prompt fragment router"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.persistence import PromptFragment, PromptTemplate
from src.prompt_fragment.models import TemplateFragment
from src.prompt_fragment.repository import TemplateFragmentRepository


def test_list_fragments_paginated(client: TestClient, db: Session) -> None:
    for i in range(3):
        db.add(PromptFragment(name=f"Frag {i}", content=f"content {i}"))
    db.commit()

    response = client.get("/api/prompt-fragments/", params={"limit": 2, "page": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["meta"]["total"] == 3
    assert data["meta"]["has_more"] is True


def test_list_fragments_used_by(client: TestClient, db: Session) -> None:
    template = PromptTemplate(name="Uses It", system_template="x")
    fragment = PromptFragment(name="Attached", content="y")
    db.add_all([template, fragment])
    db.commit()
    db.refresh(template)
    db.refresh(fragment)

    TemplateFragmentRepository(db).create(
        TemplateFragment(template_id=template.id, fragment_id=fragment.id)
    )
    db.commit()

    response = client.get("/api/prompt-fragments/")
    assert response.status_code == 200
    items = response.json()["items"]
    found = next(f for f in items if f["id"] == fragment.id)
    assert found["used_by"] == [{"id": template.id, "name": "Uses It"}]


def test_list_fragments_unused_only(client: TestClient, db: Session) -> None:
    db.add_all(
        [
            PromptFragment(name="Orphan", content="a"),
            PromptFragment(name="Global", content="b", is_global=True),
        ]
    )
    db.commit()

    response = client.get("/api/prompt-fragments/", params={"unused_only": True})
    assert response.status_code == 200
    names = {f["name"] for f in response.json()["items"]}
    assert names == {"Orphan", "Global"}
