import pytest

from api.api_v1.endpoints.news import (
    get_news_app_config_repository,
    get_news_service,
)
from main import app
from repositories.news import NewsRepositoryError
from schemas.configuration import AppConfig


class MockNewsService:
    def __init__(self):
        self.calls = []
        self.error: NewsRepositoryError | None = None

    async def get_news(self, ressort=None, regions=None):
        self.calls.append({"ressort": ressort, "regions": regions})
        if self.error is not None:
            raise self.error
        return {
            "news": [
                {
                    "sophoraId": "news-1",
                    "title": "Testmeldung",
                    "topline": "Topline",
                    "firstSentence": "Ein kurzer Teaser.",
                    "date": "2026-05-27T10:00:00+02:00",
                    "shareURL": "https://www.tagesschau.de/",
                    "detailsweb": "https://www.tagesschau.de/",
                    "ressort": ressort,
                    "breakingNews": False,
                }
            ],
            "source": "live",
        }


class MockAppConfigRepository:
    def __init__(self, config: AppConfig):
        self.config = config

    def get_app_config(self):
        return self.config


@pytest.fixture
def mock_news_dependencies():
    service = MockNewsService()
    config_repository = MockAppConfigRepository(
        AppConfig(
            widgets={
                "news": {
                    "ressort": "wissen",
                    "regions": [4, 5],
                    "refresh_seconds": 1800,
                }
            }
        )
    )

    async def _override_news_service():
        return service

    async def _override_app_config_repository():
        return config_repository

    app.dependency_overrides[get_news_service] = _override_news_service
    app.dependency_overrides[get_news_app_config_repository] = (
        _override_app_config_repository
    )
    yield service
    app.dependency_overrides.pop(get_news_service, None)
    app.dependency_overrides.pop(get_news_app_config_repository, None)


@pytest.mark.asyncio
async def test_get_news_uses_config_defaults(client, mock_news_dependencies):
    response = await client.get("/api/v1/news")

    assert response.status_code == 200
    assert response.json()["news"][0]["title"] == "Testmeldung"
    assert mock_news_dependencies.calls == [
        {"ressort": "wissen", "regions": [4, 5]}
    ]


@pytest.mark.asyncio
async def test_get_news_allows_query_overrides(client, mock_news_dependencies):
    response = await client.get("/api/v1/news?ressort=sport&regions=1,2")

    assert response.status_code == 200
    assert mock_news_dependencies.calls == [{"ressort": "sport", "regions": [1, 2]}]


@pytest.mark.asyncio
async def test_get_news_returns_provider_error(client, mock_news_dependencies):
    mock_news_dependencies.error = NewsRepositoryError(
        "Tagesschau API is not reachable.", status_code=502
    )

    response = await client.get("/api/v1/news")

    assert response.status_code == 502
    assert response.json()["detail"] == "Tagesschau API is not reachable."