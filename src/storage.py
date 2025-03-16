import os
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.database import Base, Chat
from src.models import Link, User

load_dotenv()


class StorageInterface(ABC):
    @abstractmethod
    def add_user(self, chat_id: int) -> None:
        """Добавить пользователя c указанным chat_id."""

    @abstractmethod
    def get_user(self, chat_id: int) -> Optional[User]:
        """Получить пользователя по chat_id."""


class ORMStorage(StorageInterface):
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_user(self, chat_id: int) -> None:
        session = self.Session()
        try:
            if not session.get(Chat, chat_id):
                user = Chat(chat_id=chat_id)
                session.add(user)
                session.commit()
        finally:
            session.close()

    def get_user(self, chat_id: int) -> Optional[User]:
        session = self.Session()
        try:
            user = session.get(Chat, chat_id)
            if user:
                links = [Link(url=link.url) for link in user.links]
                return User(chat_id=int(user.chat_id), tracked_links=links)
            return None
        finally:
            session.close()


class SQLStorage(StorageInterface):
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        with self.engine.connect():
            Base.metadata.create_all(self.engine)

    def add_user(self, chat_id: int) -> None:
        query = text("INSERT INTO chats (chat_id) VALUES (:chat_id) ON CONFLICT DO NOTHING")
        with self.engine.connect() as conn:
            conn.execute(query, {"chat_id": chat_id})
            conn.commit()

    def get_user(self, chat_id: int) -> Optional[User]:
        with self.engine.connect() as conn:
            user_row = conn.execute(
                text("SELECT chat_id FROM chats WHERE chat_id = :chat_id"),
                {"chat_id": chat_id},
            ).fetchone()
            if user_row:
                links_result = []  # type: ignore[var-annotated]
                try:  # noqa: SIM105
                    links_result = conn.execute(  # type: ignore[assignment]
                        text("SELECT url FROM links WHERE chat_id = :chat_id"),
                        {"chat_id": chat_id},
                    ).fetchall()
                except Exception:  # noqa: S110, BLE001
                    pass
                links = [Link(url=row.url) for row in links_result]
                return User(chat_id=user_row.chat_id, tracked_links=links)
            return None


class Storage(StorageInterface):
    def __init__(self, db_url: str = os.getenv("DB_URL")) -> None:  # type: ignore[assignment]
        access_type = os.getenv("ACCESS_TYPE", "ORM").upper()
        self.impl: StorageInterface
        if access_type == "SQL":
            self.impl = SQLStorage(db_url)
        else:
            self.impl = ORMStorage(db_url)

    def add_user(self, chat_id: int) -> None:
        return self.impl.add_user(chat_id)

    def get_user(self, chat_id: int) -> Optional[User]:
        return self.impl.get_user(chat_id)
