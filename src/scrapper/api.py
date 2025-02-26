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


def raise_http_exception(description: str, code: str, status_code: int) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=ApiErrorResponse(  # type: ignore[call-arg]
            description=description,
            code=code,
        ).model_dump(),
    )


@router.post(
    "/tg-chat/{chat_id}",
    responses={
        200: {"description": "Чат зарегистрирован"},
        400: {"model": ApiErrorResponse},
    },
)
async def register_chat(chat_id: int, request: Request) -> dict[str, str]:
    try:
        storage: ScrapperStorage = request.app.state.storage
        storage.add_chat(chat_id)
        if storage.get_chat(chat_id):
            return {"status": "ok"}
        else:
            return {"status": "error"}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                description="Ошибка при регистрации чата",
                code="CHAT_REGISTRATION_ERROR",
                exceptionName=e.__class__.__name__,
                exceptionMessage=str(e),
            ).model_dump(),
        ) from e


@router.delete(
    "/tg-chat/{chat_id}",
    responses={
        200: {"description": "Чат успешно удалён"},
        400: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
    },
)
async def remove_chat(chat_id: int, request: Request) -> dict[str, str] | None:
    try:
        storage: ScrapperStorage = request.app.state.storage
        if storage.remove_chat(chat_id):
            return {"status": "ok"}
        raise_http_exception("Чат не найден", "CHAT_NOT_FOUND", 404)
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
        ) from e
    else:
        return None


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
        ) from e


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
) -> LinkResponse | None:
    try:
        storage: ScrapperStorage = request.app.state.storage

        def add_link_to_storage() -> LinkResponse | None:
            link = storage.add_link(
                tg_chat_id,
                link_request.link,
                link_request.tags,
                link_request.filters,
            )
            if not link:
                raise_http_exception("Ссылка уже отслеживается", "LINK_ALREADY_EXISTS", 400)
            return link

        return add_link_to_storage()
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
        ) from e


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
) -> LinkResponse | None:
    try:
        storage: ScrapperStorage = request.app.state.storage

        def remove_link_from_storage() -> LinkResponse | None:
            link = storage.remove_link(tg_chat_id, link_request.link)
            if not link:
                raise_http_exception("Ссылка не найдена", "LINK_NOT_FOUND", 404)
            return link

        return remove_link_from_storage()
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
        ) from e
