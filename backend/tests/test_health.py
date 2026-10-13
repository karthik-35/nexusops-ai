
from fastapi.testclient import TestClient
from app.main import app

# Create a test client for our FastAPI application
client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "nexusops-ai"
    }


def test_unknown_endpoint():
    response = client.get("/api/v1/unknown")

    assert response.status_code == 404
