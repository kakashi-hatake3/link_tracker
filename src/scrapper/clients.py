import logging
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

import aiohttp
from pydantic import HttpUrl
from starlette.status import HTTP_200_OK

from src.scrapper.models import UpdateDetail

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    @staticmethod
    def _parse_github_url(url: str) -> tuple[Optional[str], Optional[str]]:
        parse_parts_count = 2
        parsed = urlparse(url)
        if parsed.netloc != "github.com":
            return None, None
        parts = parsed.path.strip("/").split("/")
        return (parts[0], parts[1]) if len(parts) >= parse_parts_count else (None, None)

    @staticmethod
    def _parse_stackoverflow_url(url: str) -> Optional[str]:
        parse_parts_count = 2
        parsed = urlparse(url)
        if "stackoverflow.com" not in parsed.netloc:
            return None
        parts = parsed.path.strip("/").split("/")
        return parts[1] if len(parts) >= parse_parts_count and parts[0] == "questions" else None


class GitHubClient(BaseClient):
    BASE_URL = "https://api.github.com"

    async def make_api_request(
        self,
        url: str,
        last_check: Optional[datetime],
        new_updates: List[UpdateDetail],
        is_issue: bool,
    ) -> None:
        params = {
            "state": "all",
            "sort": "created",
            "direction": "asc",
            "since": last_check.isoformat(),  # type: ignore[union-attr]
        }
        async with self.session.get(url, params=params) as response:
            if response.status == HTTP_200_OK:
                events = await response.json()
                for event in events:
                    if is_issue and "pull_request" in event:
                        continue
                    created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
                    if created_at > last_check:  # type: ignore[operator]
                        new_updates.append(
                            UpdateDetail(
                                platform="GitHub",
                                update_type="Issue" if is_issue else "PR",
                                title=event.get("title", "No Title"),
                                username=event.get("user", {}).get("login", "Unknown"),
                                created_at=created_at,
                                preview=(event.get("body") or "")[:200],
                            ),
                        )

    async def get_new_updates(
        self,
        url: HttpUrl,
        last_check: Optional[datetime],
    ) -> List[UpdateDetail]:
        owner, repo = self._parse_github_url(str(url))
        if not owner or not repo:
            return []

        new_updates: List[UpdateDetail] = []
        if last_check is None:
            return new_updates

        pr_api_url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"

        await self.make_api_request(pr_api_url, last_check, new_updates, False)

        issues_api_url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"

        await self.make_api_request(issues_api_url, last_check, new_updates, True)

        return new_updates


class StackOverflowClient(BaseClient):
    BASE_URL = "https://api.stackexchange.com/2.3"

    async def make_api_request(
        self,
        url: str,
        last_check: Optional[datetime],
        new_updates: List[UpdateDetail],
        question_title: str,
        is_answer: bool,
    ) -> None:
        params = {
            "site": "stackoverflow",
            "sort": "creation",
            "order": "asc",
            "filter": "withbody",
        }
        async with self.session.get(url, params=params) as response:
            if response.status == HTTP_200_OK:
                data = await response.json()
                for event in data.get("items", []):
                    creation_date = event.get("creation_date")
                    if creation_date:
                        created_at = datetime.fromtimestamp(creation_date, tz=timezone.utc)
                        if created_at > last_check:  # type: ignore[operator]
                            new_updates.append(
                                UpdateDetail(
                                    platform="StackOverflow",
                                    update_type="Answer" if is_answer else "Comment",
                                    title=question_title,
                                    username=event.get("owner", {}).get("display_name", "Unknown"),
                                    created_at=created_at,
                                    preview=(event.get("body") or "")[:200],
                                ),
                            )

    async def get_new_updates(
        self,
        url: HttpUrl,
        last_check: Optional[datetime],
    ) -> List[UpdateDetail]:
        question_id = self._parse_stackoverflow_url(str(url))
        if not question_id:
            return []

        new_updates: List[UpdateDetail] = []
        if last_check is None:
            return new_updates

        question_api_url = f"{self.BASE_URL}/questions/{question_id}"
        params = {
            "site": "stackoverflow",
            "filter": "!)rTkraRkW6wZ.J)YB)3)",  # Фильтр для получения title
        }
        async with self.session.get(question_api_url, params=params) as response:
            if response.status != HTTP_200_OK:
                return new_updates
            data = await response.json()
            items = data.get("items", [])
            if not items:
                return new_updates
            question_title = items[0].get("title", "No Title")

        answers_api_url = f"{self.BASE_URL}/questions/{question_id}/answers"

        await self.make_api_request(answers_api_url, last_check, new_updates, question_title, True)

        comments_api_url = f"{self.BASE_URL}/questions/{question_id}/comments"

        await self.make_api_request(
            comments_api_url,
            last_check,
            new_updates,
            question_title,
            False,
        )

        return new_updates
