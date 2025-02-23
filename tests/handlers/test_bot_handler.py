
import pytest

from src.handlers.bot_handlers import HELP_MESSAGE, BotHandler
from src.storage import Storage


class FakeScrapper:
    async def register_chat(self, chat_id: int) -> bool:
        return True

    async def add_link(self, chat_id: int, url, description=None):
        return type(
            "FakeLinkResponse", (), {"url": url, "tags": [description] if description else []},
        )

    async def remove_link(self, chat_id: int, url):
        if url == "https://example.com":
            return type("FakeLinkResponse", (), {"url": url})
        return None

    async def get_links(self, chat_id: int):
        if chat_id == 12345:
            FakeLinkResponse = type(
                "FakeLinkResponse", (), {"url": "https://example.com", "tags": ["tag1", "tag2"]},
            )
            return [FakeLinkResponse]
        return []


class FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeEvent:
    def __init__(self, text: str, chat_id: int = 12345) -> None:
        self.chat_id = chat_id
        self.message = FakeMessage(text)
        self.replies = []

    async def reply(self, message: str) -> None:
        self.replies.append(message)


class FakeClient:
    def __init__(self) -> None:
        self.handlers = []

    def add_event_handler(self, callback, event) -> None:
        self.handlers.append((callback, event))

    async def __call__(self, request):
        return


class CustomFakeScrapper:
    def __init__(self, add_link_return=None, remove_link_return=None, get_links_exception=False) -> None:
        self._add_link_return = add_link_return
        self._remove_link_return = remove_link_return
        self._get_links_exception = get_links_exception

    async def register_chat(self, chat_id: int) -> bool:
        return True

    async def add_link(self, chat_id: int, url, description=None):
        if self._add_link_return is None:
            return None
        return type(
            "FakeLinkResponse", (), {"url": url, "tags": [description] if description else []},
        )

    async def remove_link(self, chat_id: int, url):
        return self._remove_link_return

    async def get_links(self, chat_id: int):
        if self._get_links_exception:
            raise Exception("Test exception in get_links")
        return []


@pytest.mark.asyncio
async def test_start_handler() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/start", chat_id=111)
    await handler._start_handler(fake_event)
    user = storage.get_user(111)
    assert user is not None
    assert any("Добро пожаловать" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_help_handler() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    fake_event = FakeEvent("/help")
    await handler._help_handler(fake_event)
    assert fake_event.replies[0] == HELP_MESSAGE


@pytest.mark.asyncio
async def test_track_handler_success() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/track https://example.com Some description", chat_id=222)
    await handler._track_handler(fake_event)
    assert any("добавлена для отслеживания" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_invalid_url() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/track not-a-url", chat_id=333)
    await handler._track_handler(fake_event)
    assert any("Ошибка при добавлении ссылки" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_success() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/untrack https://example.com", chat_id=444)
    await handler._untrack_handler(fake_event)
    assert any("прекращено" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_not_found() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/untrack https://nonexistent.com", chat_id=555)
    await handler._untrack_handler(fake_event)
    assert any("не отслеживается" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_list_handler_empty() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)

    async def fake_get_links(chat_id: int):
        return []

    handler.scrapper = FakeScrapper()
    handler.scrapper.get_links = fake_get_links
    fake_event = FakeEvent("/list", chat_id=666)
    await handler._list_handler(fake_event)
    assert any("пуст" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_list_handler_with_links() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/list", chat_id=12345)
    await handler._list_handler(fake_event)
    reply = fake_event.replies[0]
    assert "https://example.com" in reply
    assert "tag1, tag2" in reply


@pytest.mark.asyncio
async def test_unknown_command_handler() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    fake_event = FakeEvent("/unknown", chat_id=777)
    await handler._unknown_command_handler(fake_event)
    assert any("Неизвестная команда" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_missing_url() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = CustomFakeScrapper()
    fake_event = FakeEvent("/track", chat_id=111)
    await handler._track_handler(fake_event)
    assert any("Пожалуйста, укажите URL для отслеживания" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_scrapper_returns_none() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = CustomFakeScrapper(add_link_return=None)
    fake_event = FakeEvent("/track https://example.com Some description", chat_id=222)
    await handler._track_handler(fake_event)
    assert any("Эта ссылка уже отслеживается" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_missing_url() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = CustomFakeScrapper()
    fake_event = FakeEvent("/untrack", chat_id=333)
    await handler._untrack_handler(fake_event)
    assert any(
        "Пожалуйста, укажите URL для прекращения отслеживания" in reply
        for reply in fake_event.replies
    )


@pytest.mark.asyncio
async def test_list_handler_exception() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = CustomFakeScrapper(get_links_exception=True)
    fake_event = FakeEvent("/list", chat_id=444)
    await handler._list_handler(fake_event)
    assert any("Ошибка при получении списка ссылок" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_empty_text() -> None:
    fake_client = FakeClient()
    storage = Storage()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = CustomFakeScrapper()
    fake_event = FakeEvent("", chat_id=555)
    await handler._untrack_handler(fake_event)
    assert fake_event.replies == []
