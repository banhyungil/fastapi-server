from fastapi import APIRouter

from app.api.endpoints import image_processing_router

api_router = APIRouter()
api_router.include_router(image_processing_router)
