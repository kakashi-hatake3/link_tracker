import pytest

from src.storage import ORMStorage, SQLStorage, Storage, StorageInterface


@pytest.fixture(params=["ORM", "SQL", "WRAPPER"])
def storage(request, postgres_container, monkeypatch) -> StorageInterface:
    if request.param == "ORM":
        stor = ORMStorage(postgres_container)
    elif request.param == "SQL":
        stor = SQLStorage(postgres_container)
    elif request.param == "WRAPPER":
        monkeypatch.setenv("ACCESS_TYPE", "ORM")
        stor = Storage(postgres_container)
    else:
        raise ValueError("Unknown storage type")
    return stor


def test_get_user_not_exist(storage: StorageInterface) -> None:
    user = storage.get_user(9999)
    assert user is None

def test_add_and_get_user(storage: StorageInterface) -> None:
    chat_id = 123
    storage.add_user(chat_id)
    user = storage.get_user(chat_id)
    assert user is not None
    assert user.chat_id == chat_id
    assert user.tracked_links == []

def test_add_duplicate_user(storage: StorageInterface) -> None:
    chat_id = 456
    storage.add_user(chat_id)
    storage.add_user(chat_id)
    user = storage.get_user(chat_id)
    assert user is not None
    assert user.chat_id == chat_id
