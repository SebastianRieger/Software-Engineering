from fastapi import APIRouter, Depends, HTTPException, Query

from core.config import settings
from schemas.gestures import (
    GestureFrameResponse,
    GestureStartRequest,
    GestureStatusResponse,
    GestureVideoProcessingResponse,
)
from services.gestures import GestureService, GestureServiceError, gesture_service


router = APIRouter()


async def get_gesture_service() -> GestureService:
    return gesture_service


@router.get("/status", response_model=GestureStatusResponse)
async def get_status(
    service: GestureService = Depends(get_gesture_service),
):
    return service.get_status()


@router.post("/start", response_model=GestureStatusResponse)
async def start_gesture_detection(
    payload: GestureStartRequest,
    service: GestureService = Depends(get_gesture_service),
):
    try:
        return service.start(camera_index=payload.camera_index)
    except GestureServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/stop", response_model=GestureStatusResponse)
async def stop_gesture_detection(
    service: GestureService = Depends(get_gesture_service),
):
    return service.stop()


@router.get("/frame", response_model=GestureFrameResponse)
async def get_preview_frame(
    service: GestureService = Depends(get_gesture_service),
):
    image = service.get_frame()
    if image is None:
        raise HTTPException(status_code=404, detail="Kein Vorschaubild verfuegbar.")
    return {"image": image}


@router.post("/dev/process-video", response_model=GestureVideoProcessingResponse)
async def process_video(
    video_path: str = Query(..., min_length=1),
    service: GestureService = Depends(get_gesture_service),
):
    if not settings.GESTURES_DEV_ENDPOINT_ENABLED:
        raise HTTPException(status_code=404, detail="Endpoint ist deaktiviert.")

    try:
        return service.process_video(video_path=video_path)
    except GestureServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
