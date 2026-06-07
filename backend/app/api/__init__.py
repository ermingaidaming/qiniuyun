from fastapi import APIRouter

from app.api.cpc import router as cpc_router
from app.api.export import router as export_router
from app.api.har import router as har_router
from app.api.novels import router as novels_router
from app.api.r2 import router as r2_router
from app.api.screenplay import router as screenplay_router

router = APIRouter()
router.include_router(novels_router)
router.include_router(screenplay_router)
router.include_router(export_router)
router.include_router(cpc_router)
router.include_router(r2_router)
router.include_router(har_router)
