from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from core.config import settings
from schemas.interactions import UIActionArguments


class VoiceStartRequest(BaseModel):
    device_index: int = Field(default=settings.VOICE_DEVICE_INDEX, ge=-1)


class VoiceInputDeviceResponse(BaseModel):
    index: int = Field(ge=0)
    name: str
    max_input_channels: int = Field(ge=0)
    default_samplerate: float | None = Field(default=None, ge=0)
    is_default: bool = False


class VoiceInputDeviceListResponse(BaseModel):
    devices: list[VoiceInputDeviceResponse] = Field(default_factory=list)


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


class VoiceSignalDefinition(BaseModel):
    raw_input: str = Field(min_length=1)
    phrases: list[str] = Field(default_factory=list)
    action_args: UIActionArguments = Field(default_factory=UIActionArguments)


def build_default_voice_signals() -> list[VoiceSignalDefinition]:
    return [
        VoiceSignalDefinition(raw_input=raw_input, phrases=list(phrases))
        for raw_input, phrases in settings.VOICE_SIGNAL_SYNONYMS.items()
    ]


def build_default_widget_aliases() -> dict[str, list[str]]:
    return {
        widget_type: list(aliases)
        for widget_type, aliases in settings.VOICE_WIDGET_ALIASES.items()
    }


class VoiceConfig(BaseModel):
    enabled: bool = settings.VOICE_ENABLED
    device_index: int = Field(default=settings.VOICE_DEVICE_INDEX, ge=-1)
    sample_rate: int = Field(default=settings.VOICE_SAMPLE_RATE, ge=8000, le=48000)
    block_size: int = Field(default=settings.VOICE_BLOCK_SIZE, ge=256, le=8192)
    queue_max_chunks: int = Field(default=settings.VOICE_QUEUE_MAX_CHUNKS, ge=1, le=256)
    energy_threshold: float = Field(default=settings.VOICE_ENERGY_THRESHOLD, ge=0, le=32768)
    command_cooldown_seconds: float = Field(default=settings.VOICE_COMMAND_COOLDOWN_SECONDS, ge=0, le=30)
    partial_results_enabled: bool = settings.VOICE_PARTIAL_RESULTS_ENABLED
    grid_cell_count: int = Field(default=settings.VOICE_GRID_CELL_COUNT, ge=1, le=64)
    commands: list[str] = Field(default_factory=lambda: list(settings.VOICE_COMMANDS))
    signals: list[VoiceSignalDefinition] = Field(default_factory=build_default_voice_signals)
    widget_aliases: dict[str, list[str]] = Field(default_factory=build_default_widget_aliases)
    updated_at: datetime | None = None


class VoiceConfigEnvelope(BaseModel):
    config: VoiceConfig


class VoiceCommandEventPayload(BaseModel):
    command: str
    raw_input: str = Field(min_length=1)
    timestamp: datetime
    source: Literal["microphone"] = "microphone"
    transcript: str | None = None
    partial: bool = False
    device_index: int | None = None


class VoiceCommandEventEnvelope(BaseModel):
    eventType: Literal["VoiceCommandDetected"] = "VoiceCommandDetected"
    payload: VoiceCommandEventPayload