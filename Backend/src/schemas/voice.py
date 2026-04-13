from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VoiceStartRequest(BaseModel):
    device_index: int = Field(default=0, ge=0)


class VoiceStatusResponse(BaseModel):
    message: str
    available: bool
    running: bool
    mode: Literal["skeleton", "unavailable"] = "unavailable"
    provider: str | None = None
    device_index: int | None = None
    last_command: str | None = None
    last_command_at: datetime | None = None
    last_error: str | None = None