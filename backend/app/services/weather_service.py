import asyncio
from typing import Dict


class WeatherService:
    """Simple weather service stub. Replace with real OpenWeatherMap integration."""

    async def fetch_weather(self, location: str) -> Dict:
        await asyncio.sleep(0.01)
        return {
            "location": location,
            "timestamp": "2025-10-28T12:00:00Z",
            "temperature_c": 18.5,
            "humidity": 56,
            "wind_speed": 3.2,
            "condition": "Partly Cloudy",
        }


weather_service = WeatherService()
