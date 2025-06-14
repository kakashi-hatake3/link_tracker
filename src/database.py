from typing import Type

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import DeclarativeBase, declarative_base, relationship

Base: Type[DeclarativeBase] = declarative_base()


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


class Link(Base):  # type: ignore[valid-type]
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.chat_id"), nullable=False)
    url = Column(String, nullable=False)
    chat = relationship("Chat", back_populates="links")
    tags = relationship("Tag", secondary=link_tags, back_populates="links")
    filters = relationship("Filter", secondary=link_filters, back_populates="links")


class Chat(Base):  # type: ignore[valid-type]
    __tablename__ = "chats"
    chat_id = Column(Integer, primary_key=True, index=True)
    links = relationship("Link", back_populates="chat", cascade="all, delete-orphan")


class Tag(Base):  # type: ignore[valid-type]
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    links = relationship("Link", secondary=link_tags, back_populates="tags")


class Filter(Base):  # type: ignore[valid-type]
    __tablename__ = "filters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    links = relationship("Link", secondary=link_filters, back_populates="filters")
