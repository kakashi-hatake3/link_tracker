import pytest
import aiohttp
from fastapi.testclient import TestClient
from src.scrapper.app import app
from src.scrapper.storage import ScrapperStorage


@pytest.fixture(autouse=True)
def disable_update_notification(monkeypatch):
    async def fake_send_update_notification(self, update):
        return

    monkeypatch.setattr(
        "src.scrapper.scheduler.UpdateScheduler._send_update_notification",
        fake_send_update_notification,
    )


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_app_lifespan(client: TestClient):
    state = client.app.state
    assert isinstance(state.storage, ScrapperStorage)
    assert isinstance(state.session, aiohttp.ClientSession)
    assert state.update_checker is not None
    assert state.scheduler is not None
    assert state.scheduler._running is True
