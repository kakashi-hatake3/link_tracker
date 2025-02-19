from fastapi import APIRouter
from src.api.updates import router as updates_router

__all__ = ("router",)

router = APIRouter()
router.include_router(updates_router)
