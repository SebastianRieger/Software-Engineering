from fastapi import APIRouter

from core.config import settings
from repositories.config import ConfigRepository
from repositories.weather import WeatherRepository
from schemas.system import SystemStatusResponse


router = APIRouter()


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    config_repository = ConfigRepository()
    weather_repository = WeatherRepository()
    return {
        "status": "running",
        "version": settings.VERSION,
        "database_path": str(settings.sqlite_path),
        "config_entries": config_repository.count_entries(),
        "weather_cache_entries": weather_repository.count_cache_entries(),
    }
