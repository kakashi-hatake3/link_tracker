import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import LinkUpdate
from src.scrapper.sender import NotificationSender

class FakeAiohttpResponse:
    def __init__(self, status, json_data=None):
        self.status = status
        self._json_data = json_data or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def json(self):
        return self._json_data


@pytest.mark.asyncio
async def test_send_update_notification_exception():
    update = LinkUpdate(
        id=3,
        url="https://github.com/owner/repo",
        tgChatIds=[321],
        description="Test update exception",
    )
    sender = NotificationSender("http://testbot.com")
    fake_session = AsyncMock()
    fake_session.post.side_effect = Exception("Test Exception")

    with patch("src.scrapper.sender.aiohttp.ClientSession") as mock_client_session, \
         patch("src.scrapper.sender.logger") as mock_logger:
        fake_context_manager = MagicMock()
        fake_context_manager.__aenter__.return_value = fake_session
        mock_client_session.return_value = fake_context_manager

        await sender.send_update_notification(update)

        mock_logger.exception.assert_called_with("Error sending update notification")
