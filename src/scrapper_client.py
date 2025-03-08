from typing import Optional

import aiohttp
from fastapi.encoders import jsonable_encoder
from pydantic import HttpUrl
from starlette.status import HTTP_200_OK

from src.scrapper.models import AddLinkRequest, LinkResponse, ListLinksResponse, RemoveLinkRequest


class ScrapperClient:
    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self.base_url = base_url.rstrip("/")

    async def register_chat(self, chat_id: int) -> bool:
        async with (
            aiohttp.ClientSession() as session,
            session.post(f"{self.base_url}/tg-chat/{chat_id}") as response,
        ):
            return response.status == HTTP_200_OK

    async def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
    ) -> Optional[LinkResponse]:

        request = AddLinkRequest(
            link=url,
            tags=tags,
            filters=filters,
        )

        async with aiohttp.ClientSession() as session:
            headers = {"Tg-Chat-Id": str(chat_id)}
            async with session.post(
                f"{self.base_url}/links",
                headers=headers,
                json=jsonable_encoder(request),
            ) as response:
                if response.status == HTTP_200_OK:
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
                if response.status == HTTP_200_OK:
                    return LinkResponse.model_validate(await response.json())
                return None

    async def get_links(self, chat_id: int) -> list[LinkResponse]:
        async with aiohttp.ClientSession() as session:
            headers = {"Tg-Chat-Id": str(chat_id)}
            async with session.get(f"{self.base_url}/links", headers=headers) as response:
                if response.status == HTTP_200_OK:
                    data = await response.json()
                    return ListLinksResponse.model_validate(data).links
                return []
