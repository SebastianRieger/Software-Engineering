from fastapi import APIRouter, Depends, HTTPException

from schemas.led import LEDBrightnessRequest, LEDColorRequest, LEDStateResponse
from schemas.voice import VoiceInputDeviceListResponse, VoiceStartRequest, VoiceStatusResponse
from services.led import LEDService, led_service
from services.voice import VoiceService, VoiceServiceError, voice_service


led_router = APIRouter()
voice_router = APIRouter()


async def get_led_service() -> LEDService:
    return led_service


async def get_voice_service() -> VoiceService:
    return voice_service


@led_router.get("/status", response_model=LEDStateResponse)
async def get_led_status(service: LEDService = Depends(get_led_service)):
    return service.get_status()


@led_router.post("/color", response_model=LEDStateResponse)
async def set_led_color(
    payload: LEDColorRequest,
    service: LEDService = Depends(get_led_service),
):
    return service.set_color((payload.red, payload.green, payload.blue))


@led_router.post("/brightness", response_model=LEDStateResponse)
async def set_led_brightness(
    payload: LEDBrightnessRequest,
    service: LEDService = Depends(get_led_service),
):
    return service.set_brightness(payload.brightness)


@voice_router.get("/status", response_model=VoiceStatusResponse)
async def get_voice_status(service: VoiceService = Depends(get_voice_service)):
    return service.get_status()


@voice_router.get("/devices", response_model=VoiceInputDeviceListResponse)
async def get_voice_devices(service: VoiceService = Depends(get_voice_service)):
    return {"devices": service.list_input_devices()}


@voice_router.post("/start", response_model=VoiceStatusResponse)
async def start_voice(
    payload: VoiceStartRequest,
    service: VoiceService = Depends(get_voice_service),
):
    try:
        return service.start(device_index=payload.device_index)
    except VoiceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@voice_router.post("/stop", response_model=VoiceStatusResponse)
async def stop_voice(service: VoiceService = Depends(get_voice_service)):
    return service.stop()