from fastapi import APIRouter, Depends, HTTPException, Query

from core.config import settings
from repositories.weather import WeatherRepositoryError
from schemas.weather import WeatherCurrentResponse, WeatherForecastResponse
from services.weather import WeatherService


router = APIRouter()


async def get_weather_service() -> WeatherService:
    return WeatherService()


@router.get("/", response_model=WeatherCurrentResponse)
@router.get("/current", response_model=WeatherCurrentResponse)
async def get_current_weather(
    lat: float = Query(default=settings.DEFAULT_LAT),
    lon: float = Query(default=settings.DEFAULT_LON),
    weather_service: WeatherService = Depends(get_weather_service),
):
    try:
        return await weather_service.get_current_weather(lat=lat, lon=lon)
    except WeatherRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    days: int = Query(default=5, ge=1, le=7),
    lat: float = Query(default=settings.DEFAULT_LAT),
    lon: float = Query(default=settings.DEFAULT_LON),
    weather_service: WeatherService = Depends(get_weather_service),
):
    try:
        return await weather_service.get_forecast(days=days, lat=lat, lon=lon)
    except WeatherRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
