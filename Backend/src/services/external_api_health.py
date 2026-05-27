from datetime import datetime, timezone
from time import perf_counter
from typing import Awaitable, Callable

from repositories.app_config import AppConfigRepository
from schemas.system import ExternalApiHealthProvider, ExternalApiHealthResponse
from services.news import NewsService
from services.weather import WeatherService


class ExternalApiHealthService:
    def __init__(
        self,
        weather_service: WeatherService | None = None,
        news_service: NewsService | None = None,
        app_config_repository: AppConfigRepository | None = None,
    ) -> None:
        self.weather_service = weather_service or WeatherService()
        self.news_service = news_service or NewsService()
        self.app_config_repository = app_config_repository or AppConfigRepository()

    async def check_all(self) -> ExternalApiHealthResponse:
        checked_at = datetime.now(timezone.utc)
        config = self.app_config_repository.get_app_config()

        providers = [
            await self._check_provider(
                provider="open-meteo-weather",
                checked_at=checked_at,
                operation=lambda: self.weather_service.get_current_weather(
                    lat=config.system.latitude,
                    lon=config.system.longitude,
                ),
            ),
            await self._check_provider(
                provider="tagesschau-news",
                checked_at=checked_at,
                operation=lambda: self.news_service.get_news(
                    ressort=config.widgets.news.ressort,
                    regions=config.widgets.news.regions,
                ),
            ),
        ]

        return ExternalApiHealthResponse(checked_at=checked_at, providers=providers)

    async def _check_provider(
        self,
        provider: str,
        checked_at: datetime,
        operation: Callable[[], Awaitable[object]],
    ) -> ExternalApiHealthProvider:
        started_at = perf_counter()
        try:
            await operation()
            status = "ok"
            error = None
        except Exception as exc:  # pylint: disable=broad-exception-caught
            status = "down"
            error = str(exc)

        return ExternalApiHealthProvider(
            provider=provider,
            status=status,
            checked_at=checked_at,
            response_time_ms=round((perf_counter() - started_at) * 1000, 2),
            error=error,
        )
