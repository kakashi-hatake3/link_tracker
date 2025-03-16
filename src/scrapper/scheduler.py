import asyncio
import contextlib
import datetime
import logging
from typing import Dict

from pydantic import HttpUrl

from src.models import LinkUpdate
from src.scrapper.sender import NotificationSender
from src.scrapper.storage import ScrapperStorage
from src.scrapper.update_checker import UpdateChecker
from src.settings import TGBotSettings

settings = TGBotSettings()  # type: ignore[call-arg]

logger = logging.getLogger(__name__)


class UpdateScheduler:
    def __init__(
        self,
        storage: ScrapperStorage,
        update_checker: UpdateChecker,
        bot_base_url: str = "http://localhost:7777",
    ) -> None:
        self.storage = storage  # type: ignore
        self.update_checker = update_checker
        self.bot_base_url = bot_base_url.rstrip("/")
        self._last_check: Dict[str, datetime.datetime] = {}
        self._running = False
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._next_update_id = 1
        self._sender = NotificationSender(bot_base_url)

    async def start(self, check_interval: int = settings.check_interval) -> None:
        """Запускает планировщик c указанным интервалом проверки в секундах."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop(check_interval))
        logger.info("Update scheduler started with interval %d seconds", check_interval)

    async def stop(self) -> None:
        """Останавливает планировщик."""
        if not self._running or not self._task:
            return

        self._running = False
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        logger.info("Update scheduler stopped")

    async def _check_loop(self, interval: int) -> None:
        """Основной цикл проверки обновлений."""
        while self._running:
            try:
                logger.info("updating..........")
                await self._check_all_links()
            except Exception:
                logger.exception("Error checking updates")

            await asyncio.sleep(interval)

    async def _check_all_links(self) -> None:
        for url_str, chat_ids in self.storage.get_all_unique_links_chat_ids():
            try:
                last_check = self._last_check.get(url_str)
                new_updates = await self.update_checker.get_new_updates(
                    HttpUrl(url_str),
                    last_check,
                )
                if new_updates:
                    for upd in new_updates:
                        message = (
                            f"Платформа: {upd.platform}\n"
                            f"Тип: {upd.update_type}\n"
                            f"Заголовок: {upd.title}\n"
                            f"Пользователь: {upd.username}\n"
                            f"Время создания: {upd.created_at.isoformat()}\n"
                            f"Превью: {upd.preview}"
                        )
                        update_obj = LinkUpdate(
                            id=self._next_update_id,  # type: ignore
                            url=HttpUrl(url_str),
                            tgChatIds=list(chat_ids),
                            description=message,
                        )
                        self._next_update_id += 1
                        await self._sender.send_update_notification(update_obj)
                    latest_time = max(upd.created_at for upd in new_updates)
                    self._last_check[url_str] = latest_time
                else:
                    self._last_check[url_str] = datetime.datetime.now(datetime.UTC)
            except Exception:  # noqa: PERF203
                logger.exception("Ошибка проверки URL %s", url_str)
