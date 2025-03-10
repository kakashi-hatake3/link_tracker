from typing import NoReturn

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from src.scrapper.api import router
from src.scrapper.storage import ScrapperStorage


@pytest.fixture(scope="function")
def postgres_container_api() -> str:
    with PostgresContainer("postgres:14") as postgres:
        # Получаем URL подключения, заменяем префикс для использования psycopg3 с SQLAlchemy
        db_url = postgres.get_connection_url(driver="psycopg").replace("postgresql://", "postgresql+psycopg://", 1)
        yield db_url


@pytest.fixture
def app(postgres_container_api) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.storage = ScrapperStorage(postgres_container_api)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_register_chat(client: TestClient) -> None:
    response = client.post("/tg-chat/1")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    storage: ScrapperStorage = client.app.state.storage
    chat = storage.get_chat(1)
    assert chat is not None
    assert chat.chat_id == 1


def test_remove_chat_success(client: TestClient) -> None:
    client.post("/tg-chat/1")

    response = client.delete("/tg-chat/1")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    storage: ScrapperStorage = client.app.state.storage
    assert storage.get_chat(1) is None


def test_remove_chat_not_found(client: TestClient) -> None:
    response = client.delete("/tg-chat/999")
    assert response.status_code == 404
    error = response.json()
    assert error["detail"]["description"] == "Чат не найден"
    assert error["detail"]["code"] == "CHAT_NOT_FOUND"


def test_get_links_empty(client: TestClient) -> None:
    client.post("/tg-chat/1")
    headers = {"Tg-Chat-Id": "1"}

    response = client.get("/links", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["size"] == 0
    assert data["links"] == []


def test_add_link_success_and_duplicate(client: TestClient) -> None:
    client.post("/tg-chat/1")
    headers = {"Tg-Chat-Id": "1"}

    link_request = {"link": "https://example.com", "tags": ["tag1", "tag2"], "filters": ["filter1"]}

    response = client.post("/links", json=link_request, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com/"
    assert data["tags"] == ["tag1", "tag2"]
    assert data["filters"] == ["filter1"]
    assert "id" in data

    duplicate_response = client.post("/links", json=link_request, headers=headers)
    assert duplicate_response.status_code == 400
    error = duplicate_response.json()
    assert error["detail"]["description"] == "Ссылка уже отслеживается"
    assert error["detail"]["code"] == "LINK_ALREADY_EXISTS"


def test_remove_link_success_and_not_found(client: TestClient) -> None:
    client.post("/tg-chat/1")
    headers = {"Tg-Chat-Id": "1"}

    link_request = {"link": "https://example.com", "tags": ["tag1"], "filters": []}
    add_response = client.post("/links", json=link_request, headers=headers)
    assert add_response.status_code == 200

    remove_request = {"link": "https://example.com"}
    remove_response = client.request("DELETE", "/links", json=remove_request, headers=headers)
    assert remove_response.status_code == 200
    removed_data = remove_response.json()
    assert removed_data["url"] == "https://example.com/"

    remove_again = client.request("DELETE", "/links", json=remove_request, headers=headers)
    assert remove_again.status_code == 404
    error = remove_again.json()
    assert error["detail"]["description"] == "Ссылка не найдена"
    assert error["detail"]["code"] == "LINK_NOT_FOUND"


def test_register_chat_exception(client: TestClient, monkeypatch) -> None:
    def raise_exception(chat_id: int) -> NoReturn:
        raise Exception("Test error")

    client.app.state.storage.add_chat = raise_exception

    response = client.post("/tg-chat/1")
    assert response.status_code == 400
    error = response.json()
    detail = error["detail"]
    assert detail["description"] == "Ошибка при регистрации чата"
    assert detail["code"] == "CHAT_REGISTRATION_ERROR"
    assert detail["exception_name"] == "Exception"
    assert "Test error" in detail["exception_message"]


def test_remove_chat_exception(client: TestClient, monkeypatch) -> None:
    def raise_exception(chat_id: int) -> NoReturn:
        raise Exception("Test error")

    client.app.state.storage.remove_chat = raise_exception

    response = client.delete("/tg-chat/1")
    assert response.status_code == 400
    error = response.json()
    detail = error["detail"]
    assert detail["description"] == "Ошибка при удалении чата"
    assert detail["code"] == "CHAT_REMOVAL_ERROR"
    assert detail["exception_name"] == "Exception"
    assert "Test error" in detail["exception_message"]


def test_get_links_exception(client: TestClient, monkeypatch) -> None:
    def raise_exception(chat_id: int) -> NoReturn:
        raise Exception("Test error")

    client.app.state.storage.get_links = raise_exception

    headers = {"Tg-Chat-Id": "1"}
    response = client.get("/links", headers=headers)
    assert response.status_code == 400
    error = response.json()
    detail = error["detail"]
    assert detail["description"] == "Ошибка при получении списка ссылок"
    assert detail["code"] == "LINKS_FETCH_ERROR"
    assert detail["exception_name"] == "Exception"
    assert "Test error" in detail["exception_message"]


def test_add_link_exception(client: TestClient, monkeypatch) -> None:
    def raise_exception(chat_id: int, url, tags, filters) -> NoReturn:
        raise Exception("Test error")

    client.app.state.storage.add_link = raise_exception

    headers = {"Tg-Chat-Id": "1"}
    link_request = {"link": "https://example.com", "tags": ["tag1"], "filters": []}
    response = client.post("/links", json=link_request, headers=headers)
    assert response.status_code == 400
    error = response.json()
    detail = error["detail"]
    assert detail["description"] == "Ошибка при добавлении ссылки"
    assert detail["code"] == "LINK_ADDITION_ERROR"
    assert detail["exception_name"] == "Exception"
    assert "Test error" in detail["exception_message"]


def test_remove_link_exception(client: TestClient, monkeypatch) -> None:
    def raise_exception(chat_id: int, url: str) -> NoReturn:
        raise Exception("Test error")

    client.app.state.storage.remove_link = raise_exception

    headers = {"Tg-Chat-Id": "1"}
    remove_request = {"link": "https://example.com"}
    response = client.request("DELETE", "/links", json=remove_request, headers=headers)
    assert response.status_code == 400
    error = response.json()
    detail = error["detail"]
    assert detail["description"] == "Ошибка при удалении ссылки"
    assert detail["code"] == "LINK_REMOVAL_ERROR"
    assert detail["exception_name"] == "Exception"
    assert "Test error" in detail["exception_message"]
