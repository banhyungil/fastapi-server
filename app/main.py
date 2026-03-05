from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from app.api.router import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging

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
