import urllib.parse
import os
import subprocess
from unittest.mock import MagicMock, Mock

import pytest
from telethon import TelegramClient
from telethon.events import NewMessage
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def mock_event() -> Mock:
    event = Mock(spec=NewMessage.Event)
    event.input_chat = "test_chat"
    event.chat_id = 123456789
    event.message = "/chat_id"
    event.client = MagicMock(spec=TelegramClient)
    return event


def convert_to_jdbc(db_url: str) -> str:
    """Преобразует URL подключения в формат JDBC, который требуется Liquibase."""
    parsed = urllib.parse.urlparse(db_url)
    host = parsed.hostname
    port = parsed.port
    if host == "localhost":
        host = "host.docker.internal"
    jdbc_url = f"jdbc:postgresql://{host}:{port}{parsed.path}"
    return jdbc_url


@pytest.fixture(scope="module")
def postgres_container() -> str:
    with PostgresContainer("postgres:14") as postgres:
        db_url = postgres.get_connection_url(driver="psycopg").replace("postgresql://", "postgresql+psycopg://", 1)

        jdbc_url = convert_to_jdbc(db_url)

        subprocess.run([
            "docker", "run", "--rm",
            "--add-host=host.docker.internal:host-gateway",
            "-v", f"{os.getcwd()}/migrations:/changesets",
            "liquibase/liquibase:4.29",
            "--searchPath=/changesets",
            "--changelog-file=master.xml",
            "--driver=org.postgresql.Driver",
            f"--url={jdbc_url}",
            "--username=postgres",
            "--password=postgres",
            "update"
        ], check=True)

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
