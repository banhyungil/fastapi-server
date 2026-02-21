from fastapi import APIRouter

from app.api.endpoints.health import router as health_router
from app.api.endpoints.image_processing import router as image_processing_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(image_processing_router)
