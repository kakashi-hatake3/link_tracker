from datetime import datetime
from typing import List, Optional

import aiohttp
from pydantic import HttpUrl

from src.scrapper.clients import GitHubClient, StackOverflowClient
from src.scrapper.models import UpdateDetail


class UpdateChecker:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.github = GitHubClient(session)
        self.stackoverflow = StackOverflowClient(session)

    async def get_new_updates(
        self,
        url: HttpUrl,
        last_check: Optional[datetime],
    ) -> List[UpdateDetail]:
        str_url = str(url).lower()
        if "github.com" in str_url:
            return await self.github.get_new_updates(url, last_check)
        elif "stackoverflow.com" in str_url:
            return await self.stackoverflow.get_new_updates(url, last_check)
        return []
