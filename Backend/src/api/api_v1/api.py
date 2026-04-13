from fastapi import APIRouter

from .endpoints import calendar, configuration, gestures, led, smart_home, system, voice, weather

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(configuration.router, prefix="/config", tags=["config"])
api_router.include_router(gestures.router, prefix="/gestures", tags=["gestures"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(led.router, prefix="/led", tags=["led"])
api_router.include_router(smart_home.router, prefix="/smart-home", tags=["smart-home"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
