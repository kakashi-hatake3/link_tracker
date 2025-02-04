from fastapi import status
from starlette.testclient import TestClient


def test_api_ping(
    test_client: TestClient,
) -> None:
    response = test_client.get("/api/v1/ping")
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert "pong" in response_json
    assert response_json["pong"] == "ok"
