import pytest
from datetime import datetime
from urllib.parse import urlparse

from pydantic import HttpUrl

from src.scrapper.clients import BaseClient, GitHubClient, StackOverflowClient, UpdateChecker


class FakeResponse:
    def __init__(self, status: int, json_data: dict = None):
        self.status = status
        self._json_data = json_data or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return self._json_data


class FakeGetContext:
    def __init__(self, fake_get, url, kwargs):
        self.fake_get = fake_get
        self.url = url
        self.kwargs = kwargs
        self.response = None

    async def __aenter__(self):
        self.response = await self.fake_get(self.url, **self.kwargs)
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeSession:
    def __init__(self, fake_get):
        self.fake_get = fake_get

    def get(self, url, **kwargs):
        return FakeGetContext(self.fake_get, url, kwargs)


async def fake_get_github_success(url, **kwargs):
    return FakeResponse(200, {"updated_at": "2023-02-22T10:00:00Z"})


async def fake_get_github_failure(url, **kwargs):
    return FakeResponse(404)


async def fake_get_stackoverflow_success(url, **kwargs):
    return FakeResponse(200, {"items": [{"last_activity_date": 1677052800}]})


async def fake_get_stackoverflow_failure(url, **kwargs):
    return FakeResponse(404)


def test_parse_github_url_valid():
    owner, repo = BaseClient._parse_github_url("https://github.com/owner/repo")
    assert owner == "owner"
    assert repo == "repo"


def test_parse_github_url_invalid_domain():
    owner, repo = BaseClient._parse_github_url("https://example.com/owner/repo")
    assert owner is None and repo is None


def test_parse_github_url_insufficient_parts():
    owner, repo = BaseClient._parse_github_url("https://github.com/owner")
    assert owner is None and repo is None


def test_parse_stackoverflow_url_valid():
    question_id = BaseClient._parse_stackoverflow_url(
        "https://stackoverflow.com/questions/1234567/title"
    )
    assert question_id == "1234567"


def test_parse_stackoverflow_url_invalid_domain():
    question_id = BaseClient._parse_stackoverflow_url("https://example.com/questions/1234567/title")
    assert question_id is None


def test_parse_stackoverflow_url_invalid_path():
    question_id = BaseClient._parse_stackoverflow_url("https://stackoverflow.com/tags/python")
    assert question_id is None


@pytest.mark.asyncio
async def test_github_get_last_update_success():
    session = FakeSession(fake_get_github_success)
    client = GitHubClient(session)
    url: HttpUrl = "https://github.com/owner/repo"
    result = await client.get_last_update(url)
    expected = datetime.fromisoformat("2023-02-22T10:00:00+00:00")
    assert result == expected


@pytest.mark.asyncio
async def test_github_get_last_update_invalid_url():
    session = FakeSession(fake_get_github_success)
    client = GitHubClient(session)
    url: HttpUrl = "https://notgithub.com/owner/repo"
    result = await client.get_last_update(url)
    assert result is None


@pytest.mark.asyncio
async def test_github_get_last_update_failure():
    session = FakeSession(fake_get_github_failure)
    client = GitHubClient(session)
    url: HttpUrl = "https://github.com/owner/repo"
    result = await client.get_last_update(url)
    assert result is None


@pytest.mark.asyncio
async def test_stackoverflow_get_last_update_success():
    session = FakeSession(fake_get_stackoverflow_success)
    client = StackOverflowClient(session)
    url: HttpUrl = "https://stackoverflow.com/questions/1234567/title"
    result = await client.get_last_update(url)
    expected = datetime.fromtimestamp(1677052800)
    assert result == expected


@pytest.mark.asyncio
async def test_stackoverflow_get_last_update_invalid_url():
    session = FakeSession(fake_get_stackoverflow_success)
    client = StackOverflowClient(session)
    url: HttpUrl = "https://notoverflow.com/questions/1234567/title"
    result = await client.get_last_update(url)
    assert result is None


@pytest.mark.asyncio
async def test_stackoverflow_get_last_update_failure():
    session = FakeSession(fake_get_stackoverflow_failure)
    client = StackOverflowClient(session)
    url: HttpUrl = "https://stackoverflow.com/questions/1234567/title"
    result = await client.get_last_update(url)
    assert result is None


@pytest.mark.asyncio
async def test_update_checker_github():
    session = FakeSession(fake_get_github_success)
    checker = UpdateChecker(session)
    url: HttpUrl = "https://github.com/owner/repo"
    result = await checker.check_updates(url)
    expected = datetime.fromisoformat("2023-02-22T10:00:00+00:00")
    assert result == expected


@pytest.mark.asyncio
async def test_update_checker_stackoverflow():
    session = FakeSession(fake_get_stackoverflow_success)
    checker = UpdateChecker(session)
    url: HttpUrl = "https://stackoverflow.com/questions/1234567/title"
    result = await checker.check_updates(url)
    expected = datetime.fromtimestamp(1677052800)
    assert result == expected


@pytest.mark.asyncio
async def test_update_checker_unknown_url():
    session = FakeSession(lambda url, **kwargs: FakeResponse(200, {}))
    checker = UpdateChecker(session)
    url: HttpUrl = "https://example.com"
    result = await checker.check_updates(url)
    assert result is None
