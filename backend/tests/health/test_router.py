"""Tests for the health check API endpoint"""

from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.persistence import get_db
from src.main import app

client = TestClient(app)


def test_health_check_healthy_db(db: Session) -> None:
    """Test health check when DB connection is healthy"""

    app.dependency_overrides[get_db] = lambda: db
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "ok"
    assert data["storage"] == "ok"

    # Clean up
    app.dependency_overrides = {}


def test_health_check_unhealthy_db() -> None:
    """Test health check when DB connection is down"""
    mock_db = Mock()
    mock_db.execute.side_effect = Exception("Connection error")

    app.dependency_overrides[get_db] = lambda: mock_db
    response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "error"

    # Clean up
    app.dependency_overrides = {}
