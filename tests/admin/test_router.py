"""Smoke tests for the admin log-query router (PostgreSQL-backed)"""

from fastapi.testclient import TestClient


def test_admin_llm_stats_empty(client: TestClient) -> None:
    """Stats endpoint returns 200 with empty stats when no logs exist"""
    response = client.get("/admin/logs/llm/stats")
    assert response.status_code == 200
    assert response.json()["stats"] == []


def test_admin_llm_logs_empty(client: TestClient) -> None:
    """LLM logs endpoint returns an empty page"""
    response = client.get("/admin/logs/llm")
    assert response.status_code == 200
    body = response.json()
    assert body["logs"] == []
    assert body["total"] == 0


def test_admin_http_logs(client: TestClient) -> None:
    """HTTP logs endpoint returns a page envelope"""
    response = client.get("/admin/logs/http")
    assert response.status_code == 200
    assert "logs" in response.json()


def test_admin_errors_empty(client: TestClient) -> None:
    """Error logs endpoint returns an empty page"""
    response = client.get("/admin/logs/errors")
    assert response.status_code == 200
    assert response.json()["total"] == 0
