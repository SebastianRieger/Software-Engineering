from fastapi import APIRouter, Depends, Query

from repositories.config import ConfigRepository
from schemas.configuration import LayoutConfig, LayoutConfigEnvelope


router = APIRouter()


async def get_config_repository() -> ConfigRepository:
    return ConfigRepository()


@router.get("/layout", response_model=LayoutConfigEnvelope)
async def get_layout(
    profile: str = Query(default="default"),
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_layout(profile=profile)
    return LayoutConfigEnvelope(profile=profile, config=config)


@router.put("/layout", response_model=LayoutConfigEnvelope)
async def save_layout(
    layout: LayoutConfig,
    profile: str = Query(default="default"),
    repository: ConfigRepository = Depends(get_config_repository),
):
    saved_config = repository.save_layout(layout=layout, profile=profile)
    return LayoutConfigEnvelope(profile=profile, config=saved_config)
