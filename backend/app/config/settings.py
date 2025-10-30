from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "nimrag-backend"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    openweather_api_key: str | None = None
    database_url: str = "sqlite+aiosqlite:///./data.db"

    class Config:
        env_file = ".env"


settings = Settings()
