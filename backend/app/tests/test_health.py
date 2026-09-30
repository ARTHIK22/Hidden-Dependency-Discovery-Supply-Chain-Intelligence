# backend/app/tests/test_health.py

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["message"] == "Hidden Dependency Intelligence API"


def test_health():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is (data["database"] == "connected")
    assert data["status"] in {"healthy", "degraded"}
    assert data["database"] in {"connected", "unavailable"}
    assert data["redis"] in {"available", "unavailable"}
