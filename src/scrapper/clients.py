import logging
from datetime import datetime, timezone
from typing import Optional, List
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
        parsed = urlparse(url)
        if parsed.netloc != "github.com":
            return None, None
        parts = parsed.path.strip("/").split("/")
        return (parts[0], parts[1]) if len(parts) >= 2 else (None, None)

    @staticmethod
    def _parse_stackoverflow_url(url: str) -> Optional[str]:
        parsed = urlparse(url)
        if "stackoverflow.com" not in parsed.netloc:
            return None
        parts = parsed.path.strip("/").split("/")
        return parts[1] if len(parts) >= 2 and parts[0] == "questions" else None


class GitHubClient(BaseClient):
    BASE_URL = "https://api.github.com"

    async def get_new_updates(self, url: HttpUrl, last_check: Optional[datetime]) -> List[UpdateDetail]:
        owner, repo = self._parse_github_url(str(url))
        if not owner or not repo:
            return []

        new_updates: List[UpdateDetail] = []
        if last_check is None:
            return new_updates

        pr_api_url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {"state": "all", "sort": "created", "direction": "asc", "since": last_check.isoformat()} # мб добавить , "since": last_check.isoformat()
        async with self.session.get(pr_api_url, params=params) as response:
            if response.status == HTTP_200_OK:
                pulls = await response.json()
                for pr in pulls:
                    created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                    if created_at > last_check:
                        new_updates.append(UpdateDetail(
                            platform="GitHub",
                            update_type="PR",
                            title=pr.get("title", "No Title"),
                            username=pr.get("user", {}).get("login", "Unknown"),
                            created_at=created_at,
                            preview=(pr.get("body") or "")[:200],
                        ))

        issues_api_url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        params = {"state": "all", "sort": "created", "direction": "asc", "since": last_check.isoformat()}
        async with self.session.get(issues_api_url, params=params) as response:
            if response.status == HTTP_200_OK:
                issues = await response.json()
                for issue in issues:
                    if "pull_request" in issue:
                        continue
                    created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
                    if created_at > last_check:
                        new_updates.append(UpdateDetail(
                            platform="GitHub",
                            update_type="Issue",
                            title=issue.get("title", "No Title"),
                            username=issue.get("user", {}).get("login", "Unknown"),
                            created_at=created_at,
                            preview=(issue.get("body") or "")[:200],
                        ))
        return new_updates


class StackOverflowClient(BaseClient):
    BASE_URL = "https://api.stackexchange.com/2.3"

    async def get_new_updates(self, url: HttpUrl, last_check: Optional[datetime]) -> List[UpdateDetail]:
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
        params = {
            "site": "stackoverflow",
            "sort": "creation",
            "order": "asc",
            "filter": "withbody",
        }
        async with self.session.get(answers_api_url, params=params) as response:
            if response.status == HTTP_200_OK:
                data = await response.json()
                for answer in data.get("items", []):
                    creation_date = answer.get("creation_date")
                    if creation_date:
                        created_at = datetime.fromtimestamp(creation_date, tz=timezone.utc)
                        if created_at > last_check:
                            new_updates.append(UpdateDetail(
                                platform="StackOverflow",
                                update_type="Answer",
                                title=question_title,
                                username=answer.get("owner", {}).get("display_name", "Unknown"),
                                created_at=created_at,
                                preview=(answer.get("body") or "")[:200],
                            ))
        comments_api_url = f"{self.BASE_URL}/questions/{question_id}/comments"
        params = {
            "site": "stackoverflow",
            "sort": "creation",
            "order": "asc",
            "filter": "withbody",
        }
        async with self.session.get(comments_api_url, params=params) as response:
            if response.status == HTTP_200_OK:
                data = await response.json()
                for comment in data.get("items", []):
                    creation_date = comment.get("creation_date")
                    if creation_date:
                        created_at = datetime.fromtimestamp(creation_date, tz=timezone.utc)
                        if created_at > last_check:
                            new_updates.append(UpdateDetail(
                                platform="StackOverflow",
                                update_type="Comment",
                                title=question_title,
                                username=comment.get("owner", {}).get("display_name", "Unknown"),
                                created_at=created_at,
                                preview=(comment.get("body") or "")[:200],
                            ))
        return new_updates
