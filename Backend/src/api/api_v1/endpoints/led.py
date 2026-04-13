from fastapi import APIRouter, Depends

from schemas.led import LEDBrightnessRequest, LEDColorRequest, LEDStateResponse
from services.led import LEDService, led_service

router = APIRouter()


async def get_led_service() -> LEDService:
    return led_service


@router.get("/status", response_model=LEDStateResponse)
async def get_led_status(service: LEDService = Depends(get_led_service)):
    return service.get_status()


@router.post("/color", response_model=LEDStateResponse)
async def set_led_color(
    payload: LEDColorRequest,
    service: LEDService = Depends(get_led_service),
):
    return service.set_color((payload.red, payload.green, payload.blue))


@router.post("/brightness", response_model=LEDStateResponse)
async def set_led_brightness(
    payload: LEDBrightnessRequest,
    service: LEDService = Depends(get_led_service),
):
    return service.set_brightness(payload.brightness)
