from .file import router as file_router
from .image_processing import router as image_processing_router
from .preset import router as preset_router
from .process import router as process_router

__all__ = ["file_router", "image_processing_router", "preset_router", "process_router"]