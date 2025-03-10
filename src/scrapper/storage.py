from typing import Dict, Optional, Union, Set

import os

from dotenv import load_dotenv
from pydantic import HttpUrl

from src.scrapper.database import SQLStorage, ORMStorage, StorageInterface
from src.scrapper.models import ChatInfo, LinkResponse, ListLinksResponse


load_dotenv()


class ScrapperStorage(StorageInterface):
    def __init__(self, db_url: str = os.getenv("DB_URL")) -> None:
        access_type = os.getenv("ACCESS_TYPE", "ORM").upper()
        self.impl: StorageInterface
        if access_type == "SQL":
            self.impl = SQLStorage(db_url)
        else:
            self.impl = ORMStorage(db_url)

    def add_chat(self, chat_id: int) -> None:
        return self.impl.add_chat(chat_id)

    def remove_chat(self, chat_id: int) -> bool:
        return self.impl.remove_chat(chat_id)

    def get_chat(self, chat_id: int) -> Optional[ChatInfo]:
        return self.impl.get_chat(chat_id)

    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters:list[str],
    ) -> Optional[LinkResponse]:
        return self.impl.add_link(chat_id, url, tags, filters)

    def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        return self.impl.remove_link(chat_id, url)

    def get_links(self, chat_id: int) -> ListLinksResponse:
        return self.impl.get_links(chat_id)

    def get_all_unique_links_chat_ids(self) -> Dict[str, Set[int]]:
        return self.impl.get_all_unique_links_chat_ids()
