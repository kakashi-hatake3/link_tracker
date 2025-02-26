from typing import Dict, List, Optional

from pydantic import HttpUrl

from src.scrapper.models import ChatInfo, LinkResponse


class ScrapperStorage:
    def __init__(self) -> None:
        self.chats: Dict[int, ChatInfo] = {}
        self._next_link_id: int = 1

    def add_chat(self, chat_id: int) -> None:
        """Добавить новый чат."""
        if chat_id not in self.chats:
            self.chats[chat_id] = ChatInfo(chat_id=chat_id)

    def remove_chat(self, chat_id: int) -> bool:
        """Удалить чат."""
        return bool(self.chats.pop(chat_id, None))

    def get_chat(self, chat_id: int) -> Optional[ChatInfo]:
        """Получить информацию o чате."""
        return self.chats.get(chat_id)

    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: List[str],
        filters: List[str],
    ) -> Optional[LinkResponse]:
        """Добавить ссылку для отслеживания."""
        chat = self.get_chat(chat_id)
        if not chat:
            return None

        # Проверяем, не отслеживается ли уже эта ссылка
        if any(str(link.url) == str(url) for link in chat.links):
            return None

        link = LinkResponse(
            id=self._next_link_id,
            url=url,
            tags=tags,
            filters=filters,
        )
        self._next_link_id += 1
        chat.links.append(link)
        return link

    def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        """Удалить ссылку из отслеживания."""
        chat = self.get_chat(chat_id)
        if not chat:
            return None

        for i, link in enumerate(chat.links):
            if str(link.url) == str(url):
                return chat.links.pop(i)
        return None

    def get_links(self, chat_id: int) -> List[LinkResponse]:
        """Получить все отслеживаемые ссылки чата."""
        chat = self.get_chat(chat_id)
        return chat.links if chat else []
