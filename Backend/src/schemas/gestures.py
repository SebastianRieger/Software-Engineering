from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


GestureType = Literal["swipe_left", "swipe_right", "swipe_down", "circle"]


class GestureStartRequest(BaseModel):
    camera_index: int = Field(default=0, ge=0)


class GestureStatusResponse(BaseModel):
    available: bool
    running: bool
    camera_index: int | None = None
    last_gesture: GestureType | None = None
    last_gesture_at: datetime | None = None
    debug_frame_available: bool = False


class GestureFrameResponse(BaseModel):
    image: str


class GestureEventPayload(BaseModel):
    gesture: GestureType
    timestamp: datetime
    source: Literal["camera"] = "camera"
    hand: str | None = None


class GestureEventEnvelope(BaseModel):
    eventType: Literal["GestureDetected"] = "GestureDetected"
    payload: GestureEventPayload


class GestureVideoProcessingResponse(BaseModel):
    gestures: list[GestureType] = Field(default_factory=list)
    frames_processed: int = Field(ge=0)
    trajectory_points: int = Field(ge=0)
