"""Tests for health check endpoint."""

from fastapi.testclient import TestClient
from bootstrap.api import app


def test_health():
    """Return 200 with status ok from the health endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
