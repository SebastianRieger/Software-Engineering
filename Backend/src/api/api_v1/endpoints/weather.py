from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from services.weather import WeatherService

router = APIRouter()

class WeatherData(BaseModel):
    temperature: float
    humidity: float
    condition: str
    wind_speed: float
    timestamp: datetime

class WeatherForecast(BaseModel):
    date: datetime
    min_temp: float
    max_temp: float
    condition: str

@router.get("/current", response_model=WeatherData)
async def get_current_weather():
    """Get current weather data"""
    try:
        weather_service = WeatherService()
        return await weather_service.get_current_weather()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast", response_model=List[WeatherForecast])
async def get_weather_forecast(days: Optional[int] = 5):
    """Get weather forecast for the next X days"""
    try:
        weather_service = WeatherService()
        return await weather_service.get_forecast(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))