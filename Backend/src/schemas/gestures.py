from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from core.config import settings


GestureType = Literal["swipe_left", "swipe_right", "swipe_down", "circle"]


class GestureStartRequest(BaseModel):
    camera_index: int = Field(default=0, ge=0)


class GestureStatusResponse(BaseModel):
    available: bool
    running: bool
    camera_index: int | None = None
    last_gesture: GestureType | None = None
    last_gesture_at: datetime | None = None
    last_confidence: float | None = Field(default=None, ge=0, le=1)
    last_tracking_source: str | None = None
    debug_frame_available: bool = False
    last_error: str | None = None


class GestureFrameResponse(BaseModel):
    image: str


class GestureEventPayload(BaseModel):
    gesture: GestureType
    timestamp: datetime
    source: Literal["camera"] = "camera"
    hand: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    tracking_source: str | None = None


class GestureEventEnvelope(BaseModel):
    eventType: Literal["GestureDetected"] = "GestureDetected"
    payload: GestureEventPayload


class GestureVideoProcessingResponse(BaseModel):
    gestures: list[GestureType] = Field(default_factory=list)
    frames_processed: int = Field(ge=0)
    trajectory_points: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    tracking_source: str | None = None


class GestureConfig(BaseModel):
    smoothing_alpha: float = Field(default=settings.GESTURE_SMOOTHING_ALPHA, ge=0, le=1)
    max_trajectory_points: int = Field(default=settings.GESTURE_MAX_TRAJECTORY_POINTS, ge=6, le=512)
    cooldown_seconds: float = Field(default=settings.GESTURE_COOLDOWN_SECONDS, ge=0, le=10)
    swipe_threshold: float = Field(default=settings.GESTURE_SWIPE_THRESHOLD, gt=0, le=1)
    down_threshold: float = Field(default=settings.GESTURE_DOWN_THRESHOLD, gt=0, le=1)
    swipe_min_span: float = Field(default=settings.GESTURE_SWIPE_MIN_SPAN, gt=0, le=1)
    circle_sweep_min: float = Field(default=settings.GESTURE_CIRCLE_SWEEP_MIN, gt=0)
    circle_radius_cv_max: float = Field(default=settings.GESTURE_CIRCLE_RADIUS_CV_MAX, gt=0)
    circle_min_radius: float = Field(default=settings.GESTURE_CIRCLE_MIN_RADIUS, gt=0, le=1)
    min_detection_points: int = Field(default=settings.GESTURE_MIN_DETECTION_POINTS, ge=4, le=128)
    min_confidence: float = Field(default=settings.GESTURE_MIN_CONFIDENCE, ge=0, le=1)
    updated_at: datetime | None = None


class GestureConfigEnvelope(BaseModel):
    config: GestureConfig
