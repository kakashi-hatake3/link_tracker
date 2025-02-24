import asyncio
from collections.abc import Generator
from unittest.mock import MagicMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from telethon import TelegramClient
from telethon.events import NewMessage

from src.api import router
from src.server import default_lifespan


@pytest.fixture(scope="session")
def mock_event() -> Mock:
    event = Mock(spec=NewMessage.Event)
    event.input_chat = "test_chat"
    event.chat_id = 123456789
    event.message = "/chat_id"
    event.client = MagicMock(spec=TelegramClient)
    return event


@pytest.fixture(scope="session")
def fast_api_application() -> FastAPI:
    app = FastAPI(
        title="telegram_bot_app",
        lifespan=default_lifespan,
    )
    app.include_router(router=router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def test_client(fast_api_application: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(
        fast_api_application,
        backend_options={"loop_factory": asyncio.new_event_loop},
    ) as test_client:
        yield test_client
