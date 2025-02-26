import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from pydantic import HttpUrl
from starlette.status import HTTP_200_OK

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    @staticmethod
    def _parse_github_url(url: str) -> tuple[Optional[str], Optional[str]]:
        """Извлекает owner и repo из GitHub URL."""
        max_split = 2
        parsed = urlparse(url)
        if parsed.netloc != "github.com":
            return None, None

        parts = parsed.path.strip("/").split("/")
        if len(parts) >= max_split:
            return parts[0], parts[1]
        return None, None

    @staticmethod
    def _parse_stackoverflow_url(url: str) -> Optional[str]:
        """Извлекает ID вопроса из StackOverflow URL."""
        max_split = 2
        parsed = urlparse(url)
        if "stackoverflow.com" not in parsed.netloc:
            return None

        parts = parsed.path.strip("/").split("/")
        if len(parts) >= max_split and parts[0] == "questions":
            return parts[1]
        return None


class GitHubClient(BaseClient):
    BASE_URL = "https://api.github.com"

    async def get_last_update(self, url: HttpUrl) -> Optional[datetime]:
        """Получает время последнего обновления репозитория."""
        owner, repo = self._parse_github_url(str(url))
        if not owner or not repo:
            return None

        api_url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        logger.debug("before getting api")
        async with self.session.get(api_url) as response:
            logger.debug("api response: %d", response.status)
            if response.status != HTTP_200_OK:
                return None

            data = await response.json()
            logger.debug("data %s", data)

            updated_at = data.get("updated_at")
            if not updated_at:
                return None

            return datetime.fromisoformat(updated_at.replace("Z", "+00:00"))


class StackOverflowClient(BaseClient):
    BASE_URL = "https://api.stackexchange.com/2.3"

    async def get_last_update(self, url: HttpUrl) -> Optional[datetime]:
        """Получает время последнего обновления вопроса."""
        question_id = self._parse_stackoverflow_url(str(url))
        if not question_id:
            return None

        api_url = f"{self.BASE_URL}/questions/{question_id}"
        params = {
            "site": "stackoverflow",
            "filter": "!9Z(-wzu0T",  # Фильтр, включающий только last_activity_date
        }

        async with self.session.get(api_url, params=params) as response:
            if response.status != HTTP_200_OK:
                return None

            data = await response.json()
            items = data.get("items", [])
            if not items:
                return None

            last_activity_date = items[0].get("last_activity_date")
            if not last_activity_date:
                return None

            return datetime.fromtimestamp(last_activity_date, tz=timezone.utc)


class UpdateChecker:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.github = GitHubClient(session)
        self.stackoverflow = StackOverflowClient(session)

    async def check_updates(self, url: HttpUrl) -> Optional[datetime]:
        """Проверяет обновления для URL."""
        str_url = str(url).lower()

        if "github.com" in str_url:
            return await self.github.get_last_update(url)
        elif "stackoverflow.com" in str_url:
            return await self.stackoverflow.get_last_update(url)

        return None
