"""The SQLite test client must never seed the configured application database."""

import pytest
from pytest_mock import MockerFixture


def test_client_startup_does_not_open_global_session(
    request: pytest.FixtureRequest, mocker: MockerFixture
) -> None:
    session_factory = mocker.patch(
        "src.core.persistence.SessionLocal",
        side_effect=AssertionError("Test startup opened the configured database"),
    )

    client = request.getfixturevalue("client")
    response = client.get("/api/providers")

    assert response.status_code == 200
    assert response.json()["items"] == []
    session_factory.assert_not_called()
