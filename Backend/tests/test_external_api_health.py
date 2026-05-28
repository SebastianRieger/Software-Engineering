from datetime import datetime, timezone

import pytest

from api.system_endpoints import get_external_api_health_service
from main import app
from schemas.configuration import AppConfig
from schemas.system import ExternalApiHealthProvider, ExternalApiHealthResponse
from services.external_api_health import ExternalApiHealthService


class MockAppConfigRepository:
    def get_app_config(self):
        return AppConfig(
            system={
                "location_name": "Stuttgart",
                "latitude": 48.7758,
                "longitude": 9.1829,
                "units": "metric",
                "theme": "dark",
                "weather_refresh_seconds": 900,
            },
            widgets={"news": {"ressort": "inland", "regions": [1]}},
        )


class MockWeatherService:
    async def get_current_weather(self, lat=None, lon=None, city=None):
        return {"temperature": 20.0, "lat": lat, "lon": lon, "city": city}


class FailingNewsService:
    async def get_news(self, ressort=None, regions=None):
        raise RuntimeError("news provider unavailable")


@pytest.mark.asyncio
async def test_external_api_health_reports_partial_failures():
    service = ExternalApiHealthService(
        weather_service=MockWeatherService(),
        news_service=FailingNewsService(),
        app_config_repository=MockAppConfigRepository(),
    )

    result = await service.check_all()

    statuses = {provider.provider: provider.status for provider in result.providers}
    assert statuses["open-meteo-weather"] == "ok"
    assert statuses["tagesschau-news"] == "down"
    assert result.providers[1].error == "news provider unavailable"


@pytest.mark.asyncio
async def test_external_api_health_endpoint(client):
    checked_at = datetime.now(timezone.utc)

    class MockHealthService:
        async def check_all(self):
            return ExternalApiHealthResponse(
                checked_at=checked_at,
                providers=[
                    ExternalApiHealthProvider(
                        provider="tagesschau-news",
                        status="down",
                        checked_at=checked_at,
                        response_time_ms=1.2,
                        error="timeout",
                    )
                ],
            )

    async def _override_health_service():
        return MockHealthService()

    app.dependency_overrides[get_external_api_health_service] = _override_health_service
    try:
        response = await client.get("/api/v1/system/external-apis/health")
    finally:
        app.dependency_overrides.pop(get_external_api_health_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["providers"][0]["provider"] == "tagesschau-news"
    assert data["providers"][0]["status"] == "down"
