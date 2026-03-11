from fastapi import APIRouter

from app.api.endpoints import custom_filter_router, file_router, image_processing_router, preset_router, process_router

api_router = APIRouter()
api_router.include_router(custom_filter_router)
api_router.include_router(file_router)
api_router.include_router(image_processing_router)
api_router.include_router(preset_router)
api_router.include_router(process_router)
