from fastapi import APIRouter
from app.schemas.weather import WeatherResponse

router = APIRouter()


@router.get("/weather", response_model=WeatherResponse)
async def get_weather():
    """Return a mocked weather response (replace with real service)."""
    return {
        "location": "Berlin",
        "timestamp": "2025-10-28T12:00:00Z",
        "temperature_c": 18.5,
        "humidity": 56,
        "wind_speed": 3.2,
        "condition": "Partly Cloudy",
    }
