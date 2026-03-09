import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.services.image_processing_service import PARAM_MODELS, cleanup_cache

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup
    cleanup_cache()
    logger.info("cache cleanup completed on startup")

    async def _periodic_cleanup() -> None:
        while True:
            await asyncio.sleep(5 * 60)
            cleanup_cache()

    task = asyncio.create_task(_periodic_cleanup())
    yield
    # shutdown
    task.cancel()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    # 기본 헤더 외에 추가할 헤더 명시
    expose_headers=["X-Process-Time-Ms"],
)

register_exception_handlers(app)



@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running"}


app.include_router(api_router, prefix=settings.api_prefix)

# StaticFiles는 독립 ASGI 앱이라 CORSMiddleware를 타지 않으므로
# sub-application이 아닌 APIRouter로 정적파일을 서빙하거나,
# mount 전에 별도 CORS 래퍼를 적용한다.
_uploads_app = CORSMiddleware(
    StaticFiles(directory="uploads"),
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", _uploads_app, name="uploads")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    # 필터 파라미터 모델을 components/schemas에 등록 (동일 모델 중복 제거)
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    seen: set[type] = set()
    for model_cls in PARAM_MODELS.values():
        if model_cls in seen:
            continue
        seen.add(model_cls)
        schemas[model_cls.__name__] = model_cls.model_json_schema(by_alias=True)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
