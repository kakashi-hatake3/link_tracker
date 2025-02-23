from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)


def test_api_ping():
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": "ok"}
