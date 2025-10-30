from fastapi import APIRouter

router = APIRouter()

# include sub-routers
from . import weather as weather_module  # noqa: F401
from . import system as system_module  # noqa: F401
from . import led as led_module  # noqa: F401

router.include_router(weather_module.router, prefix="", tags=["weather"])
router.include_router(system_module.router, prefix="", tags=["system"])
router.include_router(led_module.router, prefix="", tags=["led"])
