import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set
import aiohttp
from fastapi.encoders import jsonable_encoder

from src.scrapper.storage import ScrapperStorage
from src.scrapper.clients import UpdateChecker
from src.models import LinkUpdate

logger = logging.getLogger(__name__)

class UpdateScheduler:
    def __init__(self, storage: ScrapperStorage, update_checker: UpdateChecker, bot_base_url: str = "http://localhost:7777"):
        self.storage = storage
        self.update_checker = update_checker
        self.bot_base_url = bot_base_url.rstrip('/')
        self._last_check: Dict[str, datetime] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._next_update_id = 1

    async def start(self, check_interval: int = 10):
        """Запускает планировщик с указанным интервалом проверки в секундах"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._check_loop(check_interval))
        logger.info("Update scheduler started with interval %d seconds", check_interval)

    async def stop(self):
        """Останавливает планировщик"""
        if not self._running or not self._task:
            return

        self._running = False
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logger.info("Update scheduler stopped")

    async def _check_loop(self, interval: int):
        """Основной цикл проверки обновлений"""
        while self._running:
            try:
                logger.info('updating..........')
                await self._check_all_links()
            except Exception as e:
                logger.error("Error checking updates: %s", str(e))

            await asyncio.sleep(interval)

    async def _check_all_links(self):
        """Проверяет обновления для всех отслеживаемых ссылок"""
        # Собираем все уникальные ссылки из всех чатов
        all_links: Dict[str, Set[int]] = {}
        for chat_info in self.storage._chats.values():
            for link in chat_info.links:
                str_url = str(link.url)
                if str_url not in all_links:
                    all_links[str_url] = set()
                all_links[str_url].add(chat_info.chat_id)
        logger.info("links: %s", all_links)
        # Проверяем каждую ссылку
        for url_str, chat_ids in all_links.items():
            try:
                last_update = await self.update_checker.check_updates(url_str)
                logger.info("last update: %s", last_update)
                if not last_update:
                    continue

                # Если это первая проверка или есть обновление
                if url_str not in self._last_check or last_update > self._last_check[url_str]:
                    # Если это не первая проверка, значит есть реальное обновление
                    if url_str in self._last_check:
                        logger.info("Found update for URL: %s", url_str)
                        # Создаем объект обновления
                        update = LinkUpdate(
                            id=self._next_update_id,
                            url=url_str,
                            tgChatIds=list(chat_ids)
                        )
                        self._next_update_id += 1

                        # Отправляем уведомление через API
                        await self._send_update_notification(update)

                    self._last_check[url_str] = last_update

            except Exception as e:
                logger.error("Error checking URL %s: %s", url_str, str(e))

    async def _send_update_notification(self, update: LinkUpdate):
        """Отправляет уведомление об обновлении через API бота"""
        try:
            bot_api_url = f"{self.bot_base_url}/api/v1/updates"
            logger.debug("before session")
            json_data = jsonable_encoder(update)
            logger.debug("after dump: %s", json_data)
            async with aiohttp.ClientSession() as session:
                logger.debug("getting session")
                async with session.post(bot_api_url, json=json_data) as response:
                    logger.debug("sending request: %d", response.status)
                    if response.status != 200:
                        error_data = await response.json()
                        logger.error("Failed to send update notification: %s", error_data)
                    else:
                        logger.info("Successfully sent update notification for URL %s to %d chats",
                                  update.url, len(update.tg_chat_ids))

        except Exception as e:
            logger.error("Error sending update notification: %s", str(e)) 