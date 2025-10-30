import aiohttp
from datetime import datetime
from core.config import settings

class WeatherService:
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    async def get_current_weather(self):
        """Fetch current weather data from OpenWeatherMap API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/weather",
                params={
                    "appid": self.api_key,
                    "units": "metric",
                    # Default coordinates can be configured
                    "lat": "48.7758",  # Default to some location
                    "lon": "9.1829"
                }
            ) as response:
                data = await response.json()
                
                return {
                    "temperature": data["main"]["temp"],
                    "humidity": data["main"]["humidity"],
                    "condition": data["weather"][0]["main"],
                    "wind_speed": data["wind"]["speed"],
                    "timestamp": datetime.utcfromtimestamp(data["dt"])
                }
                
    async def get_forecast(self, days: int = 5):
        """Fetch weather forecast from OpenWeatherMap API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/forecast",
                params={
                    "appid": self.api_key,
                    "units": "metric",
                    "lat": "48.7758",
                    "lon": "9.1829"
                }
            ) as response:
                data = await response.json()
                
                # Process and aggregate forecast data by day
                daily_forecasts = []
                # Implementation details here
                
                return daily_forecasts[:days]