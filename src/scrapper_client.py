from typing import List, Optional

import aiohttp
from fastapi.encoders import jsonable_encoder
from pydantic import HttpUrl

from src.scrapper.models import AddLinkRequest, LinkResponse, ListLinksResponse, RemoveLinkRequest


class ScrapperClient:
    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self.base_url = base_url.rstrip("/")

    async def register_chat(self, chat_id: int) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/tg-chat/{chat_id}") as response:
                return response.status == 200

    async def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        description: Optional[str] = None,
    ) -> Optional[LinkResponse]:
        # Преобразуем описание в теги, если оно есть
        tags = [description] if description else []

        request = AddLinkRequest(
            link=url,
            tags=tags,
            filters=[],
        )

        async with aiohttp.ClientSession() as session:
            headers = {"Tg-Chat-Id": str(chat_id)}
            async with session.post(
                f"{self.base_url}/links",
                headers=headers,
                json=jsonable_encoder(request),
            ) as response:
                if response.status == 200:
                    return LinkResponse.model_validate(await response.json())
                return None

    async def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        request = RemoveLinkRequest(link=url)

        async with aiohttp.ClientSession() as session:
            headers = {"Tg-Chat-Id": str(chat_id)}
            async with session.delete(
                f"{self.base_url}/links",
                headers=headers,
                json=jsonable_encoder(request),
            ) as response:
                if response.status == 200:
                    return LinkResponse.model_validate(await response.json())
                return None

    async def get_links(self, chat_id: int) -> List[LinkResponse]:
        async with aiohttp.ClientSession() as session:
            headers = {"Tg-Chat-Id": str(chat_id)}
            async with session.get(f"{self.base_url}/links", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return ListLinksResponse.model_validate(data).links
                return []
