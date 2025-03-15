from sqlalchemy import (
    Column, Integer, String, ForeignKey, Table
)
from sqlalchemy.orm import relationship
from src.database import Base


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
