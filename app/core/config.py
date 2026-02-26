from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FastAPI Server"
    env: str = "local"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "postgresql://postgres:test1!@localhost:5434/postgres"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
