from fastapi import APIRouter, Depends, HTTPException, Query

from repositories.weather import WeatherRepositoryError
from schemas.weather import (
    WeatherCurrentResponse,
    WeatherForecastResponse,
    WeatherGeocodingResponse,
)
from services.weather import WeatherService

weather_router = APIRouter()
calendar_router = APIRouter()
smart_home_router = APIRouter()


async def get_weather_service() -> WeatherService:
    return WeatherService()


@weather_router.get("/geocode", response_model=WeatherGeocodingResponse)
async def geocode_city(
    city: str = Query(..., min_length=2),
    weather_service: WeatherService = Depends(get_weather_service),
):
    try:
        return await weather_service.geocode_city(city=city)
    except WeatherRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@weather_router.get("/", response_model=WeatherCurrentResponse)
@weather_router.get("/current", response_model=WeatherCurrentResponse)
async def get_current_weather(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    city: str | None = Query(default=None, min_length=2),
    weather_service: WeatherService = Depends(get_weather_service),
):
    try:
        return await weather_service.get_current_weather(lat=lat, lon=lon, city=city)
    except WeatherRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@weather_router.get("/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    days: int = Query(default=5, ge=1, le=7),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    city: str | None = Query(default=None, min_length=2),
    weather_service: WeatherService = Depends(get_weather_service),
):
    try:
        return await weather_service.get_forecast(
            days=days, lat=lat, lon=lon, city=city
        )
    except WeatherRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@calendar_router.get("/")
async def get_calendar_events():
    return {"message": "Calendar functionality coming soon"}


@smart_home_router.get("/devices")
async def get_devices():
    return {"message": "Smart home functionality coming soon"}
