from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exception_name: Optional[str] = Field(None, alias="exceptionName")
    exception_message: Optional[str] = Field(None, alias="exceptionMessage")
    stacktrace: Optional[list[str]] = None


class LinkResponse(BaseModel):
    id: int
    url: HttpUrl
    tags: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)


class AddLinkRequest(BaseModel):
    link: HttpUrl
    tags: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)


class RemoveLinkRequest(BaseModel):
    link: HttpUrl


class ListLinksResponse(BaseModel):
    links: list[LinkResponse]
    size: int


class ChatInfo(BaseModel):
    chat_id: int
    links: list[LinkResponse] = Field(default_factory=list)


class UpdateDetail(BaseModel):
    platform: str
    update_type: str
    title: str
    username: str
    created_at: datetime
    preview: str
