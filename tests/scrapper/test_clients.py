# from datetime import datetime, timezone
# from typing import TYPE_CHECKING, Optional
#
# import pytest
#
# from src.scrapper.clients import BaseClient, GitHubClient, StackOverflowClient, UpdateChecker
#
# if TYPE_CHECKING:
#     from pydantic import HttpUrl
#
#
# class FakeResponse:
#     def __init__(self, status: int, json_data: Optional[dict] = None) -> None:
#         self.status = status
#         self._json_data = json_data or {}
#
#     async def __aenter__(self):
#         return self
#
#     async def __aexit__(self, exc_type, exc, tb):
#         pass
#
#     async def json(self):
#         return self._json_data
#
#
# class FakeGetContext:
#     def __init__(self, fake_get, url, kwargs) -> None:
#         self.fake_get = fake_get
#         self.url = url
#         self.kwargs = kwargs
#         self.response = None
#
#     async def __aenter__(self):
#         self.response = await self.fake_get(self.url, **self.kwargs)
#         return self.response
#
#     async def __aexit__(self, exc_type, exc, tb):
#         pass
#
#
# class FakeSession:
#     def __init__(self, fake_get) -> None:
#         self.fake_get = fake_get
#
#     def get(self, url, **kwargs):
#         return FakeGetContext(self.fake_get, url, kwargs)
#
#
# async def fake_get_github_success(url, **kwargs):
#     return FakeResponse(200, {"updated_at": "2023-02-22T10:00:00Z"})
#
#
# async def fake_get_github_failure(url, **kwargs):
#     return FakeResponse(404)
#
#
# async def fake_get_stackoverflow_success(url, **kwargs):
#     return FakeResponse(200, {"items": [{"last_activity_date": 1677052800}]})
#
#
# async def fake_get_stackoverflow_failure(url, **kwargs):
#     return FakeResponse(404)
#
#
# def test_parse_github_url_valid() -> None:
#     owner, repo = BaseClient._parse_github_url("https://github.com/owner/repo")
#     assert owner == "owner"
#     assert repo == "repo"
#
#
# def test_parse_github_url_invalid_domain() -> None:
#     owner, repo = BaseClient._parse_github_url("https://example.com/owner/repo")
#     assert owner is None
#     assert repo is None
#
#
# def test_parse_github_url_insufficient_parts() -> None:
#     owner, repo = BaseClient._parse_github_url("https://github.com/owner")
#     assert owner is None
#     assert repo is None
#
#
# def test_parse_stackoverflow_url_valid() -> None:
#     question_id = BaseClient._parse_stackoverflow_url(
#         "https://stackoverflow.com/questions/1234567/title",
#     )
#     assert question_id == "1234567"
#
#
# def test_parse_stackoverflow_url_invalid_domain() -> None:
#     question_id = BaseClient._parse_stackoverflow_url("https://example.com/questions/1234567/title")
#     assert question_id is None
#
#
# def test_parse_stackoverflow_url_invalid_path() -> None:
#     question_id = BaseClient._parse_stackoverflow_url("https://stackoverflow.com/tags/python")
#     assert question_id is None
#
#
# @pytest.mark.asyncio
# async def test_github_get_last_update_success() -> None:
#     session = FakeSession(fake_get_github_success)
#     client = GitHubClient(session)
#     url: HttpUrl = "https://github.com/owner/repo"
#     result = await client.get_last_update(url)
#     expected = datetime.fromisoformat("2023-02-22T10:00:00+00:00")
#     assert result == expected
#
#
# @pytest.mark.asyncio
# async def test_github_get_last_update_invalid_url() -> None:
#     session = FakeSession(fake_get_github_success)
#     client = GitHubClient(session)
#     url: HttpUrl = "https://notgithub.com/owner/repo"
#     result = await client.get_last_update(url)
#     assert result is None
#
#
# @pytest.mark.asyncio
# async def test_github_get_last_update_failure() -> None:
#     session = FakeSession(fake_get_github_failure)
#     client = GitHubClient(session)
#     url: HttpUrl = "https://github.com/owner/repo"
#     result = await client.get_last_update(url)
#     assert result is None
#
#
# @pytest.mark.asyncio
# async def test_stackoverflow_get_last_update_success() -> None:
#     session = FakeSession(fake_get_stackoverflow_success)
#     client = StackOverflowClient(session)
#     url: HttpUrl = "https://stackoverflow.com/questions/1234567/title"
#     result = await client.get_last_update(url)
#     expected = datetime.fromtimestamp(1677052800, tz=timezone.utc)
#     assert result == expected
#
#
# @pytest.mark.asyncio
# async def test_stackoverflow_get_last_update_invalid_url() -> None:
#     session = FakeSession(fake_get_stackoverflow_success)
#     client = StackOverflowClient(session)
#     url: HttpUrl = "https://notoverflow.com/questions/1234567/title"
#     result = await client.get_last_update(url)
#     assert result is None
#
#
# @pytest.mark.asyncio
# async def test_stackoverflow_get_last_update_failure() -> None:
#     session = FakeSession(fake_get_stackoverflow_failure)
#     client = StackOverflowClient(session)
#     url: HttpUrl = "https://stackoverflow.com/questions/1234567/title"
#     result = await client.get_last_update(url)
#     assert result is None
#
#
# @pytest.mark.asyncio
# async def test_update_checker_github() -> None:
#     session = FakeSession(fake_get_github_success)
#     checker = UpdateChecker(session)
#     url: HttpUrl = "https://github.com/owner/repo"
#     result = await checker.check_updates(url)
#     expected = datetime.fromisoformat("2023-02-22T10:00:00+00:00")
#     assert result == expected
#
#
# @pytest.mark.asyncio
# async def test_update_checker_stackoverflow() -> None:
#     session = FakeSession(fake_get_stackoverflow_success)
#     checker = UpdateChecker(session)
#     url: HttpUrl = "https://stackoverflow.com/questions/1234567/title"
#     result = await checker.check_updates(url)
#     expected = datetime.fromtimestamp(1677052800, tz=timezone.utc)
#     assert result == expected
#
#
# @pytest.mark.asyncio
# async def test_update_checker_unknown_url() -> None:
#     session = FakeSession(lambda url, **kwargs: FakeResponse(200, {}))
#     checker = UpdateChecker(session)
#     url: HttpUrl = "https://example.com"
#     result = await checker.check_updates(url)
#     assert result is None

# test_new_clients.py
import pytest
from datetime import datetime, timezone
from typing import Optional

from src.scrapper.clients import BaseClient, GitHubClient, StackOverflowClient
from src.scrapper.update_checker import UpdateChecker


class FakeResponse:
    def __init__(self, status: int, json_data: Optional[dict] = None) -> None:
        self.status = status
        self._json_data = json_data or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return self._json_data

class FakeGetContext:
    def __init__(self, fake_get, url, kwargs) -> None:
        self.fake_get = fake_get
        self.url = url
        self.kwargs = kwargs

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


def test_parse_github_url_valid():
    owner, repo = BaseClient._parse_github_url("https://github.com/owner/repo")
    assert owner == "owner"
    assert repo == "repo"

def test_parse_github_url_invalid_domain():
    owner, repo = BaseClient._parse_github_url("https://example.com/owner/repo")
    assert owner is None
    assert repo is None

def test_parse_github_url_insufficient_parts():
    owner, repo = BaseClient._parse_github_url("https://github.com/owner")
    assert owner is None
    assert repo is None

def test_parse_stackoverflow_url_valid():
    question_id = BaseClient._parse_stackoverflow_url("https://stackoverflow.com/questions/1234567/title")
    assert question_id == "1234567"

def test_parse_stackoverflow_url_invalid_domain():
    question_id = BaseClient._parse_stackoverflow_url("https://example.com/questions/1234567/title")
    assert question_id is None

def test_parse_stackoverflow_url_invalid_path():
    question_id = BaseClient._parse_stackoverflow_url("https://stackoverflow.com/tags/python")
    assert question_id is None


async def fake_get_github_new_updates(url, **kwargs):
    if "pulls" in url:
        pr = {
            "created_at": "2023-03-10T10:00:00Z",
            "title": "New PR Title",
            "user": {"login": "pr_user"},
            "body": "This is the PR description body " * 10,
        }
        return FakeResponse(200, [pr])
    elif "issues" in url:
        issue = {
            "created_at": "2023-03-11T10:00:00Z",
            "title": "New Issue Title",
            "user": {"login": "issue_user"},
            "body": "This is the issue description body " * 10,
        }
        return FakeResponse(200, [issue])
    else:
        return FakeResponse(404)

@pytest.mark.asyncio
async def test_github_get_new_updates_no_last_check():
    session = FakeSession(lambda url, **kwargs: FakeResponse(200, []))
    client = GitHubClient(session)
    url = "https://github.com/owner/repo"
    updates = await client.get_new_updates(url, None)
    assert updates == []

@pytest.mark.asyncio
async def test_github_get_new_updates_with_updates():
    session = FakeSession(fake_get_github_new_updates)
    client = GitHubClient(session)
    url = "https://github.com/owner/repo"
    last_check = datetime.fromisoformat("2023-03-01T00:00:00+00:00")
    updates = await client.get_new_updates(url, last_check)
    assert len(updates) == 2
    pr_update = next((u for u in updates if u.update_type == "PR"), None)
    issue_update = next((u for u in updates if u.update_type == "Issue"), None)
    assert pr_update is not None
    assert issue_update is not None
    assert pr_update.title == "New PR Title"
    assert pr_update.username == "pr_user"
    assert len(pr_update.preview) <= 200


async def fake_get_stackoverflow_new_updates(url, **kwargs):
    if "questions/" in url and "answers" not in url and "comments" not in url:
        return FakeResponse(200, {"items": [{"title": "Test Question Title"}]})
    elif "answers" in url:
        answer = {
            "creation_date": 1678052800,
            "owner": {"display_name": "answer_user"},
            "body": "This is the answer body " * 20,
        }
        return FakeResponse(200, {"items": [answer]})
    elif "comments" in url:
        comment = {
            "creation_date": 1678052900,
            "owner": {"display_name": "comment_user"},
            "body": "This is the comment body " * 20,
        }
        return FakeResponse(200, {"items": [comment]})
    return FakeResponse(404)

@pytest.mark.asyncio
async def test_stackoverflow_get_new_updates_no_last_check():
    session = FakeSession(lambda url, **kwargs: FakeResponse(200, {}))
    client = StackOverflowClient(session)
    url = "https://stackoverflow.com/questions/1234567/title"
    updates = await client.get_new_updates(url, None)
    assert updates == []

@pytest.mark.asyncio
async def test_stackoverflow_get_new_updates_with_updates():
    session = FakeSession(fake_get_stackoverflow_new_updates)
    client = StackOverflowClient(session)
    url = "https://stackoverflow.com/questions/1234567/title"
    last_check = datetime.fromisoformat("2023-03-01T00:00:00+00:00")
    updates = await client.get_new_updates(url, last_check)
    assert len(updates) == 2
    answer_update = next((u for u in updates if u.update_type == "Answer"), None)
    comment_update = next((u for u in updates if u.update_type == "Comment"), None)
    assert answer_update is not None
    assert comment_update is not None
    assert answer_update.title == "Test Question Title"
    assert answer_update.username == "answer_user"
    assert len(answer_update.preview) <= 200

@pytest.mark.asyncio
async def test_update_checker_github():
    session = FakeSession(fake_get_github_new_updates)
    checker = UpdateChecker(session)
    url = "https://github.com/owner/repo"
    last_check = datetime.fromisoformat("2023-03-01T00:00:00+00:00")
    updates = await checker.get_new_updates(url, last_check)
    assert len(updates) == 2

@pytest.mark.asyncio
async def test_update_checker_stackoverflow():
    session = FakeSession(fake_get_stackoverflow_new_updates)
    checker = UpdateChecker(session)
    url = "https://stackoverflow.com/questions/1234567/title"
    last_check = datetime.fromisoformat("2023-03-01T00:00:00+00:00")
    updates = await checker.get_new_updates(url, last_check)
    assert len(updates) == 2

@pytest.mark.asyncio
async def test_update_checker_unknown_url():
    session = FakeSession(lambda url, **kwargs: FakeResponse(200, {}))
    checker = UpdateChecker(session)
    url = "https://example.com"
    last_check = datetime.fromisoformat("2023-03-01T00:00:00+00:00")
    updates = await checker.get_new_updates(url, last_check)
    assert updates == []
