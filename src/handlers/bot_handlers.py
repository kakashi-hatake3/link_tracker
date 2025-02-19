from typing import Optional
from urllib.parse import urlparse

from telethon import TelegramClient, events
from telethon.events import NewMessage
from pydantic import HttpUrl

from src.models import Link
from src.storage import Storage

HELP_MESSAGE = """
Доступные команды:
/start - регистрация пользователя
/help - вывод списка доступных команд
/track <url> [description] - начать отслеживание ссылки
/untrack <url> - прекратить отслеживание ссылки
/list - показать список отслеживаемых ссылок
"""

class BotHandler:
    def __init__(self, client: TelegramClient, storage: Storage):
        self.client = client
        self.storage = storage
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        self.client.add_event_handler(self._start_handler, events.NewMessage(pattern='/start'))
        self.client.add_event_handler(self._help_handler, events.NewMessage(pattern='/help'))
        self.client.add_event_handler(self._track_handler, events.NewMessage(pattern='/track'))
        self.client.add_event_handler(self._untrack_handler, events.NewMessage(pattern='/untrack'))
        self.client.add_event_handler(self._list_handler, events.NewMessage(pattern='/list'))
        self.client.add_event_handler(self._unknown_command_handler, events.NewMessage(pattern='/[a-zA-Z]+'))

    async def _start_handler(self, event: NewMessage.Event) -> None:
        self.storage.add_user(event.chat_id)
        await event.reply("Добро пожаловать! Используйте /help для просмотра доступных команд.")

    async def _help_handler(self, event: NewMessage.Event) -> None:
        await event.reply(HELP_MESSAGE)

    async def _track_handler(self, event: NewMessage.Event) -> None:
        if not event.message.text:
            return
            
        parts = event.message.text.split(maxsplit=2)
        if len(parts) < 2:
            await event.reply("Пожалуйста, укажите URL для отслеживания.")
            return

        url = parts[1]
        description = parts[2] if len(parts) > 2 else None

        try:
            parsed_url = urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                raise ValueError("Invalid URL")
                
            link = Link(url=url, description=description)
            if self.storage.add_link(event.chat_id, link):
                await event.reply(f"Ссылка {url} добавлена для отслеживания.")
            else:
                await event.reply("Эта ссылка уже отслеживается.")
        except Exception as e:
            await event.reply(f"Ошибка при добавлении ссылки: {str(e)}")

    async def _untrack_handler(self, event: NewMessage.Event) -> None:
        if not event.message.text:
            return
            
        parts = event.message.text.split()
        if len(parts) < 2:
            await event.reply("Пожалуйста, укажите URL для прекращения отслеживания.")
            return

        url = parts[1]
        if self.storage.remove_link(event.chat_id, url):
            await event.reply(f"Отслеживание ссылки {url} прекращено.")
        else:
            await event.reply("Указанная ссылка не отслеживается.")

    async def _list_handler(self, event: NewMessage.Event) -> None:
        links = self.storage.get_links(event.chat_id)
        if not links:
            await event.reply("Список отслеживаемых ссылок пуст.")
            return

        message = "Отслеживаемые ссылки:\n\n"
        for link in links:
            message += f"🔗 {link.url}"
            if link.description:
                message += f" - {link.description}"
            message += "\n"
        
        await event.reply(message)

    async def _unknown_command_handler(self, event: NewMessage.Event):
        if event.message.text and event.message.text.startswith('/'):
            known_commands = {'/start', '/help', '/track', '/untrack', '/list', 'chat_id'}
            command = event.message.text.split()[0]
            if command not in known_commands:
                await event.reply("Неизвестная команда. Используйте /help для просмотра доступных команд.") 