import pytest
from pydantic import HttpUrl
from src.models import Link, LinkUpdate, ApiErrorResponse, User

def test_link_model():
    link_data = {
        "url": "https://example.com",
        "description": "Test description"
    }
    link = Link(**link_data)
    assert isinstance(link.url, HttpUrl)
    assert str(link.url) == "https://example.com/"
    assert link.description == "Test description"

    link_without_description = Link(url="https://example.com")
    assert isinstance(link_without_description.url, HttpUrl)
    assert link_without_description.description is None

def test_link_update_model():
    update_data = {
        "id": 1,
        "url": "https://example.com",
        "description": "Test description",
        "tgChatIds": [123456789]
    }
    update = LinkUpdate(**update_data)
    assert update.id == 1
    assert isinstance(update.url, HttpUrl)
    assert str(update.url) == "https://example.com/"
    assert update.description == "Test description"
    assert update.tg_chat_ids == [123456789]

def test_api_error_response_model():
    error_data = {
        "description": "Test error",
        "code": "TEST_ERROR",
        "exceptionName": "TestException",
        "exceptionMessage": "Test message",
        "stacktrace": ["line1", "line2"]
    }
    error = ApiErrorResponse(**error_data)
    assert error.description == "Test error"
    assert error.code == "TEST_ERROR"
    assert error.exception_name == "TestException"
    assert error.exception_message == "Test message"
    assert error.stacktrace == ["line1", "line2"]

    min_error_data = {
        "description": "Test error",
        "code": "TEST_ERROR"
    }
    min_error = ApiErrorResponse(**min_error_data)
    assert min_error.description == "Test error"
    assert min_error.code == "TEST_ERROR"
    assert min_error.exception_name is None
    assert min_error.exception_message is None
    assert min_error.stacktrace is None

def test_user_model():
    user_data = {
        "chat_id": 123456789,
        "tracked_links": [
            {
                "url": "https://example.com",
                "description": "Test link"
            }
        ]
    }
    user = User(**user_data)
    assert user.chat_id == 123456789
    assert len(user.tracked_links) == 1
    assert isinstance(user.tracked_links[0], Link)
    assert str(user.tracked_links[0].url) == "https://example.com/"

    user_without_links = User(chat_id=123456789)
    assert user_without_links.chat_id == 123456789
    assert len(user_without_links.tracked_links) == 0 