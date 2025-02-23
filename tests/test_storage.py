import pytest
from src.storage import Storage
from src.models import Link


def test_add_and_get_user():
    storage = Storage()
    chat_id = 123
    assert storage.get_user(chat_id) is None

    storage.add_user(chat_id)
    user = storage.get_user(chat_id)
    assert user is not None
    assert user.chat_id == chat_id
    assert user.tracked_links == []


def test_add_user_idempotent():
    storage = Storage()
    chat_id = 123
    storage.add_user(chat_id)
    user1 = storage.get_user(chat_id)
    storage.add_user(chat_id)
    user2 = storage.get_user(chat_id)
    assert user1 is user2


def test_add_link_success():
    storage = Storage()
    chat_id = 100
    storage.add_user(chat_id)
    link = Link(url="https://example.com", description="Example site")

    result = storage.add_link(chat_id, link)
    assert result is True

    user = storage.get_user(chat_id)
    assert len(user.tracked_links) == 1
    assert user.tracked_links[0].url == link.url
    assert user.tracked_links[0].description == "Example site"


def test_add_link_failure_no_user():
    storage = Storage()
    chat_id = 200
    link = Link(url="https://example.com", description="Example site")
    result = storage.add_link(chat_id, link)
    assert result is False


def test_add_link_duplicate():
    storage = Storage()
    chat_id = 300
    storage.add_user(chat_id)
    link = Link(url="https://example.com", description="Example site")

    result1 = storage.add_link(chat_id, link)
    result2 = storage.add_link(chat_id, link)
    assert result1 is True
    assert result2 is False

    user = storage.get_user(chat_id)
    assert len(user.tracked_links) == 1


def test_remove_link_success():
    storage = Storage()
    chat_id = 400
    storage.add_user(chat_id)
    link = Link(url="https://example.com", description="Example site")
    storage.add_link(chat_id, link)

    result = storage.remove_link(chat_id, "https://example.com/")
    assert result is True

    user = storage.get_user(chat_id)
    assert len(user.tracked_links) == 0


def test_remove_link_failure_no_user():
    storage = Storage()
    result = storage.remove_link(500, "https://example.com")
    assert result is False


def test_remove_link_failure_not_found():
    storage = Storage()
    chat_id = 600
    storage.add_user(chat_id)
    link = Link(url="https://example.com", description="Example site")
    storage.add_link(chat_id, link)

    result = storage.remove_link(chat_id, "https://notexist.com")
    assert result is False

    user = storage.get_user(chat_id)
    assert len(user.tracked_links) == 1


def test_get_links_empty():
    storage = Storage()
    chat_id = 700
    storage.add_user(chat_id)
    links = storage.get_links(chat_id)
    assert links == []


def test_get_links_no_user():
    storage = Storage()
    links = storage.get_links(800)
    assert links == []
