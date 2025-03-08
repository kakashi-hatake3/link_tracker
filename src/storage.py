from typing import Dict, Optional

from src.models import Link, User


class Storage:
    def __init__(self) -> None:
        self._users: Dict[int, User] = {}

    def add_user(self, chat_id: int) -> None:
        if chat_id not in self._users:
            self._users[chat_id] = User(chat_id=chat_id)

    def get_user(self, chat_id: int) -> Optional[User]:
        return self._users.get(chat_id)

    def add_link(self, chat_id: int, link: Link) -> bool:
        user = self.get_user(chat_id)
        if not user:
            return False

        if any(existing.url == link.url for existing in user.tracked_links):
            return False

        user.tracked_links.append(link)
        return True

    def remove_link(self, chat_id: int, url: str) -> bool:
        user = self.get_user(chat_id)
        if not user:
            return False

        initial_length = len(user.tracked_links)
        user.tracked_links = [link for link in user.tracked_links if str(link.url) != url]
        return len(user.tracked_links) < initial_length

    def get_links(self, chat_id: int) -> list[Link]:
        user = self.get_user(chat_id)
        return user.tracked_links if user else []
