import pytest
from fastapi import HTTPException

from src.handlers.bot_handlers import HELP_MESSAGE, BotHandler
from src.storage import Storage


class FakeScrapper:
    async def register_chat(self, chat_id: int) -> bool:
        return True

    async def add_link(self, chat_id: int, url, tags, filters):
        return type(
            "FakeLinkResponse", (), {"url": url, "tags": tags, "filters": filters},
        )

    async def remove_link(self, chat_id: int, url):
        if url == "https://example.com":
            return type("FakeLinkResponse", (), {"url": url})
        return None

    async def get_links(self, chat_id: int):
        if chat_id == 12345:
            FakeLinkResponse = type(
                "FakeLinkResponse", (), {"url": "https://example.com",
                                         "tags": ["tag1", "tag2"],
                                         "filters": ["filter1", "filter2"]},
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


class FullFakeScrapper:
    def __init__(self, *,
                 register_chat_return=True,
                 add_link_return="fake_link",
                 remove_link_return="fake_removed",
                 get_links_return=None,
                 add_link_exception=None,
                 remove_link_exception=None,
                 get_links_exception=None) -> None:
        self._register_chat_return = register_chat_return
        self._add_link_return = add_link_return
        self._remove_link_return = remove_link_return
        self._get_links_return = get_links_return if get_links_return is not None else []
        self._add_link_exception = add_link_exception
        self._remove_link_exception = remove_link_exception
        self._get_links_exception = get_links_exception

    async def register_chat(self, chat_id: int) -> bool:
        return self._register_chat_return

    async def add_link(self, chat_id: int, url, tags, filters):
        if self._add_link_exception:
            raise self._add_link_exception
        return self._add_link_return

    async def remove_link(self, chat_id: int, url):
        if self._remove_link_exception:
            raise self._remove_link_exception
        return self._remove_link_return

    async def get_links(self, chat_id: int):
        if self._get_links_exception:
            raise self._get_links_exception
        return self._get_links_return


@pytest.fixture(scope="module")
def storage(postgres_container):
    return Storage(postgres_container)


@pytest.mark.asyncio
async def test_start_handler_success(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(register_chat_return=True)
    fake_event = FakeEvent("/start", chat_id=111)
    await handler._start_handler(fake_event)
    assert storage.get_user(111) is not None
    assert any("Добро пожаловать" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_start_handler_error(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(register_chat_return=False)
    fake_event = FakeEvent("/start", chat_id=112)
    await handler._start_handler(fake_event)
    assert any("Произошла ошибка при регистрации" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_help_handler(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    fake_event = FakeEvent("/help")
    await handler._help_handler(fake_event)
    assert fake_event.replies[0] == HELP_MESSAGE


@pytest.mark.asyncio
async def test_track_handler_success(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(add_link_return="fake_link")
    fake_event = FakeEvent("/track https://example.com", chat_id=222)
    await handler._track_handler(fake_event)
    assert any("Введите тэги (опционально)" in reply for reply in fake_event.replies)
    fake_event = FakeEvent("tag1 tag2", chat_id=222)
    await handler._conversation_handler(fake_event)
    assert any("Настройте фильтры (опционально)" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_missing_url(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("/track", chat_id=223)
    await handler._track_handler(fake_event)
    assert any("Пожалуйста, укажите URL для отслеживания" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_invalid_url(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("/track not-a-url", chat_id=224)
    await handler._track_handler(fake_event)
    assert any("Некорректный URL" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_scrapper_returns_none(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(add_link_return=None)
    fake_event = FakeEvent("/track https://example.com", chat_id=225)
    await handler._track_handler(fake_event)
    assert any("Введите тэги (опционально)" in reply for reply in fake_event.replies)

    fake_event = FakeEvent("tag1 tag2", chat_id=225)
    await handler._conversation_handler(fake_event)
    assert any("Настройте фильтры (опционально)" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_http_exception(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(add_link_exception=HTTPException(detail="API error", status_code=400))
    fake_event = FakeEvent("/track https://example.com", chat_id=226)
    await handler._track_handler(fake_event)
    assert any("Введите тэги (опционально)" in reply for reply in fake_event.replies)

    fake_event = FakeEvent("tag1 tag2", chat_id=226)
    await handler._conversation_handler(fake_event)
    assert any("Настройте фильтры (опционально)" in reply for reply in fake_event.replies)

    fake_event = FakeEvent("filter1 filter2", chat_id=226)
    await handler._conversation_handler(fake_event)
    assert any("Ошибка API:" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_success(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(remove_link_return="fake_removed")
    fake_event = FakeEvent("/untrack https://example.com", chat_id=444)
    await handler._untrack_handler(fake_event)
    assert any("прекращено" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_missing_url(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("/untrack", chat_id=445)
    await handler._untrack_handler(fake_event)
    assert any("Пожалуйста, укажите URL для прекращения отслеживания" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_not_found(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(remove_link_return=None)
    fake_event = FakeEvent("/untrack https://nonexistent.com", chat_id=446)
    await handler._untrack_handler(fake_event)
    assert any("не отслеживается" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_http_exception(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(remove_link_exception=HTTPException(detail="API error", status_code=400))
    fake_event = FakeEvent("/untrack https://example.com", chat_id=447)
    await handler._untrack_handler(fake_event)
    assert any("Ошибка API:" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_generic_exception(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(remove_link_exception=Exception("Generic error"))
    fake_event = FakeEvent("/untrack https://example.com", chat_id=448)
    await handler._untrack_handler(fake_event)
    assert any("Произошла непредвиденная ошибка при удалении ссылки" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_list_handler_empty(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    async def fake_get_links(chat_id: int):
        return []
    handler.scrapper = FullFakeScrapper()
    handler.scrapper.get_links = fake_get_links
    fake_event = FakeEvent("/list", chat_id=666)
    await handler._list_handler(fake_event)
    assert any("пуст" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_list_handler_with_links(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    def fake_get_links(chat_id: int):
        FakeLinkResponse = type("FakeLinkResponse", (), {"url": "https://example.com", "tags": ["tag1", "tag2"]})
        return [FakeLinkResponse]
    handler.scrapper = FullFakeScrapper()
    handler.scrapper.get_links = fake_get_links
    fake_event = FakeEvent("/list", chat_id=12345)
    await handler._list_handler(fake_event)
    reply = fake_event.replies[0]
    assert "https://example.com" in reply
    assert "tag1, tag2" in reply


@pytest.mark.asyncio
async def test_list_handler_http_exception(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(get_links_exception=HTTPException(detail="API error", status_code=400))
    fake_event = FakeEvent("/list", chat_id=777)
    await handler._list_handler(fake_event)
    assert any("Ошибка API:" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_list_handler_generic_exception(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(get_links_exception=Exception("Generic error"))
    fake_event = FakeEvent("/list", chat_id=778)
    await handler._list_handler(fake_event)
    assert any("Произошла непредвиденная ошибка при получении списка ссылок" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_unknown_command_handler(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    fake_event = FakeEvent("/unknown", chat_id=779)
    await handler._unknown_command_handler(fake_event)
    assert any("Неизвестная команда" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_start_handler(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("/start", chat_id=111)
    await handler._start_handler(fake_event)
    user = storage.get_user(111)
    assert user is not None
    assert any("Добро пожаловать" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_help_handler(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    fake_event = FakeEvent("/help")
    await handler._help_handler(fake_event)
    assert fake_event.replies[0] == HELP_MESSAGE


@pytest.mark.asyncio
async def test_untrack_handler_success(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("/untrack https://example.com", chat_id=444)
    await handler._untrack_handler(fake_event)
    assert any("прекращено" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_not_found(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/untrack https://nonexistent.com", chat_id=555)
    await handler._untrack_handler(fake_event)
    assert any("не отслеживается" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_list_handler_empty(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)

    async def fake_get_links(chat_id: int):
        return []

    handler.scrapper = FullFakeScrapper()
    handler.scrapper.get_links = fake_get_links
    fake_event = FakeEvent("/list", chat_id=666)
    await handler._list_handler(fake_event)
    assert any("пуст" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_list_handler_with_links(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FakeScrapper()
    fake_event = FakeEvent("/list", chat_id=12345)
    await handler._list_handler(fake_event)
    reply = fake_event.replies[0]
    assert "https://example.com" in reply
    assert "tag1, tag2" in reply


@pytest.mark.asyncio
async def test_unknown_command_handler(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    fake_event = FakeEvent("/unknown", chat_id=777)
    await handler._unknown_command_handler(fake_event)
    assert any("Неизвестная команда" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_track_handler_missing_url(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("/track", chat_id=111)
    await handler._track_handler(fake_event)
    assert any("Пожалуйста, укажите URL для отслеживания" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_missing_url(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("/untrack", chat_id=333)
    await handler._untrack_handler(fake_event)
    assert any(
        "Пожалуйста, укажите URL для прекращения отслеживания" in reply
        for reply in fake_event.replies
    )


@pytest.mark.asyncio
async def test_list_handler_exception(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper(get_links_exception=True)
    fake_event = FakeEvent("/list", chat_id=444)
    await handler._list_handler(fake_event)
    assert any("Произошла непредвиденная ошибка при получении списка ссылок" in reply for reply in fake_event.replies)


@pytest.mark.asyncio
async def test_untrack_handler_empty_text(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    handler.scrapper = FullFakeScrapper()
    fake_event = FakeEvent("", chat_id=555)
    await handler._untrack_handler(fake_event)
    assert fake_event.replies == ["Пожалуйста, укажите URL для прекращения отслеживания."]


@pytest.mark.asyncio
async def test_conversation_handler_generic_exception(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    chat_id = 300
    handler.conversations[chat_id] = {
         "url": "https://example.com",
         "tags": ["tag1", "tag2"],
         "stage": "await_filters",
    }
    handler.scrapper = FullFakeScrapper(add_link_exception=Exception("Test generic error"))
    fake_event = FakeEvent("filter1 filter2", chat_id=chat_id)
    await handler._conversation_handler(fake_event)
    assert any("Произошла непредвиденная ошибка при добавлении ссылки" in reply for reply in fake_event.replies)
    assert chat_id not in handler.conversations


@pytest.mark.asyncio
async def test_conversation_handler_link_response_none(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    chat_id = 301
    handler.conversations[chat_id] = {
         "url": "https://example.com",
         "tags": ["tag1", "tag2"],
         "stage": "await_filters",
    }
    handler.scrapper = FullFakeScrapper(add_link_return=None)
    fake_event = FakeEvent("filter1 filter2", chat_id=chat_id)
    await handler._conversation_handler(fake_event)
    assert any("Эта ссылка уже отслеживается или произошла ошибка при добавлении" in reply for reply in fake_event.replies)
    assert chat_id not in handler.conversations


@pytest.mark.asyncio
async def test_conversation_handler_success(storage) -> None:
    fake_client = FakeClient()
    handler = BotHandler(fake_client, storage)
    chat_id = 302
    handler.conversations[chat_id] = {
         "url": "https://example.com",
         "tags": ["tag1", "tag2"],
         "stage": "await_filters",
    }
    handler.scrapper = FullFakeScrapper(add_link_return="fake_link")
    fake_event = FakeEvent("filter1 filter2", chat_id=chat_id)
    await handler._conversation_handler(fake_event)
    assert any("Ссылка https://example.com добавлена для отслеживания" in reply for reply in fake_event.replies)
    assert chat_id not in handler.conversations
