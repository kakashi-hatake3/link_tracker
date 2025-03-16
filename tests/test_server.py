from types import TracebackType
from typing import Awaitable, Optional, Type, Union

import pytest
from fastapi import FastAPI
from telethon import TelegramClient


class FakeTelegramClient:
    async def send_message(self, chat_id: int, message: str) -> None:
        return None

    async def __aenter__(self) -> "FakeTelegramClient":
        return self

    async def __aexit__(
        self,
        _exc_type: Optional[Type[BaseException]],
        _exc: Optional[BaseException],
        _tb: Optional[TracebackType],
    ) -> None:
        del _exc_type, _exc, _tb


class FakeTelegramClientWrapper:
    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def start(self, bot_token: str) -> Awaitable[FakeTelegramClient]:
        async def coro() -> FakeTelegramClient:
            return FakeTelegramClient()

        return coro()


class FakeBotHandler:
    @classmethod
    async def create(
        cls,
        _tg_client: Union[TelegramClient, FakeTelegramClient],
        _storage: object,
    ) -> str:
        return "fake_bot_handler"


def fake_telegram_client_constructor(*args: object, **kwargs: object) -> FakeTelegramClientWrapper:
    return FakeTelegramClientWrapper(*args, **kwargs)


@pytest.fixture(autouse=True)
def patch_telethon_and_bot_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.server.TelegramClient", fake_telegram_client_constructor)
    monkeypatch.setattr(
        "src.server.BotHandler",
        type("FakeBotHandlerClass", (), {"create": FakeBotHandler.create}),
    )


@pytest.fixture
def test_app() -> FastAPI:
    from src.server import app

    return app

#
# def test_lifespan_setup(test_app: FastAPI) -> None:
#     with TestClient(test_app) as client:
#         assert hasattr(client.app, "settings")
#         assert hasattr(client.app, "storage")
#         assert hasattr(client.app, "tg_client")
#         assert hasattr(client.app, "bot_handler")
#         assert client.app.bot_handler == "fake_bot_handler"
