from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy import create_engine
from telethon import TelegramClient
from telethon.events import NewMessage
from testcontainers.postgres import PostgresContainer

from src.database import Base


@pytest.fixture(scope="session")
def mock_event() -> Mock:
    event = Mock(spec=NewMessage.Event)
    event.input_chat = "test_chat"
    event.chat_id = 123456789
    event.message = "/chat_id"
    event.client = MagicMock(spec=TelegramClient)
    return event


@pytest.fixture(scope="module")
def postgres_container() -> str:
    with PostgresContainer("postgres:14") as postgres:
        db_url = postgres.get_connection_url(driver="psycopg").replace("postgresql://", "postgresql+psycopg://", 1)
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        yield db_url


# @pytest.fixture(scope="session")
# def fast_api_application() -> FastAPI:
#     app = FastAPI(
#         title="telegram_bot_app",
#         lifespan=default_lifespan,
#     )
#     app.include_router(router=router, prefix="/api/v1")
#     return app


# @pytest.fixture(scope="session")
# def test_client(fast_api_application: FastAPI) -> Generator[TestClient, None, None]:
#     with TestClient(
#         fast_api_application,
#         backend_options={"loop_factory": asyncio.new_event_loop},
#     ) as test_client:
#         yield test_client
