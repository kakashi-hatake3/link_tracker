from fastapi import APIRouter, HTTPException, Request

from src.models import ApiErrorResponse, LinkUpdate

router = APIRouter()


@router.post(
    "/updates",
    responses={
        200: {"description": "Обновление обработано"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
    },
)
async def process_update(update: LinkUpdate, request: Request) -> dict[str, str]:
    try:
        app = request.app
        for chat_id in update.tg_chat_ids:
            user = app.storage.get_user(chat_id)
            if user:
                message = f"Обновление для ссылки {update.url}"
                if update.description:
                    message += f"\nОписание: {update.description}"
                await app.tg_client.send_message(chat_id, message)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ApiErrorResponse(
                description="Ошибка при обработке обновления",
                code="UPDATE_PROCESSING_ERROR",
                exceptionName=e.__class__.__name__,
                exceptionMessage=str(e),
            ).model_dump(),
        )
