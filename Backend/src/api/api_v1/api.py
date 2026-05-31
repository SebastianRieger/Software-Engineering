from fastapi import APIRouter

from ..device_endpoints import musical_audio_router, voice_router
from ..system_endpoints import calibration_router, config_router, gesture_router
from .endpoints import calendar, led, market, news, nina, smart_home, system, weather


api_router = APIRouter()

api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(nina.router, prefix="/nina", tags=["nina"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(
    calibration_router, prefix="/calibration", tags=["calibration"]
)
api_router.include_router(gesture_router, prefix="/gestures", tags=["gestures"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(led.router, prefix="/led", tags=["led"])
api_router.include_router(smart_home.router, prefix="/smart-home", tags=["smart-home"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(voice_router, prefix="/voice", tags=["voice"])
api_router.include_router(
    musical_audio_router, prefix="/musical-audio", tags=["musical-audio"]
)
