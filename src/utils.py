from pydantic import HttpUrl

from src.database import Chat, Link
from src.scrapper.models import ChatInfo, LinkResponse


def link_to_schema(link: Link) -> LinkResponse:
    return LinkResponse(
        id=int(link.id),
        url=HttpUrl(str(link.url)),
        tags=[tag.name for tag in link.tags],
        filters=[flt.name for flt in link.filters],
    )


def chat_to_schema(chat: Chat) -> ChatInfo:
    return ChatInfo(
        chat_id=int(chat.chat_id),
        links=[link_to_schema(link) for link in chat.links],
    )
