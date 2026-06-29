from fastapi import APIRouter, Depends, HTTPException

from repositories.app_config import AppConfigRepository, AppConfigRepositoryError
from repositories.meme import MemeRepositoryError
from schemas.meme import MemeBatchResponse
from services.meme import MemeService

router = APIRouter()


async def get_meme_service() -> MemeService:
    return MemeService()


async def get_meme_app_config_repository() -> AppConfigRepository:
    return AppConfigRepository()


@router.get("", response_model=MemeBatchResponse)
@router.get("/", response_model=MemeBatchResponse, include_in_schema=False)
async def get_meme(
    meme_service: MemeService = Depends(get_meme_service),
    config_repository: AppConfigRepository = Depends(get_meme_app_config_repository),
):
    try:
        config = config_repository.get_app_config().widgets.meme
    except AppConfigRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    try:
        return await meme_service.get_memes(
            subreddit=config.subreddit,
            sfw_only=config.sfw_only,
        )
    except MemeRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
