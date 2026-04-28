from fastapi import APIRouter

from .data_endpoints import calendar_router, smart_home_router, weather_router
from .device_endpoints import led_router, voice_router
from .system_endpoints import calibration_router, config_router, gesture_router, system_router


api_router = APIRouter()

api_router.include_router(weather_router, prefix="/weather", tags=["weather"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(calibration_router, prefix="/calibration", tags=["calibration"])
api_router.include_router(gesture_router, prefix="/gestures", tags=["gestures"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["calendar"])
api_router.include_router(led_router, prefix="/led", tags=["led"])
api_router.include_router(smart_home_router, prefix="/smart-home", tags=["smart-home"])
api_router.include_router(system_router, prefix="/system", tags=["system"])
api_router.include_router(voice_router, prefix="/voice", tags=["voice"])
