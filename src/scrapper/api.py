from typing import TYPE_CHECKING

from fastapi import APIRouter, Header, HTTPException, Request

from src.scrapper.models import (
    AddLinkRequest,
    ApiErrorResponse,
    LinkResponse,
    ListLinksResponse,
    RemoveLinkRequest,
)

if TYPE_CHECKING:
    from src.scrapper.storage import ScrapperStorage

router = APIRouter()


@router.post(
    "/tg-chat/{id}",
    responses={
        200: {"description": "Чат зарегистрирован"},
        400: {"model": ApiErrorResponse},
    },
)
async def register_chat(id: int, request: Request) -> dict[str, str]:
    try:
        storage: ScrapperStorage = request.app.state.storage
        storage.add_chat(id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                description="Ошибка при регистрации чата",
                code="CHAT_REGISTRATION_ERROR",
                exceptionName=e.__class__.__name__,
                exceptionMessage=str(e),
            ).model_dump(),
        )


@router.delete(
    "/tg-chat/{id}",
    responses={
        200: {"description": "Чат успешно удалён"},
        400: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
    },
)
async def remove_chat(id: int, request: Request) -> dict[str, str]:
    try:
        storage: ScrapperStorage = request.app.state.storage
        if storage.remove_chat(id):
            return {"status": "ok"}
        raise HTTPException(
            status_code=404,
            detail=ApiErrorResponse(  # type: ignore[call-arg]
                description="Чат не найден",
                code="CHAT_NOT_FOUND",
            ).model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                description="Ошибка при удалении чата",
                code="CHAT_REMOVAL_ERROR",
                exceptionName=e.__class__.__name__,
                exceptionMessage=str(e),
            ).model_dump(),
        )


@router.get(
    "/links",
    response_model=ListLinksResponse,
    responses={
        200: {"model": ListLinksResponse},
        400: {"model": ApiErrorResponse},
    },
)
async def get_links(
    request: Request,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
) -> ListLinksResponse:
    try:
        storage: ScrapperStorage = request.app.state.storage
        links = storage.get_links(tg_chat_id)
        return ListLinksResponse(links=links, size=len(links))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                description="Ошибка при получении списка ссылок",
                code="LINKS_FETCH_ERROR",
                exceptionName=e.__class__.__name__,
                exceptionMessage=str(e),
            ).model_dump(),
        )


@router.post(
    "/links",
    response_model=LinkResponse,
    responses={
        200: {"model": LinkResponse},
        400: {"model": ApiErrorResponse},
    },
)
async def add_link(
    request: Request,
    link_request: AddLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
) -> LinkResponse:
    try:
        storage: ScrapperStorage = request.app.state.storage
        link = storage.add_link(
            tg_chat_id,
            link_request.link,
            link_request.tags,
            link_request.filters,
        )
        if link:
            return link
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(  # type: ignore[call-arg]
                description="Ссылка уже отслеживается",
                code="LINK_ALREADY_EXISTS",
            ).model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                description="Ошибка при добавлении ссылки",
                code="LINK_ADDITION_ERROR",
                exceptionName=e.__class__.__name__,
                exceptionMessage=str(e),
            ).model_dump(),
        )


@router.delete(
    "/links",
    response_model=LinkResponse,
    responses={
        200: {"model": LinkResponse},
        400: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
    },
)
async def remove_link(
    request: Request,
    link_request: RemoveLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
) -> LinkResponse:
    try:
        storage: ScrapperStorage = request.app.state.storage
        link = storage.remove_link(tg_chat_id, link_request.link)
        if link:
            return link
        raise HTTPException(
            status_code=404,
            detail=ApiErrorResponse(  # type: ignore[call-arg]
                description="Ссылка не найдена",
                code="LINK_NOT_FOUND",
            ).model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(  # type: ignore[call-arg]
                description="Ошибка при удалении ссылки",
                code="LINK_REMOVAL_ERROR",
                exceptionName=e.__class__.__name__,
                exceptionMessage=str(e),
            ).model_dump(),
        )
