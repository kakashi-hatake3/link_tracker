from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exception_name: Optional[str] = Field(None, alias="exceptionName")
    exception_message: Optional[str] = Field(None, alias="exceptionMessage")
    stacktrace: Optional[List[str]] = None

class LinkResponse(BaseModel):
    id: int
    url: HttpUrl
    tags: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)

class AddLinkRequest(BaseModel):
    link: HttpUrl
    tags: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)

class RemoveLinkRequest(BaseModel):
    link: HttpUrl

class ListLinksResponse(BaseModel):
    links: List[LinkResponse]
    size: int

class ChatInfo(BaseModel):
    chat_id: int
    links: List[LinkResponse] = Field(default_factory=list) 