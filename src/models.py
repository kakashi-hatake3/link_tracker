from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Link(BaseModel):
    url: HttpUrl
    description: Optional[str] = None


class LinkUpdate(BaseModel):
    id: int
    url: HttpUrl
    description: Optional[str] = None
    tg_chat_ids: list[int] = Field(alias="tgChatIds")


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exception_name: Optional[str] = Field(None, alias="exceptionName")
    exception_message: Optional[str] = Field(None, alias="exceptionMessage")
    stacktrace: Optional[list[str]] = None


class User(BaseModel):
    chat_id: int
    tracked_links: list[Link] = Field(default_factory=list)
