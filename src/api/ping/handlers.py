from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/ping", response_model=None)
async def ping_handler(
    _: Request,
) -> dict[str, str]:
    return {"pong": "ok"}
