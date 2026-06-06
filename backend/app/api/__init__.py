from fastapi import APIRouter

from app.api.export import router as export_router
from app.api.novels import router as novels_router
from app.api.screenplay import router as screenplay_router

router = APIRouter()
router.include_router(novels_router)
router.include_router(screenplay_router)
router.include_router(export_router)
