import os
from abc import ABC, abstractmethod
from typing import Dict, Optional, Set

from dotenv import load_dotenv
from pydantic import HttpUrl
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from src.database import Chat, Filter, Link, Tag
from src.scrapper.models import ChatInfo, LinkResponse, ListLinksResponse
from src.utils import chat_to_schema, link_to_schema

load_dotenv()


class StorageInterface(ABC):
    @abstractmethod
    def add_chat(self, chat_id: int) -> None:
        """Добавить новый чат."""

    @abstractmethod
    def remove_chat(self, chat_id: int) -> bool:
        """Удалить чат."""

    @abstractmethod
    def get_chat(self, chat_id: int) -> Optional[ChatInfo]:
        """Получить информацию o чате."""

    @abstractmethod
    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
    ) -> Optional[LinkResponse]:
        """Добавить ссылку для отслеживания."""

    @abstractmethod
    def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        """Удалить ссылку из отслеживания."""

    @abstractmethod
    def get_links(self, chat_id: int) -> ListLinksResponse:
        """Получить все отслеживаемые ссылки чата."""

    @abstractmethod
    def get_all_unique_links_chat_ids(self) -> Dict[str, Set[int]]:
        """Получить словарь уникальных ссылок и множества чатов, отслеживающих их."""


class ORMStorage(StorageInterface):
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def add_chat(self, chat_id: int) -> None:
        session = self.Session()
        try:
            if not session.get(Chat, chat_id):
                chat = Chat(chat_id=chat_id)
                session.add(chat)
                session.commit()
        finally:
            session.close()

    def remove_chat(self, chat_id: int) -> bool:
        session = self.Session()
        try:
            chat = session.get(Chat, chat_id)
            if chat:
                session.delete(chat)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_chat(self, chat_id: int) -> Optional[ChatInfo]:
        session = self.Session()
        try:
            chat = session.get(Chat, chat_id)
            if chat:
                return chat_to_schema(chat)
            return None
        finally:
            session.close()

    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
    ) -> Optional[LinkResponse]:
        session = self.Session()
        try:
            chat = session.get(Chat, chat_id)
            if not chat:
                return None

            existing = (
                session.query(Link).filter(Link.chat_id == chat_id, Link.url == str(url)).first()
            )
            if existing:
                return None

            link = Link(chat_id=chat_id, url=str(url))
            for tag_name in tags:
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                link.tags.append(tag)
            for filter_name in filters:
                flt = session.query(Filter).filter_by(name=filter_name).first()
                if not flt:
                    flt = Filter(name=filter_name)
                link.filters.append(flt)
            session.add(link)
            session.commit()
            session.refresh(link)
            return link_to_schema(link)
        finally:
            session.close()

    def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        session = self.Session()
        try:
            link = session.query(Link).filter(Link.chat_id == chat_id, Link.url == str(url)).first()
            if link:
                link_schema = link_to_schema(link)
                session.delete(link)
                session.commit()
                return link_schema
            return None
        finally:
            session.close()

    def get_links(self, chat_id: int) -> ListLinksResponse:
        session = self.Session()
        try:
            links = session.query(Link).filter(Link.chat_id == chat_id).all()
            schema_links = [link_to_schema(link) for link in links]
            return ListLinksResponse(links=schema_links, size=len(schema_links))
        finally:
            session.close()

    def get_all_unique_links_chat_ids(self) -> Dict[str, Set[int]]:
        session = self.Session()
        try:
            query = session.query(Link.url, func.array_agg(Link.chat_id)).group_by(Link.url)
            for url, chat_ids in query:
                yield url, set(chat_ids)
        finally:
            session.close()


class SQLStorage(StorageInterface):
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)

    def add_chat(self, chat_id: int) -> None:
        query = text("INSERT INTO chats (chat_id) VALUES (:chat_id) ON CONFLICT DO NOTHING")
        with self.engine.connect() as conn:
            conn.execute(query, {"chat_id": chat_id})
            conn.commit()

    def remove_chat(self, chat_id: int) -> bool:
        query = text("DELETE FROM chats WHERE chat_id = :chat_id RETURNING chat_id")
        with self.engine.connect() as conn:
            result = conn.execute(query, {"chat_id": chat_id})
            conn.commit()
            return result.fetchone() is not None

    def get_chat(self, chat_id: int) -> Optional[ChatInfo]:
        query = text("SELECT chat_id FROM chats WHERE chat_id = :chat_id")
        with self.engine.connect() as conn:
            result = conn.execute(query, {"chat_id": chat_id})
            row = result.fetchone()
            if row:
                links_resp = self.get_links(chat_id)
                return ChatInfo(chat_id=chat_id, links=links_resp.links)
            return None

    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
    ) -> Optional[LinkResponse]:
        if not self.get_chat(chat_id):
            return None

        check_query = text("SELECT id FROM links WHERE chat_id = :chat_id AND url = :url")
        with self.engine.connect() as conn:
            if conn.execute(check_query, {"chat_id": chat_id, "url": str(url)}).fetchone():
                return None

            insert_link = text(
                "INSERT INTO links (chat_id, url) VALUES (:chat_id, :url) RETURNING id",
            )
            result = conn.execute(insert_link, {"chat_id": chat_id, "url": str(url)})
            link_row = result.fetchone()
            if not link_row:
                return None
            link_id = link_row.id

            for tag in tags:
                upsert_tag = text(
                    """
                    INSERT INTO tags (name) VALUES (:name)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                )
                tag_result = conn.execute(upsert_tag, {"name": tag})
                tag_id = tag_result.fetchone().id  # type: ignore[union-attr]
                link_tag = text(
                    "INSERT INTO link_tags (link_id, tag_id) "
                    "VALUES (:link_id, :tag_id) ON CONFLICT DO NOTHING",
                )
                conn.execute(link_tag, {"link_id": link_id, "tag_id": tag_id})

            for flt in filters:
                upsert_filter = text(
                    """
                    INSERT INTO filters (name) VALUES (:name)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                )
                filter_result = conn.execute(upsert_filter, {"name": flt})
                filter_id = filter_result.fetchone().id  # type: ignore[union-attr]
                link_filter = text(
                    "INSERT INTO link_filters (link_id, filter_id) "
                    "VALUES (:link_id, :filter_id) ON CONFLICT DO NOTHING",
                )
                conn.execute(link_filter, {"link_id": link_id, "filter_id": filter_id})

            conn.commit()

            select_tags = text(
                """
                SELECT t.name FROM tags t
                JOIN link_tags lt ON t.id = lt.tag_id
                WHERE lt.link_id = :link_id
                """,
            )
            tag_names = [r.name for r in conn.execute(select_tags, {"link_id": link_id})]
            select_filters = text(
                """
                SELECT f.name FROM filters f
                JOIN link_filters lf ON f.id = lf.filter_id
                WHERE lf.link_id = :link_id
                """,
            )
            filter_names = [r.name for r in conn.execute(select_filters, {"link_id": link_id})]

            return LinkResponse(
                id=link_id,
                url=HttpUrl(str(url)),
                tags=tag_names,
                filters=filter_names,
            )

    def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        select_link = text("SELECT id FROM links WHERE chat_id = :chat_id AND url = :url")
        with self.engine.connect() as conn:
            row = conn.execute(select_link, {"chat_id": chat_id, "url": str(url)}).fetchone()
            if not row:
                return None
            link_id = row.id

            select_tags = text(
                """
                SELECT t.name FROM tags t
                JOIN link_tags lt ON t.id = lt.tag_id
                WHERE lt.link_id = :link_id
                """,
            )
            tag_names = [r.name for r in conn.execute(select_tags, {"link_id": link_id})]
            select_filters = text(
                """
                SELECT f.name FROM filters f
                JOIN link_filters lf ON f.id = lf.filter_id
                WHERE lf.link_id = :link_id
                """,
            )
            filter_names = [r.name for r in conn.execute(select_filters, {"link_id": link_id})]

            conn.execute(
                text("DELETE FROM link_tags WHERE link_id = :link_id"),
                {"link_id": link_id},
            )
            conn.execute(
                text("DELETE FROM link_filters WHERE link_id = :link_id"),
                {"link_id": link_id},
            )
            delete_link = text("DELETE FROM links WHERE id = :link_id RETURNING id, url")
            result = conn.execute(delete_link, {"link_id": link_id})
            conn.commit()
            deleted = result.fetchone()
            if deleted:
                return LinkResponse(
                    id=deleted.id,
                    url=deleted.url,
                    tags=tag_names,
                    filters=filter_names,
                )
            return None

    def get_links(self, chat_id: int) -> ListLinksResponse:
        links_list = []
        select_links = text("SELECT id, url FROM links WHERE chat_id = :chat_id")
        with self.engine.connect() as conn:
            for row in conn.execute(select_links, {"chat_id": chat_id}):
                link_id = row.id
                select_tags = text(
                    """
                    SELECT t.name FROM tags t
                    JOIN link_tags lt ON t.id = lt.tag_id
                    WHERE lt.link_id = :link_id
                    """,
                )
                tag_names = [r.name for r in conn.execute(select_tags, {"link_id": link_id})]
                select_filters = text(
                    """
                    SELECT f.name FROM filters f
                    JOIN link_filters lf ON f.id = lf.filter_id
                    WHERE lf.link_id = :link_id
                    """,
                )
                filter_names = [r.name for r in conn.execute(select_filters, {"link_id": link_id})]
                links_list.append(
                    LinkResponse(
                        id=link_id,
                        url=row.url,
                        tags=tag_names,
                        filters=filter_names,
                    ),
                )
        return ListLinksResponse(links=links_list, size=len(links_list))

    def get_all_unique_links_chat_ids(self) -> Dict[str, Set[int]]:
        query = text("SELECT url, array_agg(chat_id) AS chat_ids FROM links GROUP BY url")
        with self.engine.connect() as conn:
            result = conn.execute(query)
            for row in result:
                url = row[0]
                chat_ids = set(row[1])
                yield url, chat_ids


class ScrapperStorage(StorageInterface):
    def __init__(self, db_url: str = os.getenv("DB_URL")) -> None:  # type: ignore[arg-type, assignment]
        access_type = os.getenv("ACCESS_TYPE", "ORM").upper()
        self.impl: StorageInterface
        if access_type == "SQL":
            self.impl = SQLStorage(db_url)
        else:
            self.impl = ORMStorage(db_url)

    def add_chat(self, chat_id: int) -> None:
        return self.impl.add_chat(chat_id)

    def remove_chat(self, chat_id: int) -> bool:
        return self.impl.remove_chat(chat_id)

    def get_chat(self, chat_id: int) -> Optional[ChatInfo]:
        return self.impl.get_chat(chat_id)

    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
    ) -> Optional[LinkResponse]:
        return self.impl.add_link(chat_id, url, tags, filters)

    def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        return self.impl.remove_link(chat_id, url)

    def get_links(self, chat_id: int) -> ListLinksResponse:
        return self.impl.get_links(chat_id)

    def get_all_unique_links_chat_ids(self) -> Dict[str, Set[int]]:
        return self.impl.get_all_unique_links_chat_ids()
