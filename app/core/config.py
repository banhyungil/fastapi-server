import os
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV = os.getenv("ENV", "local")  # 환경변수 ENV로 파일 결정


class Settings(BaseSettings):
    app_name: str = "FastAPI Server"
    env: str = "local"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "postgresql://postgres:test1!@localhost:5434/postgres"
    log_level: str = 'DEBUG'

    model_config = SettingsConfigDict(
        env_file=f".env{ENV}",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
