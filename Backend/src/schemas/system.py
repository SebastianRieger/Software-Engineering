from pydantic import BaseModel


class SystemStatusResponse(BaseModel):
    status: str
    version: str
    database_path: str
    config_entries: int
    weather_cache_entries: int
