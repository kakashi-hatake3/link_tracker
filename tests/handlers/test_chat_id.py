from unittest.mock import Mock

import pytest

from src.handlers import chat_id_cmd_handler


@pytest.mark.asyncio
async def test_chat_id_cmd_handler(mock_event: Mock) -> None:
    await chat_id_cmd_handler(mock_event)

    mock_event.client.send_message.assert_called_once_with(
        entity=mock_event.input_chat,
        message="chat_id is: 123456789",
        reply_to=mock_event.message,
    )
