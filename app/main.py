from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles


from app.api.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.services.image_processing_service import PARAM_MODELS

setup_logging()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
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

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


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
