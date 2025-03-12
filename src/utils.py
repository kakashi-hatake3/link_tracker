from src.scrapper.database import Chat, Link
from src.scrapper.models import LinkResponse, ChatInfo


def link_to_schema(link: Link) -> LinkResponse:
    return LinkResponse(
        id=link.id,
        url=link.url,
        tags=[tag.name for tag in link.tags],
        filters=[flt.name for flt in link.filters],
    )

def chat_to_schema(chat: Chat) -> ChatInfo:
    return ChatInfo(
        chat_id=chat.chat_id,
        links=[link_to_schema(link) for link in chat.links],
    )
