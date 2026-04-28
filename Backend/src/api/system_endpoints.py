from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from core.config import settings
from repositories.config import ConfigRepository
from repositories.weather import WeatherRepository
from schemas.calibration import (
    CalibrationApplyResponse,
    CalibrationDefinitionsResponse,
    CalibrationRollbackResponse,
    CalibrationSessionCreateRequest,
    CalibrationSessionResponse,
)
from schemas.configuration import (
    LayoutConfig,
    LayoutConfigEnvelope,
    SystemConfig,
    SystemConfigEnvelope,
)
from schemas.gestures import (
    GestureCameraListResponse,
    GestureConfig,
    GestureConfigEnvelope,
    GestureFrameResponse,
    GestureStartRequest,
    GestureStatusResponse,
    GestureVideoProcessingResponse,
)
from schemas.interactions import InputActionConfig, InputActionConfigEnvelope
from schemas.system import SystemStatusResponse
from schemas.voice import VoiceConfig, VoiceConfigEnvelope
from services.calibration import CalibrationService, CalibrationServiceError, calibration_service
from services.gestures import GestureService, GestureServiceError, gesture_service
from services.voice import voice_service


config_router = APIRouter()
system_router = APIRouter()
gesture_router = APIRouter()
calibration_router = APIRouter()


async def get_config_repository() -> ConfigRepository:
    return ConfigRepository()


async def get_gesture_service() -> GestureService:
    return gesture_service


async def get_calibration_service() -> CalibrationService:
    return calibration_service


def _select_gesture_camera_index(service: GestureService) -> int:
    for device in service.list_camera_devices():
        if isinstance(device, dict):
            if device.get("available", True):
                return int(device["index"])
            continue

        if getattr(device, "available", True):
            return int(getattr(device, "index"))
    return 0


def _ensure_gesture_runtime_for_calibration(service: GestureService) -> None:
    status = service.get_status()
    if bool(status.get("running")):
        return
    service.start(camera_index=_select_gesture_camera_index(service))


@config_router.get("/layout", response_model=LayoutConfigEnvelope)
async def get_layout(
    profile: str = Query(default="default"),
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_layout(profile=profile)
    return LayoutConfigEnvelope(profile=profile, config=config)


@config_router.put("/layout", response_model=LayoutConfigEnvelope)
async def save_layout(
    layout: LayoutConfig,
    profile: str = Query(default="default"),
    repository: ConfigRepository = Depends(get_config_repository),
):
    saved_config = repository.save_layout(layout=layout, profile=profile)
    return LayoutConfigEnvelope(profile=profile, config=saved_config)


@config_router.get("/system", response_model=SystemConfigEnvelope)
async def get_system_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_system_config()
    return SystemConfigEnvelope(config=config)


@config_router.put("/system", response_model=SystemConfigEnvelope)
async def save_system_config(
    config: SystemConfig,
    repository: ConfigRepository = Depends(get_config_repository),
):
    saved_config = repository.save_system_config(config=config)
    return SystemConfigEnvelope(config=saved_config)


@config_router.get("/gestures", response_model=GestureConfigEnvelope)
async def get_gesture_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_gesture_config()
    return GestureConfigEnvelope(config=config)


@config_router.put("/gestures", response_model=GestureConfigEnvelope)
async def save_gesture_config(
    config: GestureConfig,
    repository: ConfigRepository = Depends(get_config_repository),
    calibration_runtime: CalibrationService = Depends(get_calibration_service),
):
    if calibration_runtime.has_active_session("gesture"):
        raise HTTPException(
            status_code=409,
            detail="Gestenkonfiguration kann waehrend einer aktiven Kalibrierung nicht geaendert werden.",
        )
    saved_config = repository.save_gesture_config(config=config)
    gesture_service.reload_config()
    return GestureConfigEnvelope(config=saved_config)


@config_router.get("/voice", response_model=VoiceConfigEnvelope)
async def get_voice_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_voice_config()
    return VoiceConfigEnvelope(config=config)


@config_router.put("/voice", response_model=VoiceConfigEnvelope)
async def save_voice_config(
    config: VoiceConfig,
    repository: ConfigRepository = Depends(get_config_repository),
):
    saved_config = repository.save_voice_config(config=config)
    voice_service.reload_config()
    return VoiceConfigEnvelope(config=saved_config)


@config_router.get("/gesture-actions", response_model=InputActionConfigEnvelope)
async def get_input_action_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_input_action_config()
    return InputActionConfigEnvelope(config=config)


@config_router.put("/gesture-actions", response_model=InputActionConfigEnvelope)
async def save_input_action_config(
    config: InputActionConfig,
    repository: ConfigRepository = Depends(get_config_repository),
):
    saved_config = repository.save_input_action_config(config=config)
    gesture_service.reload_config()
    return InputActionConfigEnvelope(config=saved_config)


@system_router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    config_repository = ConfigRepository()
    weather_repository = WeatherRepository()
    return {
        "status": "running",
        "version": settings.VERSION,
        "database_path": str(settings.sqlite_path),
        "config_entries": config_repository.count_entries(),
        "weather_cache_entries": weather_repository.count_cache_entries(),
    }


@gesture_router.get("/status", response_model=GestureStatusResponse)
async def get_status(
    service: GestureService = Depends(get_gesture_service),
):
    return service.get_status()


@gesture_router.get("/devices", response_model=GestureCameraListResponse)
async def get_camera_devices(
    service: GestureService = Depends(get_gesture_service),
):
    return {"devices": service.list_camera_devices()}


@gesture_router.post("/start", response_model=GestureStatusResponse)
async def start_gesture_detection(
    payload: GestureStartRequest,
    service: GestureService = Depends(get_gesture_service),
):
    try:
        return service.start(camera_index=payload.camera_index)
    except GestureServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@gesture_router.post("/stop", response_model=GestureStatusResponse)
async def stop_gesture_detection(
    service: GestureService = Depends(get_gesture_service),
):
    return service.stop()


@gesture_router.get("/frame", response_model=GestureFrameResponse)
async def get_preview_frame(
    service: GestureService = Depends(get_gesture_service),
):
    image = service.get_frame()
    if image is None:
        raise HTTPException(status_code=404, detail="Kein Vorschaubild verfuegbar.")
    return {"image": image}


@gesture_router.post("/dev/process-video", response_model=GestureVideoProcessingResponse)
async def process_video(
    video_path: str = Query(..., min_length=1),
    service: GestureService = Depends(get_gesture_service),
):
    if not settings.GESTURES_DEV_ENDPOINT_ENABLED:
        raise HTTPException(status_code=404, detail="Endpoint ist deaktiviert.")

    resolved_path = Path(video_path).expanduser()
    if not resolved_path.is_absolute():
        raise HTTPException(
            status_code=400,
            detail="video_path muss ein absoluter Dateipfad sein.",
        )

    try:
        return service.process_video(video_path=str(resolved_path))
    except GestureServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@calibration_router.get("/definitions", response_model=CalibrationDefinitionsResponse)
async def get_calibration_definitions(
    service: CalibrationService = Depends(get_calibration_service),
):
    return service.get_definitions()


@calibration_router.post("/sessions", response_model=CalibrationSessionResponse)
async def start_calibration_session(
    payload: CalibrationSessionCreateRequest,
    service: CalibrationService = Depends(get_calibration_service),
    gesture_runtime: GestureService = Depends(get_gesture_service),
):
    try:
        session = service.start_session(payload)
        if session.modality == "gesture":
            try:
                _ensure_gesture_runtime_for_calibration(gesture_runtime)
            except GestureServiceError as exc:
                service.cancel_session(session.session_id)
                raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
            except Exception as exc:
                service.cancel_session(session.session_id)
                raise HTTPException(
                    status_code=503,
                    detail=f"Gestenerkennung konnte nicht gestartet werden: {exc}",
                ) from exc
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.get("/sessions/{session_id}", response_model=CalibrationSessionResponse)
async def get_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.get_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post("/sessions/{session_id}/complete", response_model=CalibrationSessionResponse)
async def complete_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.complete_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post("/sessions/{session_id}/apply", response_model=CalibrationApplyResponse)
async def apply_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
    gesture_runtime: GestureService = Depends(get_gesture_service),
):
    try:
        session, profile = service.apply_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    gesture_runtime.reload_config()
    return CalibrationApplyResponse(session=session, applied_profile=profile)


@calibration_router.post("/sessions/{session_id}/rollback", response_model=CalibrationRollbackResponse)
async def rollback_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
    gesture_runtime: GestureService = Depends(get_gesture_service),
):
    try:
        session, snapshot = service.rollback_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    gesture_runtime.reload_config()
    return CalibrationRollbackResponse(session=session, restored_snapshot=snapshot)


@calibration_router.post("/sessions/{session_id}/cancel", response_model=CalibrationSessionResponse)
async def cancel_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.cancel_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)