from telethon.events import NewMessage

__all__ = ("chat_id_cmd_handler",)


async def chat_id_cmd_handler(
    event: NewMessage.Event,
) -> None:
    await event.client.send_message(
        entity=event.input_chat,
        message=f"chat_id is: {event.chat_id}",
        reply_to=event.message,
    )
