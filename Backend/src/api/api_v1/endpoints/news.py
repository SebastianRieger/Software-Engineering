from fastapi import APIRouter, Depends, HTTPException, Query

from repositories.app_config import AppConfigRepository, AppConfigRepositoryError
from repositories.news import NewsRepositoryError
from schemas.configuration import NewsRessort
from schemas.news import NewsResponse
from services.news import NewsService

router = APIRouter()


async def get_news_service() -> NewsService:
    return NewsService()


async def get_news_app_config_repository() -> AppConfigRepository:
    return AppConfigRepository()


def _parse_regions(value: str | None) -> list[int] | None:
    if value is None or value.strip() == "":
        return None

    try:
        return [int(region.strip()) for region in value.split(",") if region.strip()]
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="regions must be a comma-separated list of integer region IDs.",
        ) from exc


@router.get("", response_model=NewsResponse)
@router.get("/", response_model=NewsResponse, include_in_schema=False)
async def get_news(
    ressort: NewsRessort | None = Query(default=None),
    regions: str | None = Query(default=None),
    news_service: NewsService = Depends(get_news_service),
    config_repository: AppConfigRepository = Depends(get_news_app_config_repository),
):
    try:
        config = config_repository.get_app_config().widgets.news
    except AppConfigRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    resolved_ressort = ressort if ressort is not None else config.ressort
    resolved_regions = _parse_regions(regions)
    if resolved_regions is None:
        resolved_regions = config.regions

    try:
        return await news_service.get_news(
            ressort=resolved_ressort,
            regions=resolved_regions,
        )
    except NewsRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
