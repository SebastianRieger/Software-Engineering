from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from core.config import settings


class VoiceStartRequest(BaseModel):
    device_index: int = Field(default=settings.VOICE_DEVICE_INDEX, ge=-1)


class VoiceStatusResponse(BaseModel):
    message: str
    available: bool
    enabled: bool = True
    running: bool
    mode: Literal["skeleton", "unavailable", "direct-mic"] = "unavailable"
    provider: str | None = None
    device_index: int | None = None
    device_name: str | None = None
    sample_rate: int | None = None
    block_size: int | None = None
    queue_max_chunks: int | None = None
    commands: list[str] = Field(default_factory=list)
    partial_results_enabled: bool = False
    command_cooldown_seconds: float | None = None
    chunks_processed: int = 0
    chunks_dropped: int = 0
    last_audio_level: float | None = None
    last_transcript: str | None = None
    last_command: str | None = None
    last_command_at: datetime | None = None
    last_error: str | None = None


class VoiceConfig(BaseModel):
    enabled: bool = settings.VOICE_ENABLED
    device_index: int = Field(default=settings.VOICE_DEVICE_INDEX, ge=-1)
    sample_rate: int = Field(default=settings.VOICE_SAMPLE_RATE, ge=8000, le=48000)
    block_size: int = Field(default=settings.VOICE_BLOCK_SIZE, ge=256, le=8192)
    queue_max_chunks: int = Field(default=settings.VOICE_QUEUE_MAX_CHUNKS, ge=1, le=256)
    energy_threshold: float = Field(default=settings.VOICE_ENERGY_THRESHOLD, ge=0, le=32768)
    command_cooldown_seconds: float = Field(default=settings.VOICE_COMMAND_COOLDOWN_SECONDS, ge=0, le=30)
    partial_results_enabled: bool = settings.VOICE_PARTIAL_RESULTS_ENABLED
    commands: list[str] = Field(default_factory=lambda: list(settings.VOICE_COMMANDS))
    updated_at: datetime | None = None


class VoiceConfigEnvelope(BaseModel):
    config: VoiceConfig


class VoiceCommandEventPayload(BaseModel):
    command: str
    timestamp: datetime
    source: Literal["microphone"] = "microphone"
    transcript: str | None = None
    partial: bool = False
    device_index: int | None = None


class VoiceCommandEventEnvelope(BaseModel):
    eventType: Literal["VoiceCommandDetected"] = "VoiceCommandDetected"
    payload: VoiceCommandEventPayload