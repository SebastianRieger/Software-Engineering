from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SystemStatusResponse(BaseModel):
    status: str
    version: str
    database_path: str
    config_entries: int
    weather_cache_entries: int


class ExternalApiHealthProvider(BaseModel):
    provider: str
    status: Literal["ok", "down"]
    checked_at: datetime
    response_time_ms: float
    error: str | None = None


class ExternalApiHealthResponse(BaseModel):
    checked_at: datetime
    providers: list[ExternalApiHealthProvider]
