from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scrapper.scheduler import UpdateScheduler


class FakeStorage:
    def __init__(self) -> None:
        self._links = {
            "https://github.com/test/repo": {123},
            "https://stackoverflow.com/questions/12345/test": {456},
        }

    def get_all_unique_links_chat_ids(self):
        yield from self._links.items()

@pytest.fixture
def storage():
    return FakeStorage()

@pytest.fixture
def update_checker():
    checker = MagicMock()
    checker.get_new_updates = AsyncMock()
    return checker

@pytest.fixture
def scheduler(storage, update_checker):
    return UpdateScheduler(storage, update_checker, "http://test.com")

@pytest.mark.asyncio
async def test_start_stop_scheduler(scheduler) -> None:
    await scheduler.start(check_interval=1)
    assert scheduler._running is True
    assert scheduler._task is not None

    await scheduler.stop()
    assert scheduler._running is False
    assert scheduler._task.cancelled()

@pytest.mark.asyncio
async def test_check_updates_with_new_updates(scheduler, update_checker) -> None:
    update_detail1 = MagicMock()
    update_detail1.platform = "GitHub"
    update_detail1.update_type = "PR"
    update_detail1.title = "Test PR"
    update_detail1.username = "user1"
    update_detail1.created_at = datetime.now() + timedelta(seconds=10)
    update_detail1.preview = "Preview text 1"[:200]

    update_detail2 = MagicMock()
    update_detail2.platform = "GitHub"
    update_detail2.update_type = "Issue"
    update_detail2.title = "Test Issue"
    update_detail2.username = "user2"
    update_detail2.created_at = datetime.now() + timedelta(seconds=20)
    update_detail2.preview = "Preview text 2"[:200]

    update_checker.get_new_updates.return_value = [update_detail1, update_detail2]

    scheduler._last_check["https://github.com/test/repo"] = datetime.now()

    with patch("src.scrapper.sender.NotificationSender.send_update_notification", new=AsyncMock()) as mock_sender:
        await scheduler._check_all_links()

        assert mock_sender.call_count == 4
        expected_last_check = max(update_detail1.created_at, update_detail2.created_at)
        assert scheduler._last_check["https://github.com/test/repo"] == expected_last_check

@pytest.mark.asyncio
async def test_no_notification_on_first_check(scheduler, update_checker) -> None:
    update_detail = MagicMock()
    update_detail.platform = "GitHub"
    update_detail.update_type = "PR"
    update_detail.title = "Test PR"
    update_detail.username = "user1"
    update_detail.created_at = datetime.now() + timedelta(seconds=10)
    update_detail.preview = "Preview text"[:200]

    update_checker.get_new_updates.return_value = [update_detail]

    if "https://github.com/test/repo" in scheduler._last_check:
        del scheduler._last_check["https://github.com/test/repo"]

    with patch("src.scrapper.sender.NotificationSender.send_update_notification", new=AsyncMock()):
        await scheduler._check_all_links()
        assert scheduler._last_check["https://github.com/test/repo"] == update_detail.created_at

@pytest.mark.asyncio
async def test_handle_check_updates_error(scheduler, update_checker) -> None:
    scheduler.update_checker.get_new_updates.side_effect = Exception("Test error")

    await scheduler._check_all_links()

    for url, _ in scheduler.storage.get_all_unique_links_chat_ids():
        assert url not in scheduler._last_check
