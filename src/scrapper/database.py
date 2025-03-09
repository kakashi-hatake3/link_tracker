from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Set, Type
from pydantic import HttpUrl

from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, Table, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, DeclarativeBase

from src.scrapper.models import ChatInfo, LinkResponse, ListLinksResponse


class StorageInterface(ABC):
    @abstractmethod
    def add_chat(self, chat_id: int) -> None:
        """Добавить новый чат."""
        pass

    @abstractmethod
    def remove_chat(self, chat_id: int) -> bool:
        """Удалить чат."""
        pass

    @abstractmethod
    def get_chat(self, chat_id: int) -> Optional[ChatInfo]:
        """Получить информацию о чате."""
        pass

    @abstractmethod
    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: List[str],
        filters: List[str],
    ) -> Optional[LinkResponse]:
        """Добавить ссылку для отслеживания."""
        pass

    @abstractmethod
    def remove_link(self, chat_id: int, url: HttpUrl) -> Optional[LinkResponse]:
        """Удалить ссылку из отслеживания."""
        pass

    @abstractmethod
    def get_links(self, chat_id: int) -> ListLinksResponse:
        """Получить все отслеживаемые ссылки чата."""
        pass

    @abstractmethod
    def get_all_unique_links_chat_ids(self) -> Dict[str, Set[int]]:
        """Получить словарь уникальных ссылок и множества чатов, отслеживающих их."""
        pass


Base: Type[DeclarativeBase] = declarative_base()

# Ассоциативные таблицы для связи многие ко многим
link_tags = Table(
    "link_tags",
    Base.metadata,
    Column("link_id", Integer, ForeignKey("links.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

link_filters = Table(
    "link_filters",
    Base.metadata,
    Column("link_id", Integer, ForeignKey("links.id"), primary_key=True),
    Column("filter_id", Integer, ForeignKey("filters.id"), primary_key=True),
)

class Chat(Base):
    __tablename__ = "chats"
    chat_id = Column(Integer, primary_key=True, index=True)
    links = relationship("Link", back_populates="chat", cascade="all, delete-orphan")

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.chat_id"), nullable=False)
    url = Column(String, nullable=False)
    chat = relationship("Chat", back_populates="links")
    tags = relationship("Tag", secondary=link_tags, back_populates="links")
    filters = relationship("Filter", secondary=link_filters, back_populates="links")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    links = relationship("Link", secondary=link_tags, back_populates="tags")

class Filter(Base):
    __tablename__ = "filters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    links = relationship("Link", secondary=link_filters, back_populates="filters")


def link_to_schema(link: Link) -> LinkResponse:
    return LinkResponse(
        id=link.id,
        url=link.url,
        tags=[tag.name for tag in link.tags],
        filters=[flt.name for flt in link.filters],
    )

def chat_to_schema(chat: Chat) -> ChatInfo:
    return ChatInfo(
        chat_id=chat.chat_id,
        links=[link_to_schema(link) for link in chat.links],
    )


class ORMStorage(StorageInterface):
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
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
        tags: List[str],
        filters: List[str],
    ) -> Optional[LinkResponse]:
        session = self.Session()
        try:
            chat = session.get(Chat, chat_id)
            if not chat:
                return None

            # Проверяем, не добавлена ли уже ссылка
            existing = session.query(Link).filter(
                Link.chat_id == chat_id, Link.url == str(url)
            ).first()
            if existing:
                return None

            link = Link(chat_id=chat_id, url=str(url))
            # Обработка тегов
            for tag_name in tags:
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                link.tags.append(tag)
            # Обработка фильтров
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
            link = session.query(Link).filter(
                Link.chat_id == chat_id, Link.url == str(url)
            ).first()
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
            result: Dict[str, Set[int]] = {}
            # Получаем все ссылки и соответствующие chat_id
            links = session.query(Link.url, Link.chat_id).all()
            # Группируем chat_id по url
            for url, chat_id in links:
                if url not in result:
                    result[url] = set()
                result[url].add(chat_id)
            return result
        finally:
            session.close()


class SQLStorage(StorageInterface):
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        with self.engine.connect() as conn:
            Base.metadata.create_all(self.engine)

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
                # Получаем ссылки через get_links
                links_resp = self.get_links(chat_id)
                return ChatInfo(chat_id=chat_id, links=links_resp.links)
            return None

    def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: List[str],
        filters: List[str],
    ) -> Optional[LinkResponse]:
        # Проверяем существование чата
        if not self.get_chat(chat_id):
            return None

        check_query = text("SELECT id FROM links WHERE chat_id = :chat_id AND url = :url")
        with self.engine.connect() as conn:
            if conn.execute(check_query, {"chat_id": chat_id, "url": str(url)}).fetchone():
                return None

            insert_link = text(
                "INSERT INTO links (chat_id, url) VALUES (:chat_id, :url) RETURNING id"
            )
            result = conn.execute(insert_link, {"chat_id": chat_id, "url": str(url)})
            link_row = result.fetchone()
            if not link_row:
                return None
            link_id = link_row.id

            # Обработка тегов
            for tag in tags:
                upsert_tag = text(
                    """
                    INSERT INTO tags (name) VALUES (:name)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """
                )
                tag_result = conn.execute(upsert_tag, {"name": tag})
                tag_id = tag_result.fetchone().id
                link_tag = text(
                    "INSERT INTO link_tags (link_id, tag_id) VALUES (:link_id, :tag_id) ON CONFLICT DO NOTHING"
                )
                conn.execute(link_tag, {"link_id": link_id, "tag_id": tag_id})

            # Обработка фильтров
            for flt in filters:
                upsert_filter = text(
                    """
                    INSERT INTO filters (name) VALUES (:name)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """
                )
                filter_result = conn.execute(upsert_filter, {"name": flt})
                filter_id = filter_result.fetchone().id
                link_filter = text(
                    "INSERT INTO link_filters (link_id, filter_id) VALUES (:link_id, :filter_id) ON CONFLICT DO NOTHING"
                )
                conn.execute(link_filter, {"link_id": link_id, "filter_id": filter_id})

            conn.commit()

            # Собираем данные для LinkResponse
            # Получаем теги
            select_tags = text(
                """
                SELECT t.name FROM tags t
                JOIN link_tags lt ON t.id = lt.tag_id
                WHERE lt.link_id = :link_id
                """
            )
            tag_names = [r.name for r in conn.execute(select_tags, {"link_id": link_id})]
            # Получаем фильтры
            select_filters = text(
                """
                SELECT f.name FROM filters f
                JOIN link_filters lf ON f.id = lf.filter_id
                WHERE lf.link_id = :link_id
                """
            )
            filter_names = [r.name for r in conn.execute(select_filters, {"link_id": link_id})]

            return LinkResponse(
                id=link_id,
                url=str(url),
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

            # Получаем теги
            select_tags = text(
                """
                SELECT t.name FROM tags t
                JOIN link_tags lt ON t.id = lt.tag_id
                WHERE lt.link_id = :link_id
                """
            )
            tag_names = [r.name for r in conn.execute(select_tags, {"link_id": link_id})]
            # Получаем фильтры
            select_filters = text(
                """
                SELECT f.name FROM filters f
                JOIN link_filters lf ON f.id = lf.filter_id
                WHERE lf.link_id = :link_id
                """
            )
            filter_names = [r.name for r in conn.execute(select_filters, {"link_id": link_id})]

            # Удаляем связи и ссылку
            conn.execute(text("DELETE FROM link_tags WHERE link_id = :link_id"), {"link_id": link_id})
            conn.execute(text("DELETE FROM link_filters WHERE link_id = :link_id"), {"link_id": link_id})
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
                    """
                )
                tag_names = [r.name for r in conn.execute(select_tags, {"link_id": link_id})]
                select_filters = text(
                    """
                    SELECT f.name FROM filters f
                    JOIN link_filters lf ON f.id = lf.filter_id
                    WHERE lf.link_id = :link_id
                    """
                )
                filter_names = [r.name for r in conn.execute(select_filters, {"link_id": link_id})]
                links_list.append(
                    LinkResponse(
                        id=link_id,
                        url=row.url,
                        tags=tag_names,
                        filters=filter_names,
                    )
                )
        return ListLinksResponse(links=links_list, size=len(links_list))

    def get_all_unique_links_chat_ids(self) -> Dict[str, Set[int]]:
        query = text("SELECT url, chat_id FROM links")
        result: Dict[str, Set[int]] = {}
        with self.engine.connect() as conn:
            rows = conn.execute(query).fetchall()
            # Группируем chat_id по url
            for row in rows:
                url, chat_id = row.url, row.chat_id
                if url not in result:
                    result[url] = set()
                result[url].add(chat_id)
        return result