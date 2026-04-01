from .custom_filters import router as custom_filters_router
from .files import router as files_router
from .files_local import router as files_local_router
from .filters import router as filters_router
from .presets import router as presets_router
from .processes import router as processes_router

__all__ = [
    "custom_filters_router",
    "files_router",
    "files_local_router",
    "filters_router",
    "presets_router",
    "processes_router",
]