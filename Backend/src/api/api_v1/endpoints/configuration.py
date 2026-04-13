from fastapi import APIRouter, Depends, Query

from repositories.config import ConfigRepository
from schemas.configuration import (
    LayoutConfig,
    LayoutConfigEnvelope,
    SystemConfig,
    SystemConfigEnvelope,
)
from schemas.gestures import GestureConfig, GestureConfigEnvelope
from services.gestures import gesture_service


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


@router.get("/system", response_model=SystemConfigEnvelope)
async def get_system_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_system_config()
    return SystemConfigEnvelope(config=config)


@router.put("/system", response_model=SystemConfigEnvelope)
async def save_system_config(
    config: SystemConfig,
    repository: ConfigRepository = Depends(get_config_repository),
):
    saved_config = repository.save_system_config(config=config)
    return SystemConfigEnvelope(config=saved_config)


@router.get("/gestures", response_model=GestureConfigEnvelope)
async def get_gesture_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_gesture_config()
    return GestureConfigEnvelope(config=config)


@router.put("/gestures", response_model=GestureConfigEnvelope)
async def save_gesture_config(
    config: GestureConfig,
    repository: ConfigRepository = Depends(get_config_repository),
):
    saved_config = repository.save_gesture_config(config=config)
    gesture_service.reload_config()
    return GestureConfigEnvelope(config=saved_config)
