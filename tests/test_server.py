import asyncio
import pytest
from fastapi.testclient import TestClient


class FakeTelegramClient:
    async def send_message(self, chat_id, message):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeTelegramClientWrapper:
    def __init__(self, *args, **kwargs):
        pass

    def start(self, bot_token):
        async def coro():
            return FakeTelegramClient()

        return coro()


class FakeBotHandler:
    @classmethod
    async def create(cls, tg_client, storage):
        return "fake_bot_handler"


@pytest.fixture(autouse=True)
def patch_telethon_and_bot_handler(monkeypatch):
    monkeypatch.setattr(
        "src.server.TelegramClient", lambda *args, **kwargs: FakeTelegramClientWrapper()
    )
    monkeypatch.setattr(
        "src.server.BotHandler", type("FakeBotHandlerClass", (), {"create": FakeBotHandler.create})
    )


@pytest.fixture
def test_app():
    from src.server import app

    return app


def test_lifespan_setup(test_app):
    with TestClient(test_app) as client:
        assert hasattr(client.app, "settings")
        assert hasattr(client.app, "storage")
        assert hasattr(client.app, "tg_client")
        assert hasattr(client.app, "bot_handler")
        assert client.app.bot_handler == "fake_bot_handler"
