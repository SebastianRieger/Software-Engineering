from repositories.weather import WeatherRepository
from core.config import settings


class WeatherService:
    def __init__(self, repository: WeatherRepository | None = None):
        self.repository = repository or WeatherRepository()

    async def get_current_weather(
        self,
        lat: float = settings.DEFAULT_LAT,
        lon: float = settings.DEFAULT_LON,
    ):
        return await self.repository.get_current_weather(lat=lat, lon=lon)

    async def get_forecast(
        self,
        days: int = 5,
        lat: float = settings.DEFAULT_LAT,
        lon: float = settings.DEFAULT_LON,
    ):
        return await self.repository.get_forecast(lat=lat, lon=lon, days=days)
