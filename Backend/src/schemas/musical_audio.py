from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from core.config import settings

MusicalAudioStatusCode = Literal[
    "unavailable",
    "ready",
    "running",
    "configuration_disabled",
    "no_active_artifact",
    "device_missing",
    "invalid_sample_rate",
    "permission_blocked",
    "runtime_start_failed",
    "runtime_running_no_matchable_artifacts",
]


class MusicalAudioStartRequest(BaseModel):
    device_index: int = Field(default=settings.MUSICAL_AUDIO_DEVICE_INDEX, ge=-1)


class MusicalAudioInputDeviceResponse(BaseModel):
    index: int = Field(ge=0)
    name: str
    max_input_channels: int = Field(ge=0)
    default_samplerate: float | None = Field(default=None, ge=0)
    is_default: bool = False


class MusicalAudioInputDeviceListResponse(BaseModel):
    devices: list[MusicalAudioInputDeviceResponse] = Field(default_factory=list)


class MusicalAudioStatusResponse(BaseModel):
    message: str
    available: bool
    enabled: bool = True
    running: bool
    status_code: MusicalAudioStatusCode = "unavailable"
    mode: Literal["unavailable", "direct-mic"] = "unavailable"
    provider: str | None = None
    active_profile_id: str | None = None
    device_index: int | None = None
    device_name: str | None = None
    sample_rate: int | None = None
    block_size: int | None = None
    queue_max_chunks: int | None = None
    active_artifact_id: str | None = None
    artifacts_loaded: int = 0
    validated_device_index: int | None = None
    validated_sample_rate: int | None = None
    last_pitch_hz: float | None = None
    last_match: str | None = None
    last_match_score: float | None = None
    last_event_at: datetime | None = None
    last_error: str | None = None
    last_error_code: MusicalAudioStatusCode | None = None


class MusicalAudioConfig(BaseModel):
    enabled: bool = settings.MUSICAL_AUDIO_ENABLED
    device_index: int = Field(default=settings.MUSICAL_AUDIO_DEVICE_INDEX, ge=-1)
    sample_rate: int = Field(
        default=settings.MUSICAL_AUDIO_SAMPLE_RATE, ge=8000, le=48000
    )
    block_size: int = Field(default=settings.MUSICAL_AUDIO_BLOCK_SIZE, ge=256, le=8192)
    queue_max_chunks: int = Field(
        default=settings.MUSICAL_AUDIO_QUEUE_MAX_CHUNKS, ge=1, le=256
    )
    silence_threshold: float = Field(
        default=settings.MUSICAL_AUDIO_SILENCE_THRESHOLD, ge=0, le=1
    )
    pitch_confidence_threshold: float = Field(
        default=settings.MUSICAL_AUDIO_PITCH_CONFIDENCE_THRESHOLD,
        ge=0,
        le=1,
    )
    command_cooldown_seconds: float = Field(
        default=settings.MUSICAL_AUDIO_COMMAND_COOLDOWN_SECONDS,
        ge=0,
        le=30,
    )
    min_pattern_notes: int = Field(
        default=settings.MUSICAL_AUDIO_MIN_PATTERN_NOTES, ge=1, le=64
    )
    max_pattern_window_seconds: float = Field(
        default=settings.MUSICAL_AUDIO_MAX_PATTERN_WINDOW_SECONDS,
        ge=0.2,
        le=30,
    )
    active_artifact_id: str | None = None
    updated_at: datetime | None = None


class MusicalAudioConfigEnvelope(BaseModel):
    config: MusicalAudioConfig


class MusicalAudioNoteEvent(BaseModel):
    relative_pitch_semitones: float
    relative_time_seconds: float = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)


class MusicalAudioTrainingArtifact(BaseModel):
    artifact_id: str = Field(min_length=1)
    profile_id: str = Field(default="default", min_length=1)
    raw_input: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    source_hint: Literal["whistle", "voice", "instrument", "unknown"] = "whistle"
    notes: list[MusicalAudioNoteEvent] = Field(default_factory=list)
    match_threshold: float = Field(default=3.0, ge=0)
    minimum_confidence: float = Field(default=0.6, ge=0, le=1)
    sample_count: int = Field(default=0, ge=0)
    enabled: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MusicalAudioTrainingArtifactEnvelope(BaseModel):
    artifact: MusicalAudioTrainingArtifact


class MusicalAudioTrainingArtifactListEnvelope(BaseModel):
    artifacts: list[MusicalAudioTrainingArtifact] = Field(default_factory=list)
