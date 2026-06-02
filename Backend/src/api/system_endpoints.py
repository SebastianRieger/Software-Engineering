from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from core.config import settings
from api.device_endpoints import get_musical_audio_service, get_voice_service
from repositories.app_config import AppConfigRepository, AppConfigRepositoryError
from repositories.config import ConfigRepository
from repositories.weather import WeatherRepository
from schemas.calibration import (
    CalibrationApplyResponse,
    CalibrationDefinitionsResponse,
    CalibrationRollbackResponse,
    CalibrationSessionCreateRequest,
    CalibrationSessionResponse,
)
from schemas.commands import CommandProfilesConfig, CommandProfilesConfigEnvelope
from schemas.configuration import (
    AppConfigEnvelope,
    LayoutConfig,
    LayoutConfigEnvelope,
    SystemConfig,
    SystemConfigEnvelope,
)
from schemas.gestures import (
    GestureCameraListResponse,
    GestureConfig,
    GestureConfigEnvelope,
    GestureDevCaptureResponse,
    GestureFrameResponse,
    GestureStartRequest,
    GestureStatusResponse,
    GestureVideoProcessingResponse,
)
from schemas.interactions import InputActionConfig, InputActionConfigEnvelope
from schemas.interactions import SimulatedInputRequest, SimulatedInputResponse
from schemas.musical_audio import (
    MusicalAudioConfig,
    MusicalAudioConfigEnvelope,
    MusicalAudioTrainingArtifact,
    MusicalAudioTrainingArtifactEnvelope,
    MusicalAudioTrainingArtifactListEnvelope,
)
from schemas.system import ExternalApiHealthResponse, SystemStatusResponse
from schemas.voice import VoiceConfig, VoiceConfigEnvelope
from services.calibration import (
    CalibrationService,
    CalibrationServiceError,
    calibration_service,
)
from services.external_api_health import ExternalApiHealthService
from services.gesture import GestureService, GestureServiceError, gesture_service
from services.interactions import InputOrchestrator, input_orchestrator
from services.musical_audio import MusicalAudioService
from services.voice import VoiceService
from services.weather import WeatherService
from services.news import NewsService

config_router = APIRouter()
system_router = APIRouter()
gesture_router = APIRouter()
calibration_router = APIRouter()


async def get_config_repository() -> ConfigRepository:
    return ConfigRepository()


async def get_app_config_repository() -> AppConfigRepository:
    return AppConfigRepository()


async def get_external_api_health_service(
    app_config_repository: AppConfigRepository = Depends(get_app_config_repository),
) -> ExternalApiHealthService:
    return ExternalApiHealthService(
        weather_service=WeatherService(),
        news_service=NewsService(),
        app_config_repository=app_config_repository,
    )


async def get_gesture_service() -> GestureService:
    return gesture_service


async def get_calibration_service() -> CalibrationService:
    return calibration_service


async def get_input_orchestrator() -> InputOrchestrator:
    return input_orchestrator


def _select_gesture_camera_index(
    service: GestureService, requested_camera_index: int | None = None
) -> int:
    if requested_camera_index is not None:
        return requested_camera_index

    preferred_camera_getter = getattr(service, "get_preferred_camera_index", None)
    if callable(preferred_camera_getter):
        preferred_camera_index = preferred_camera_getter()
        if isinstance(preferred_camera_index, int):
            return preferred_camera_index

    for device in service.list_camera_devices():
        if isinstance(device, dict):
            if device.get("available", True):
                return int(device["index"])
            continue

        if getattr(device, "available", True):
            return int(getattr(device, "index"))
    return 0


def _ensure_gesture_runtime_for_calibration(
    service: GestureService,
    requested_camera_index: int | None = None,
) -> None:
    status = service.get_status()
    if bool(status.get("running")):
        return
    service.start(
        camera_index=_select_gesture_camera_index(service, requested_camera_index)
    )


def _reload_command_runtime_services(
    *,
    gesture_runtime: GestureService,
    voice_runtime: VoiceService,
    musical_audio_runtime: MusicalAudioService,
) -> None:
    gesture_runtime.reload_config()
    voice_runtime.reload_config()
    musical_audio_runtime.reload_config()


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


@config_router.get("/app", response_model=AppConfigEnvelope)
async def get_app_config(
    repository: AppConfigRepository = Depends(get_app_config_repository),
):
    try:
        return AppConfigEnvelope(config=repository.get_app_config())
    except AppConfigRepositoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


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
    voice_runtime: VoiceService = Depends(get_voice_service),
):
    saved_config = repository.save_voice_config(config=config)
    voice_runtime.reload_config()
    return VoiceConfigEnvelope(config=saved_config)


async def _get_input_action_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_input_action_config()
    return InputActionConfigEnvelope(config=config)


async def _save_input_action_config(
    config: InputActionConfig,
    repository: ConfigRepository = Depends(get_config_repository),
    gesture_runtime: GestureService = Depends(get_gesture_service),
    voice_runtime: VoiceService = Depends(get_voice_service),
    musical_audio_runtime: MusicalAudioService = Depends(get_musical_audio_service),
):
    saved_config = repository.save_input_action_config(config=config)
    _reload_command_runtime_services(
        gesture_runtime=gesture_runtime,
        voice_runtime=voice_runtime,
        musical_audio_runtime=musical_audio_runtime,
    )
    return InputActionConfigEnvelope(config=saved_config)


@config_router.get("/command-profiles", response_model=CommandProfilesConfigEnvelope)
async def get_command_profiles_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_command_profiles_config()
    return CommandProfilesConfigEnvelope(config=config)


@config_router.put("/command-profiles", response_model=CommandProfilesConfigEnvelope)
async def save_command_profiles_config(
    config: CommandProfilesConfig,
    repository: ConfigRepository = Depends(get_config_repository),
    gesture_runtime: GestureService = Depends(get_gesture_service),
    voice_runtime: VoiceService = Depends(get_voice_service),
    musical_audio_runtime: MusicalAudioService = Depends(get_musical_audio_service),
):
    saved_config = repository.save_command_profiles_config(config=config)
    _reload_command_runtime_services(
        gesture_runtime=gesture_runtime,
        voice_runtime=voice_runtime,
        musical_audio_runtime=musical_audio_runtime,
    )
    return CommandProfilesConfigEnvelope(config=saved_config)


@config_router.get("/musical-audio", response_model=MusicalAudioConfigEnvelope)
async def get_musical_audio_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    config = repository.get_musical_audio_config()
    return MusicalAudioConfigEnvelope(config=config)


@config_router.put("/musical-audio", response_model=MusicalAudioConfigEnvelope)
async def save_musical_audio_config(
    config: MusicalAudioConfig,
    repository: ConfigRepository = Depends(get_config_repository),
    musical_audio_runtime: MusicalAudioService = Depends(get_musical_audio_service),
):
    saved_config = repository.save_musical_audio_config(config=config)
    musical_audio_runtime.reload_config()
    return MusicalAudioConfigEnvelope(config=saved_config)


@config_router.get(
    "/musical-audio/artifacts", response_model=MusicalAudioTrainingArtifactListEnvelope
)
async def list_musical_audio_training_artifacts(
    profile: str = Query(default="default"),
    repository: ConfigRepository = Depends(get_config_repository),
):
    artifacts = repository.list_musical_audio_training_artifacts(profile_id=profile)
    return MusicalAudioTrainingArtifactListEnvelope(artifacts=artifacts)


@config_router.get(
    "/musical-audio/artifacts/{artifact_id}",
    response_model=MusicalAudioTrainingArtifactEnvelope,
)
async def get_musical_audio_training_artifact(
    artifact_id: str,
    profile: str = Query(default="default"),
    repository: ConfigRepository = Depends(get_config_repository),
):
    artifact = repository.get_musical_audio_training_artifact(
        artifact_id=artifact_id, profile_id=profile
    )
    if artifact is None:
        raise HTTPException(
            status_code=404, detail="Musical-Audio-Artefakt wurde nicht gefunden."
        )
    return MusicalAudioTrainingArtifactEnvelope(artifact=artifact)


@config_router.put(
    "/musical-audio/artifacts/{artifact_id}",
    response_model=MusicalAudioTrainingArtifactEnvelope,
)
async def save_musical_audio_training_artifact(
    artifact_id: str,
    artifact: MusicalAudioTrainingArtifact,
    repository: ConfigRepository = Depends(get_config_repository),
    musical_audio_runtime: MusicalAudioService = Depends(get_musical_audio_service),
):
    payload = (
        artifact
        if artifact.artifact_id == artifact_id
        else artifact.model_copy(update={"artifact_id": artifact_id})
    )
    saved_artifact = repository.save_musical_audio_training_artifact(payload)
    musical_audio_runtime.reload_config()
    return MusicalAudioTrainingArtifactEnvelope(artifact=saved_artifact)


@config_router.delete("/musical-audio/artifacts/{artifact_id}")
async def delete_musical_audio_training_artifact(
    artifact_id: str,
    profile: str = Query(default="default"),
    repository: ConfigRepository = Depends(get_config_repository),
    musical_audio_runtime: MusicalAudioService = Depends(get_musical_audio_service),
):
    deleted = repository.delete_musical_audio_training_artifact(
        artifact_id=artifact_id, profile_id=profile
    )
    if not deleted:
        raise HTTPException(
            status_code=404, detail="Musical-Audio-Artefakt wurde nicht gefunden."
        )
    musical_audio_runtime.reload_config()
    return {"deleted": True, "artifact_id": artifact_id, "profile": profile}


@config_router.get("/input-actions", response_model=InputActionConfigEnvelope)
async def get_input_action_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    return await _get_input_action_config(repository)


@config_router.put("/input-actions", response_model=InputActionConfigEnvelope)
async def save_input_action_config(
    config: InputActionConfig,
    repository: ConfigRepository = Depends(get_config_repository),
    gesture_runtime: GestureService = Depends(get_gesture_service),
    voice_runtime: VoiceService = Depends(get_voice_service),
    musical_audio_runtime: MusicalAudioService = Depends(get_musical_audio_service),
):
    return await _save_input_action_config(
        config,
        repository,
        gesture_runtime,
        voice_runtime,
        musical_audio_runtime,
    )


@config_router.get("/gesture-actions", response_model=InputActionConfigEnvelope)
async def get_legacy_input_action_config(
    repository: ConfigRepository = Depends(get_config_repository),
):
    return await _get_input_action_config(repository)


@config_router.put("/gesture-actions", response_model=InputActionConfigEnvelope)
async def save_legacy_input_action_config(
    config: InputActionConfig,
    repository: ConfigRepository = Depends(get_config_repository),
    gesture_runtime: GestureService = Depends(get_gesture_service),
    voice_runtime: VoiceService = Depends(get_voice_service),
    musical_audio_runtime: MusicalAudioService = Depends(get_musical_audio_service),
):
    return await _save_input_action_config(
        config,
        repository,
        gesture_runtime,
        voice_runtime,
        musical_audio_runtime,
    )


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


@system_router.get(
    "/external-apis/health",
    response_model=ExternalApiHealthResponse,
)
async def get_external_api_health(
    health_service: ExternalApiHealthService = Depends(get_external_api_health_service),
):
    return await health_service.check_all()


@system_router.post("/dev/simulate-input", response_model=SimulatedInputResponse)
async def simulate_input_event(
    payload: SimulatedInputRequest,
    orchestrator: InputOrchestrator = Depends(get_input_orchestrator),
):
    orchestrator.reload_config()
    timestamp = datetime.now(timezone.utc)
    emitted_events: list[str] = []

    if payload.emit_raw_input_event:
        orchestrator.publish_raw_input_detected(
            input_source=payload.input_source,
            raw_input=payload.raw_input,
            timestamp=timestamp,
            metadata=payload.metadata,
        )
        emitted_events.append("RawInputDetected")

    accepted = orchestrator.publish_ui_action_requested(
        input_source=payload.input_source,
        raw_input=payload.raw_input,
        timestamp=timestamp,
        action_args=payload.action_args,
        metadata=payload.metadata,
    )

    emitted_events.append("CommandMatchEvaluated")
    if accepted:
        emitted_events.append("UIActionRequested")

    return SimulatedInputResponse(
        accepted=accepted,
        input_source=payload.input_source,
        raw_input=payload.raw_input,
        action_args=payload.action_args,
        metadata=payload.metadata,
        emitted_events=emitted_events,
    )


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
    frame = service.get_frame()
    if frame is None:
        raise HTTPException(status_code=404, detail="Kein Vorschaubild verfuegbar.")
    if isinstance(frame, str):
        return {"image": frame, "captured_at": None, "frame_age_ms": None}
    return frame


@gesture_router.post("/dev/capture", response_model=GestureDevCaptureResponse)
async def start_dev_capture(
    service: GestureService = Depends(get_gesture_service),
):
    try:
        return service.begin_dev_capture()
    except GestureServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@gesture_router.post(
    "/dev/process-video", response_model=GestureVideoProcessingResponse
)
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
                _ensure_gesture_runtime_for_calibration(
                    gesture_runtime, payload.camera_index
                )
            except GestureServiceError as exc:
                service.cancel_session(session.session_id)
                raise HTTPException(
                    status_code=exc.status_code, detail=str(exc)
                ) from exc
            except Exception as exc:
                service.cancel_session(session.session_id)
                raise HTTPException(
                    status_code=503,
                    detail=f"Gestenerkennung konnte nicht gestartet werden: {exc}",
                ) from exc
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.get(
    "/sessions/{session_id}", response_model=CalibrationSessionResponse
)
async def get_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.get_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post(
    "/sessions/{session_id}/takes/prepare", response_model=CalibrationSessionResponse
)
async def prepare_calibration_take(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.prepare_take(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post(
    "/sessions/{session_id}/takes/start", response_model=CalibrationSessionResponse
)
async def start_calibration_take(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
    gesture_runtime: GestureService = Depends(get_gesture_service),
):
    try:
        session = service.start_take_recording(session_id)
        if session.active_take is None:
            raise HTTPException(status_code=409, detail="Kein aktiver Take vorhanden.")
        gesture_runtime.begin_calibration_take_capture(
            session_id=session.session_id,
            take_id=session.active_take.take_id,
            target_id=session.active_take.target_id,
            trimmed_tail_ms=session.active_take.trimmed_tail_ms,
        )
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except GestureServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post(
    "/sessions/{session_id}/takes/stop", response_model=CalibrationSessionResponse
)
async def stop_calibration_take(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
    gesture_runtime: GestureService = Depends(get_gesture_service),
):
    try:
        session = service.get_session(session_id)
        if session.active_take is None:
            raise CalibrationServiceError(
                "Es laeuft aktuell kein Recording-Take.", status_code=409
            )
        sample, advisory_recognition = gesture_runtime.stop_calibration_take_capture(
            session_id=session.session_id,
            take_id=session.active_take.take_id,
            target_id=session.active_take.target_id,
        )
        session = service.finish_take_recording(
            session_id, sample, advisory_recognition
        )
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except GestureServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post(
    "/sessions/{session_id}/takes/accept", response_model=CalibrationSessionResponse
)
async def accept_calibration_take(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.accept_pending_take(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post(
    "/sessions/{session_id}/takes/discard", response_model=CalibrationSessionResponse
)
async def discard_calibration_take(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.discard_pending_take(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post(
    "/sessions/{session_id}/complete", response_model=CalibrationSessionResponse
)
async def complete_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
):
    try:
        session = service.complete_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)


@calibration_router.post(
    "/sessions/{session_id}/apply", response_model=CalibrationApplyResponse
)
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


@calibration_router.post(
    "/sessions/{session_id}/rollback", response_model=CalibrationRollbackResponse
)
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


@calibration_router.post(
    "/sessions/{session_id}/cancel", response_model=CalibrationSessionResponse
)
async def cancel_calibration_session(
    session_id: str,
    service: CalibrationService = Depends(get_calibration_service),
    gesture_runtime: GestureService = Depends(get_gesture_service),
):
    try:
        gesture_runtime.cancel_calibration_take_capture(session_id=session_id)
        session = service.cancel_session(session_id)
    except CalibrationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return CalibrationSessionResponse(session=session)
