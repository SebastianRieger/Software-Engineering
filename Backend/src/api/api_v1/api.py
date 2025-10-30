from fastapi import APIRouter

from .endpoints import weather, calendar, led, smart_home, system

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(led.router, prefix="/led", tags=["led"])
api_router.include_router(smart_home.router, prefix="/smart-home", tags=["smart-home"])
api_router.include_router(system.router, prefix="/system", tags=["system"])