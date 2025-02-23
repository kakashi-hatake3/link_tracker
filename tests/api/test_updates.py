import pytest
from fastapi import Request, HTTPException
from src.models import LinkUpdate
from src.api.updates import process_update


class FakeStorage:
    def __init__(self):
        self.users = {}

    def get_user(self, chat_id):
        return self.users.get(chat_id)

    def add_user(self, chat_id, user):
        self.users[chat_id] = user


class FakeUser:
    pass


class FakeTGClient:
    def __init__(self):
        self.sent_messages = []

    async def send_message(self, chat_id, message):
        self.sent_messages.append((chat_id, message))


class FakeApp:
    def __init__(self):
        self.storage = FakeStorage()
        self.tg_client = FakeTGClient()


class FakeRequest:
    def __init__(self, app):
        self.app = app


@pytest.mark.asyncio
async def test_process_update_success():
    fake_app = FakeApp()
    fake_app.storage.add_user(111, FakeUser())
    update = LinkUpdate(
        id=1, url="https://example.com", tgChatIds=[111, 222], description="Test update"
    )
    fake_request = FakeRequest(fake_app)
    response = await process_update(update, fake_request)
    assert response == {"status": "ok"}
    assert fake_app.tg_client.sent_messages == [
        (111, "Обновление для ссылки https://example.com/\nОписание: Test update")
    ]


@pytest.mark.asyncio
async def test_process_update_exception(monkeypatch):
    fake_app = FakeApp()
    fake_app.storage.add_user(111, FakeUser())

    async def fake_send_message(chat_id, message):
        raise Exception("Test error")

    fake_app.tg_client.send_message = fake_send_message
    update = LinkUpdate(id=1, url="https://example.com", tgChatIds=[111], description=None)
    fake_request = FakeRequest(fake_app)
    with pytest.raises(HTTPException) as excinfo:
        await process_update(update, fake_request)
    assert excinfo.value.status_code == 400
    detail = excinfo.value.detail
    assert detail["code"] == "UPDATE_PROCESSING_ERROR"
