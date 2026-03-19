from fastapi import APIRouter

from app.api.endpoints import (
    custom_filters_router, files_router, filters_router,
    presets_router, processes_router,
)

api_router = APIRouter()
api_router.include_router(custom_filters_router)
api_router.include_router(files_router)
api_router.include_router(filters_router)
api_router.include_router(presets_router)
api_router.include_router(processes_router)
