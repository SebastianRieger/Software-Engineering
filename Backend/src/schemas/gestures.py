from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from core.config import settings


GestureType = Literal[
    "swipe_left",
    "swipe_right",
    "swipe_up",
    "swipe_down",
    "circle",
    "push_click_short",
    "push_click_long",
    "zoom_out_hands",
    "zoom_in_hands",
]


class GestureStartRequest(BaseModel):
    camera_index: int = Field(default=0, ge=0)


class GestureCameraDeviceResponse(BaseModel):
    index: int = Field(ge=0)
    name: str
    available: bool = True
    backend: str | None = None


class GestureCameraListResponse(BaseModel):
    devices: list[GestureCameraDeviceResponse] = Field(default_factory=list)


class GestureStatusResponse(BaseModel):
    available: bool
    running: bool
    camera_index: int | None = None
    camera_name: str | None = None
    last_gesture: GestureType | None = None
    last_gesture_at: datetime | None = None
    last_confidence: float | None = Field(default=None, ge=0, le=1)
    last_tracking_source: str | None = None
    tracking_quality: float | None = Field(default=None, ge=0, le=1)
    active_phase: Literal["idle", "preparing", "holding", "committing", "releasing", "cooldown"] | None = None
    candidate_scores: dict[str, float] = Field(default_factory=dict)
    reject_reason: str | None = None
    spec_id: str | None = None
    dominant_hand_pose: str | None = None
    primitive_hits: dict[str, float] = Field(default_factory=dict)
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
    tracking_quality: float | None = Field(default=None, ge=0, le=1)
    active_phase: Literal["idle", "preparing", "holding", "committing", "releasing", "cooldown"] | None = None
    candidate_scores: dict[str, float] = Field(default_factory=dict)
    reject_reason: str | None = None
    spec_id: str | None = None
    dominant_hand_pose: str | None = None
    primitive_hits: dict[str, float] = Field(default_factory=dict)


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
    up_threshold: float = Field(default=settings.GESTURE_UP_THRESHOLD, gt=0, le=1)
    swipe_min_span: float = Field(default=settings.GESTURE_SWIPE_MIN_SPAN, gt=0, le=1)
    circle_sweep_min: float = Field(default=settings.GESTURE_CIRCLE_SWEEP_MIN, gt=0)
    circle_radius_cv_max: float = Field(default=settings.GESTURE_CIRCLE_RADIUS_CV_MAX, gt=0)
    circle_min_radius: float = Field(default=settings.GESTURE_CIRCLE_MIN_RADIUS, gt=0, le=1)
    min_detection_points: int = Field(default=settings.GESTURE_MIN_DETECTION_POINTS, ge=4, le=128)
    min_confidence: float = Field(default=settings.GESTURE_MIN_CONFIDENCE, ge=0, le=1)
    hand_size_reference: float = Field(default=settings.GESTURE_HAND_SIZE_REFERENCE, gt=0, le=1)
    hand_size_scale_min: float = Field(default=settings.GESTURE_HAND_SIZE_SCALE_MIN, gt=0, le=4)
    hand_size_scale_max: float = Field(default=settings.GESTURE_HAND_SIZE_SCALE_MAX, gt=0, le=4)
    push_depth_threshold: float = Field(default=settings.GESTURE_PUSH_DEPTH_THRESHOLD, gt=0, le=1)
    push_release_threshold: float = Field(default=settings.GESTURE_PUSH_RELEASE_THRESHOLD, ge=0, le=1)
    push_pose_extension_ratio: float = Field(default=settings.GESTURE_PUSH_POSE_EXTENSION_RATIO, gt=1, le=3)
    center_tolerance: float = Field(default=settings.GESTURE_CENTER_TOLERANCE, gt=0, le=0.5)
    long_click_seconds: float = Field(default=settings.GESTURE_LONG_CLICK_SECONDS, gt=0, le=3)
    zoom_distance_delta_threshold: float = Field(default=settings.GESTURE_ZOOM_DISTANCE_DELTA_THRESHOLD, gt=0, le=1)
    zoom_start_near_distance: float = Field(default=settings.GESTURE_ZOOM_START_NEAR_DISTANCE, gt=0, le=1)
    zoom_start_far_distance: float = Field(default=settings.GESTURE_ZOOM_START_FAR_DISTANCE, gt=0, le=2)
    two_hand_min_frames: int = Field(default=settings.GESTURE_TWO_HAND_MIN_FRAMES, ge=2, le=64)
    updated_at: datetime | None = None


class GestureConfigEnvelope(BaseModel):
    config: GestureConfig
