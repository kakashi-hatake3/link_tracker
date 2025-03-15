import os
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.database import Base, Chat
from src.models import Link, User


load_dotenv()

# class Storage:
#     def __init__(self) -> None:
#         self._users: Dict[int, User] = {}
#
#     def add_user(self, chat_id: int) -> None:
#         if chat_id not in self._users:
#             self._users[chat_id] = User(chat_id=chat_id)
#
#     def get_user(self, chat_id: int) -> Optional[User]:
#         return self._users.get(chat_id)
#
#     def add_link(self, chat_id: int, link: Link) -> bool:
#         user = self.get_user(chat_id)
#         if not user:
#             return False
#
#         if any(existing.url == link.url for existing in user.tracked_links):
#             return False
#
#         user.tracked_links.append(link)
#         return True
#
#     def remove_link(self, chat_id: int, url: str) -> bool:
#         user = self.get_user(chat_id)
#         if not user:
#             return False
#
#         initial_length = len(user.tracked_links)
#         user.tracked_links = [link for link in user.tracked_links if str(link.url) != url]
#         return len(user.tracked_links) < initial_length
#
#     def get_links(self, chat_id: int) -> list[Link]:
#         user = self.get_user(chat_id)
#         return user.tracked_links if user else []


class StorageInterface(ABC):
    @abstractmethod
    def add_user(self, chat_id: int) -> None:
        """Добавить пользователя с указанным chat_id."""
        pass

    @abstractmethod
    def get_user(self, chat_id: int) -> Optional[User]:
        """Получить пользователя по chat_id."""
        pass


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
                links = [Link(url=link.url, description=link.description)
                         for link in user.links]
                return User(chat_id=user.chat_id, tracked_links=links)
            return None
        finally:
            session.close()


class SQLStorage(StorageInterface):
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        with self.engine.connect() as conn:
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
                {"chat_id": chat_id}
            ).fetchone()
            if user_row:
                links_result = []  # type: ignore[var-annotated]
                try:
                    links_result = conn.execute(
                        text("SELECT url, description FROM links WHERE chat_id = :chat_id"),
                        {"chat_id": chat_id}
                    ).fetchall()
                except Exception:
                    pass
                links = [Link(url=row.url, description=row.description) for row in links_result]
                return User(chat_id=user_row.chat_id, tracked_links=links)
            return None


class Storage(StorageInterface):
    def __init__(self, db_url: str = os.getenv("DB_URL")) -> None:
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
