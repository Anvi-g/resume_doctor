"""
Unit Tests for Gateway API endpoints.
"""
from fastapi.testclient import TestClient
from src.backend.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
