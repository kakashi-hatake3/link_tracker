import asyncio

import aiohttp
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager
from typing import AsyncIterator

from src.scrapper.app import app, lifespan
from src.scrapper.storage import ScrapperStorage


# Пример тестового контейнера (заглушки)
class TestStorage:
    def __init__(self):
        self.data = {}

    async def save(self, key, value):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)


# Фикстура для подмены ScrapperStorage на TestStorage
@pytest.fixture
def mock_storage(monkeypatch):
    def mock_scrapper_storage():
        return TestStorage()

    monkeypatch.setattr("src.scrapper.app.ScrapperStorage", mock_scrapper_storage)


# Фикстура для отключения уведомлений об обновлениях (уже есть в вашем коде)
@pytest.fixture(autouse=True)
def disable_update_notification(monkeypatch) -> None:
    async def fake_send_update_notification(self, update) -> None:
        return

    monkeypatch.setattr(
        "src.scrapper.sender.NotificationSender.send_update_notification",
        fake_send_update_notification,
    )


# Фикстура для клиента
@pytest.fixture
def client(mock_storage):  # Добавляем mock_storage как зависимость
    with TestClient(app) as client:
        yield client


# Тест для проверки lifespan
def test_app_lifespan(client: TestClient) -> None:
    state = client.app.state
    # Проверяем, что storage является экземпляром TestStorage, а не ScrapperStorage
    assert isinstance(state.storage, TestStorage)
    assert not isinstance(state.storage, ScrapperStorage)
    assert isinstance(state.session, aiohttp.ClientSession)
    assert state.update_checker is not None
    assert state.scheduler is not None
    assert state.scheduler._running is True


# Тест для проверки работы тестового контейнера
def test_storage_functionality(client: TestClient) -> None:
    state = client.app.state
    storage = state.storage

    # Проверяем, что тестовый контейнер работает
    key, value = "test_key", "test_value"
    asyncio.run(storage.save(key, value))
    result = asyncio.run(storage.get(key))
    assert result == value