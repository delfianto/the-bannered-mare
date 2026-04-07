"""Tests for admin router"""

from fastapi.testclient import TestClient


def test_admin_llm_stats(client: TestClient) -> None:
    """Test admin LLM stats endpoint (basic check)"""
    # Note: this will return 503 if mongo not initialized in test,
    # but we just want to see if the route exists or how it handles it.
    response = client.get("/admin/logs/llm/stats")
    assert response.status_code in [200, 503]
