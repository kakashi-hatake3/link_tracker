import asyncio
import logging

from telethon import TelegramClient, events

from src.handlers import chat_id_cmd_handler
from src.settings import TGBotSettings

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


settings = TGBotSettings()  # type: ignore[call-arg]

client = TelegramClient("bot_session", settings.api_id, settings.api_hash).start(
    bot_token=settings.token,
)

client.add_event_handler(
    chat_id_cmd_handler,
    events.NewMessage(pattern="/chat_id"),
)


async def dummy_func() -> None:
    await asyncio.sleep(1)


async def main() -> None:
    while True:
        await asyncio.gather(
            asyncio.create_task(dummy_func()),
        )


# Run the event loop to start receiving messages
logger.info("Run the event loop to start receiving messages")

with client:
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.exception(
            "Main loop raised error.",
            extra={"exc": exc},
        )
