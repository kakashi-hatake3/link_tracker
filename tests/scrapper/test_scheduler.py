from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scrapper.scheduler import UpdateScheduler
from src.scrapper.storage import ScrapperStorage


@pytest.fixture
def storage(postgres_container):
    storage = ScrapperStorage(postgres_container)
    storage.add_chat(123)
    storage.add_link(123, "https://github.com/test/repo", [], [])
    storage.add_link(123, "https://stackoverflow.com/questions/12345/test", [], [])
    return storage


@pytest.fixture
def update_checker():
    checker = MagicMock()
    checker.check_updates = AsyncMock()
    return checker


@pytest.fixture
def scheduler(storage, update_checker):
    return UpdateScheduler(storage, update_checker, "http://test.com")


@pytest.mark.asyncio
async def test_start_stop_scheduler(scheduler) -> None:
    """Тест запуска и остановки планировщика."""
    await scheduler.start(check_interval=1)
    assert scheduler._running is True
    assert scheduler._task is not None

    await scheduler.stop()
    assert scheduler._running is False
    assert scheduler._task.cancelled()


@pytest.mark.asyncio
async def test_check_updates_github(scheduler, update_checker) -> None:
    """Тест проверки обновлений для GitHub ссылки."""
    update_time = datetime.now()
    update_checker.check_updates.return_value = update_time

    await scheduler._check_all_links()

    update_checker.check_updates.assert_any_call("https://github.com/test/repo")

    assert scheduler._last_check["https://github.com/test/repo"] == update_time


@pytest.mark.asyncio
async def test_check_updates_stackoverflow(scheduler, update_checker) -> None:
    """Тест проверки обновлений для StackOverflow ссылки."""
    update_time = datetime.now()
    update_checker.check_updates.return_value = update_time

    await scheduler._check_all_links()

    update_checker.check_updates.assert_any_call("https://stackoverflow.com/questions/12345/test")

    assert scheduler._last_check["https://stackoverflow.com/questions/12345/test"] == update_time


@pytest.mark.asyncio
async def test_send_update_notification(scheduler) -> None:
    """Тест отправки уведомления об обновлении."""
    mock_response = AsyncMock()
    mock_response.status = 200

    mock_session = MagicMock()
    mock_session.post = AsyncMock(return_value=mock_response)

    update_time = datetime.now()
    scheduler.update_checker.check_updates.return_value = update_time

    old_time = datetime(2000, 1, 1)
    scheduler._last_check["https://github.com/test/repo"] = old_time

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session_class.return_value = mock_session
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock()

        await scheduler._check_all_links()

        mock_session.post.assert_called_once()

        assert scheduler._last_check["https://github.com/test/repo"] == update_time


@pytest.mark.asyncio
async def test_no_update_notification_for_first_check(scheduler) -> None:
    """Тест отсутствия уведомления при первой проверке."""
    update_time = datetime.now()
    scheduler.update_checker.check_updates.return_value = update_time

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock()

        await scheduler._check_all_links()

        assert not mock_session.post.called

        assert scheduler._last_check["https://github.com/test/repo"] == update_time


@pytest.mark.asyncio
async def test_handle_check_updates_error(scheduler) -> None:
    """Тест обработки ошибки при проверке обновлений."""
    scheduler.update_checker.check_updates.side_effect = Exception("Test error")

    await scheduler._check_all_links()

    assert "https://github.com/test/repo" not in scheduler._last_check
