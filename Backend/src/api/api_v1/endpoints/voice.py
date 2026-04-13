from fastapi import APIRouter, Depends, HTTPException

from schemas.voice import VoiceStartRequest, VoiceStatusResponse
from services.voice import VoiceService, VoiceServiceError, voice_service


router = APIRouter()


async def get_voice_service() -> VoiceService:
    return voice_service


@router.get("/status", response_model=VoiceStatusResponse)
async def get_voice_status(service: VoiceService = Depends(get_voice_service)):
    return service.get_status()


@router.post("/start", response_model=VoiceStatusResponse)
async def start_voice(payload: VoiceStartRequest, service: VoiceService = Depends(get_voice_service)):
    try:
        return service.start(device_index=payload.device_index)
    except VoiceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/stop", response_model=VoiceStatusResponse)
async def stop_voice(service: VoiceService = Depends(get_voice_service)):
    return service.stop()