import pytest
from sqlalchemy import text

from src.scrapper.storage import ORMStorage, SQLStorage, StorageInterface


@pytest.fixture(params=["ORM", "SQL"])
def storage(request, postgres_container) -> StorageInterface:
    if request.param == "ORM":
        stor = ORMStorage(postgres_container)
    else:
        stor = SQLStorage(postgres_container)
    yield stor

    engine = stor.engine
    with engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE link_filters, link_tags, links, tags, chats RESTART IDENTITY CASCADE"
            )
        )
        conn.commit()


def test_add_and_get_chat(storage: StorageInterface):
    chat = storage.get_chat(1)
    assert chat is None

    storage.add_chat(1)
    chat = storage.get_chat(1)
    assert chat is not None
    assert chat.chat_id == 1

    storage.add_chat(1)
    chat = storage.get_chat(1)
    assert chat is not None
    assert chat.chat_id == 1


def test_remove_chat(storage: StorageInterface):
    result = storage.remove_chat(999)
    assert result is False

    storage.add_chat(2)
    result = storage.remove_chat(2)
    assert result is True
    assert storage.get_chat(2) is None


def test_add_link_non_existing_chat(storage: StorageInterface):
    result = storage.add_link(1, "https://example.com/", ["tag1"], ["filter1"])
    assert result is None


def test_add_link_success(storage: StorageInterface):
    storage.add_chat(1)
    result = storage.add_link(1, "https://example.com/", ["tag1", "tag2"], ["filter1"])
    assert result is not None
    assert str(result.url) == "https://example.com/"
    assert set(result.tags) == {"tag1", "tag2"}
    assert set(result.filters) == {"filter1"}


def test_add_duplicate_link(storage: StorageInterface):
    storage.add_chat(1)
    first = storage.add_link(1, "https://example.com/", ["tag1"], ["filter1"])
    duplicate = storage.add_link(1, "https://example.com/", ["tag1"], ["filter1"])
    assert first is not None
    assert duplicate is None


def test_remove_link_non_existing_chat(storage: StorageInterface):
    result = storage.remove_link(999, "https://example.com/")
    assert result is None


def test_remove_link_non_existing_link(storage: StorageInterface):
    storage.add_chat(1)
    result = storage.remove_link(1, "https://nonexistent.com")
    assert result is None


def test_remove_link_success(storage: StorageInterface):
    storage.add_chat(1)
    added = storage.add_link(1, "https://example.com/", ["tag1"], ["filter1"])
    assert added is not None

    removed = storage.remove_link(1, "https://example.com/")
    assert removed is not None
    assert str(removed.url) == "https://example.com/"

    removed_again = storage.remove_link(1, "https://example.com/")
    assert removed_again is None


def test_get_links_non_existing_chat(storage: StorageInterface):
    links_resp = storage.get_links(999)
    assert links_resp.size == 0
    assert links_resp.links == []


def test_get_links_success(storage: StorageInterface):
    storage.add_chat(1)
    storage.add_link(1, "https://example.com/", ["tag1"], ["filter1"])
    storage.add_link(1, "https://example.org/", ["tag2"], ["filter2"])
    links_resp = storage.get_links(1)
    assert links_resp.size == 2
    urls = {str(link.url) for link in links_resp.links}
    assert urls == {"https://example.com/", "https://example.org/"}


def test_get_all_unique_links_chat_ids(storage: StorageInterface):
    storage.add_chat(1)
    storage.add_chat(2)
    storage.add_chat(3)
    storage.add_link(1, "https://example.com/", ["tag1"], ["filter1"])
    storage.add_link(1, "https://example.org/", ["tag1"], ["filter1"])
    storage.add_link(2, "https://example.com/", ["tag2"], ["filter2"])
    storage.add_link(2, "https://example.net", ["tag2"], ["filter2"])
    storage.add_link(3, "https://example.org/", ["tag3"], ["filter3"])
    storage.add_link(3, "https://example.net", ["tag3"], ["filter3"])
    storage.add_link(3, "https://example.info", ["tag3"], ["filter3"])

    expected = [
        ("https://example.com/", {1, 2}),
        ("https://example.org/", {1, 3}),
        ("https://example.net", {2, 3}),
        ("https://example.info", {3}),
    ]

    for ind, (url, chat_ids) in enumerate(storage.get_all_unique_links_chat_ids()):
        assert url, chat_ids == expected[ind]
