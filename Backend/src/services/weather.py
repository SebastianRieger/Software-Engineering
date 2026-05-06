from repositories.weather import WeatherRepository


class WeatherService:
    def __init__(self, repository: WeatherRepository | None = None):
        self.repository = repository or WeatherRepository()

    async def get_current_weather(
        self,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ):
        return await self.repository.get_current_weather(lat=lat, lon=lon, city=city)

    async def get_forecast(
        self,
        days: int = 5,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ):
        return await self.repository.get_forecast(lat=lat, lon=lon, days=days, city=city)

    async def geocode_city(self, city: str):
        return await self.repository.geocode_city(city=city)
