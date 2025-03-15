from typing import Type

from sqlalchemy import Column, Integer
from sqlalchemy.orm import declarative_base, relationship, DeclarativeBase


Base: Type[DeclarativeBase] = declarative_base()


class Chat(Base):
    __tablename__ = "chats"
    chat_id = Column(Integer, primary_key=True, index=True)
    links = relationship("Link", back_populates="chat", cascade="all, delete-orphan")
