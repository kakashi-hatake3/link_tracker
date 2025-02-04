from fastapi import APIRouter

from . import ping

__all__ = ("router",)

router = APIRouter()
router.include_router(ping.router, tags=["ping"])
