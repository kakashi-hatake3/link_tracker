import logging
from urllib.parse import urlparse

from fastapi import HTTPException
from telethon import TelegramClient, events
from telethon.events import NewMessage
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

from src.scrapper_client import ScrapperClient
from src.storage import Storage

HELP_MESSAGE = """
Доступные команды:
/start - регистрация пользователя
/help - вывод списка доступных команд
/track <url> [description] - начать отслеживание ссылки
/untrack <url> - прекратить отслеживание ссылки
/list - показать список отслеживаемых ссылок
"""


logger = logging.getLogger(__name__)


class BotHandler:
    def __init__(self, client: TelegramClient, storage: Storage) -> None:
        self.client = client
        self.storage = storage
        self.scrapper = ScrapperClient()
        self._setup_handlers()

    @classmethod
    async def create(cls, client: TelegramClient, storage: Storage) -> "BotHandler":
        """Фабричный метод для создания экземпляра BotHandler."""
        handler = cls(client, storage)
        await handler.register_commands()
        return handler

    async def register_commands(self) -> None:
        """Регистрирует команды бота в Telegram."""
        commands = [
            BotCommand(command="start", description="Регистрация пользователя"),
            BotCommand(command="help", description="Вывод списка доступных команд"),
            BotCommand(command="track", description="Начать отслеживание ссылки"),
            BotCommand(command="untrack", description="Прекратить отслеживание ссылки"),
            BotCommand(command="list", description="Показать список отслеживаемых ссылок"),
        ]
        await self.client(
            SetBotCommandsRequest(
                scope=BotCommandScopeDefault(),
                lang_code="ru",
                commands=commands,
            ),
        )

    def _setup_handlers(self) -> None:
        self.client.add_event_handler(self._start_handler, events.NewMessage(pattern="/start"))
        self.client.add_event_handler(self._help_handler, events.NewMessage(pattern="/help"))
        self.client.add_event_handler(self._track_handler, events.NewMessage(pattern="/track"))
        self.client.add_event_handler(self._untrack_handler, events.NewMessage(pattern="/untrack"))
        self.client.add_event_handler(self._list_handler, events.NewMessage(pattern="/list"))
        self.client.add_event_handler(
            self._unknown_command_handler,
            events.NewMessage(pattern="/[a-zA-Z]+"),
        )

    async def _start_handler(self, event: NewMessage.Event) -> None:
        chat_id = event.chat_id
        self.storage.add_user(chat_id)

        # Регистрируем чат в scrapper API
        if await self.scrapper.register_chat(chat_id):
            await event.reply("Добро пожаловать! Используйте /help для просмотра доступных команд.")
        else:
            await event.reply("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")

    async def _help_handler(self, event: NewMessage.Event) -> None:
        await event.reply(HELP_MESSAGE)

    def _validate_url(self, url_to_validate: str) -> None:
        parsed_url = urlparse(url_to_validate)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValueError("Invalid URL")

    async def _track_handler(self, event: NewMessage.Event) -> None:
        max_split = 2
        if not event.message.text:
            return

        parts = event.message.text.split(maxsplit=max_split)
        if len(parts) < max_split:
            await event.reply("Пожалуйста, укажите URL для отслеживания.")
            return

        url = parts[1]
        description = parts[2] if len(parts) > max_split else None

        try:
            self._validate_url(url)
            # Добавляем ссылку через scrapper API
            link_response = await self.scrapper.add_link(event.chat_id, url, description)
            if link_response:
                await event.reply(f"Ссылка {url} добавлена для отслеживания.")
            else:
                await event.reply(
                    "Эта ссылка уже отслеживается или произошла ошибка при добавлении.",
                )
        except ValueError as e:
            await event.reply(f"Некорректный URL: {e}")
        except HTTPException as e:
            await event.reply(f"Ошибка API: {e}")
        except Exception:
            logger.exception("Unexpected error in track handler")
            await event.reply("Произошла непредвиденная ошибка при добавлении ссылки")

    async def _untrack_handler(self, event: NewMessage.Event) -> None:
        max_split = 2
        if not event.message.text:
            return

        parts = event.message.text.split()
        if len(parts) < max_split:
            await event.reply("Пожалуйста, укажите URL для прекращения отслеживания.")
            return

        url = parts[1]
        try:
            # Удаляем ссылку через scrapper API
            link_response = await self.scrapper.remove_link(event.chat_id, url)
            if link_response:
                await event.reply(f"Отслеживание ссылки {url} прекращено.")
            else:
                await event.reply("Указанная ссылка не отслеживается.")
        except HTTPException as e:
            await event.reply(f"Ошибка API: {e}")
        except Exception:
            logger.exception("Unexpected error in untrack handler")
            await event.reply("Произошла непредвиденная ошибка при удалении ссылки")

    async def _list_handler(self, event: NewMessage.Event) -> None:
        try:
            # Получаем список ссылок через scrapper API
            links = await self.scrapper.get_links(event.chat_id)

            if not links:
                await event.reply("Список отслеживаемых ссылок пуст.")
                return

            message = "Отслеживаемые ссылки:\n\n"
            for link in links:
                message += f"🔗 {link.url}"
                if link.tags:
                    message += f" - {', '.join(link.tags)}"
                message += "\n"

            await event.reply(message)
        except HTTPException as e:
            await event.reply(f"Ошибка API: {e}")
        except Exception:
            logger.exception("Unexpected error in list handler")
            await event.reply("Произошла непредвиденная ошибка при получении списка ссылок")

    async def _unknown_command_handler(self, event: NewMessage.Event) -> None:
        if event.message.text and event.message.text.startswith("/"):
            known_commands = {"/start", "/help", "/track", "/untrack", "/list", "chat_id"}
            command = event.message.text.split()[0]
            if command not in known_commands:
                await event.reply(
                    "Неизвестная команда. Используйте /help для просмотра доступных команд.",
                )
