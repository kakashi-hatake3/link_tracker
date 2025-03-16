import logging

import aiohttp
from fastapi.encoders import jsonable_encoder
from starlette.status import HTTP_200_OK

from src.models import LinkUpdate

logger = logging.getLogger(__name__)


class NotificationSender:

    def __init__(self, bot_base_url: str) -> None:
        self.bot_base_url = bot_base_url

    async def send_update_notification(self, update: LinkUpdate) -> None:
        """Отправляет уведомление o6 обновлении через API бота."""
        try:
            bot_api_url = f"{self.bot_base_url}/api/v1/updates"
            logger.debug("before session")
            json_data = jsonable_encoder(update)
            logger.debug("after dump: %s", json_data)
            async with aiohttp.ClientSession() as session:
                logger.debug("getting session")
                async with session.post(bot_api_url, json=json_data) as response:
                    logger.debug("sending request: %d", response.status)
                    if response.status != HTTP_200_OK:
                        error_data = await response.json()
                        logger.error("Failed to send update notification: %s", error_data)
                    else:
                        logger.info(
                            "Successfully sent update notification for URL %s to %d chats",
                            update.url,
                            len(update.tg_chat_ids),
                        )

        except Exception:
            logger.exception("Error sending update notification")
