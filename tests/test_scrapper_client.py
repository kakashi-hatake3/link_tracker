import pytest
import aiohttp
from fastapi.encoders import jsonable_encoder
from pydantic import HttpUrl
from src.scrapper_client import ScrapperClient
from src.scrapper.models import LinkResponse, ListLinksResponse


class FakeRequestContext:
    def __init__(self, coro):
        self._coro = coro
        self._result = None

    async def __aenter__(self):
        self._result = await self._coro
        return self._result

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeResponse:
    def __init__(self, status: int, json_data=None):
        self.status = status
        self._json = json_data or {}

    async def json(self):
        return self._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeClientSession:
    def __init__(self, fake_post=None, fake_get=None, fake_delete=None):
        self.fake_post = fake_post
        self.fake_get = fake_get
        self.fake_delete = fake_delete

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def post(self, url, **kwargs):
        return FakeRequestContext(self.fake_post(url, **kwargs))

    def get(self, url, **kwargs):
        return FakeRequestContext(self.fake_get(url, **kwargs))

    def delete(self, url, **kwargs):
        return FakeRequestContext(self.fake_delete(url, **kwargs))


@pytest.mark.asyncio
async def test_register_chat_success(monkeypatch):
    async def fake_post(url, **kwargs):
        return FakeResponse(200)

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeClientSession(fake_post=fake_post))

    client = ScrapperClient(base_url="http://testserver")
    result = await client.register_chat(123)
    assert result is True


@pytest.mark.asyncio
async def test_register_chat_failure(monkeypatch):
    async def fake_post(url, **kwargs):
        return FakeResponse(400)

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeClientSession(fake_post=fake_post))

    client = ScrapperClient(base_url="http://testserver")
    result = await client.register_chat(123)
    assert result is False


@pytest.mark.asyncio
async def test_add_link_success(monkeypatch):
    fake_link_response = {
        "id": 1,
        "url": "https://example.com",
        "tags": ["Test description"],
        "filters": [],
    }

    async def fake_post(url, **kwargs):
        return FakeResponse(200, json_data=fake_link_response)

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeClientSession(fake_post=fake_post))

    client = ScrapperClient(base_url="http://testserver")
    result = await client.add_link(123, "https://example.com", "Test description")
    assert result is not None
    assert result.id == 1
    assert result.url == HttpUrl("https://example.com/")
    assert result.tags == ["Test description"]
    assert result.filters == []


@pytest.mark.asyncio
async def test_add_link_failure(monkeypatch):
    async def fake_post(url, **kwargs):
        return FakeResponse(400)

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeClientSession(fake_post=fake_post))

    client = ScrapperClient(base_url="http://testserver")
    result = await client.add_link(123, "https://example.com", "Test description")
    assert result is None


@pytest.mark.asyncio
async def test_remove_link_success(monkeypatch):
    fake_link_response = {"id": 2, "url": "https://example.com", "tags": [], "filters": []}

    async def fake_delete(url, **kwargs):
        return FakeResponse(200, json_data=fake_link_response)

    monkeypatch.setattr(
        aiohttp, "ClientSession", lambda: FakeClientSession(fake_delete=fake_delete)
    )

    client = ScrapperClient(base_url="http://testserver")
    result = await client.remove_link(123, "https://example.com")
    assert result is not None
    assert result.id == 2
    assert result.url == HttpUrl("https://example.com/")


@pytest.mark.asyncio
async def test_remove_link_failure(monkeypatch):
    async def fake_delete(url, **kwargs):
        return FakeResponse(404)

    monkeypatch.setattr(
        aiohttp, "ClientSession", lambda: FakeClientSession(fake_delete=fake_delete)
    )

    client = ScrapperClient(base_url="http://testserver")
    result = await client.remove_link(123, "https://example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_links_success(monkeypatch):
    fake_list_links_response = {
        "links": [{"id": 1, "url": "https://example.com", "tags": ["tag1"], "filters": []}],
        "size": 1,
    }

    async def fake_get(url, **kwargs):
        return FakeResponse(200, json_data=fake_list_links_response)

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeClientSession(fake_get=fake_get))

    client = ScrapperClient(base_url="http://testserver")
    result = await client.get_links(123)
    assert isinstance(result, list)
    assert len(result) == 1
    link = result[0]
    assert link.id == 1
    assert link.url == HttpUrl("https://example.com/")
    assert link.tags == ["tag1"]
    assert link.filters == []


@pytest.mark.asyncio
async def test_get_links_failure(monkeypatch):
    async def fake_get(url, **kwargs):
        return FakeResponse(404)

    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeClientSession(fake_get=fake_get))

    client = ScrapperClient(base_url="http://testserver")
    result = await client.get_links(123)
    assert result == []
