"""Pydantic schemas and typed configuration payloads for gesture APIs."""

from datetime import datetime
from typing import Literal, TypedDict

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
    "pinch_close",
    "pinch_open",
]


class TrajectoryDetectionKwargs(TypedDict):
    """Keyword arguments for offline trajectory gesture detection."""

    swipe_threshold: float
    down_threshold: float
    circle_sweep_min: float
    circle_cv_max: float
    min_detection_points: int
    swipe_min_span: float
    circle_min_radius: float
    min_confidence: float
    hand_size_reference: float
    hand_size_scale_min: float
    hand_size_scale_max: float
    up_threshold: float | None
    horizontal_dominance_ratio: float
    horizontal_max_off_axis_span_ratio: float
    horizontal_max_off_axis_motion_ratio: float
    vertical_dominance_ratio: float
    vertical_max_off_axis_span_ratio: float
    vertical_max_off_axis_motion_ratio: float
    circle_min_aspect_ratio: float


class RuntimeAnalysisKwargs(TypedDict):
    """Keyword arguments for runtime gesture analysis and resolver scoring."""

    swipe_threshold: float
    circle_sweep_min: float
    circle_cv_max: float
    center_tolerance: float
    push_depth_threshold: float
    zoom_delta_threshold: float
    hand_size_reference: float
    phase_hold_max_peak_speed: float
    phase_hold_min_stability: float
    phase_preparing_max_seconds: float
    phase_release_max_recent_speed: float
    phase_release_speed_ratio: float
    phase_commit_distance_threshold: float
    primitive_hand_centered_threshold: float
    primitive_stable_hold_threshold: float
    primitive_index_primary_threshold: float
    primitive_all_fingers_open_threshold: float
    primitive_fist_like_threshold: float
    primitive_push_forward_threshold: float
    primitive_palm_visible_score: float
    primitive_palm_visible_threshold: float
    primitive_swipe_jitter_damping: float
    primitive_circle_motion_threshold: float
    primitive_two_hand_threshold: float
    resolver_push_centered_score_floor: float
    resolver_tracking_quality_trajectory_weight: float
    resolver_tracking_quality_pose_weight: float
    resolver_tracking_quality_hand_weight: float
    resolver_candidate_confidence_weight: float
    resolver_candidate_primitive_weight: float
    resolver_candidate_phase_weight: float
    resolver_required_primitive_min_score: float
    sequence_matching_enabled: bool
    sequence_min_margin: float
    sequence_score_weight: float


class GestureStartRequest(BaseModel):
    """Request body for starting gesture recognition."""

    camera_index: int = Field(default=0, ge=0)


class GestureCameraDeviceResponse(BaseModel):
    """Available camera device reported by the gesture backend."""

    index: int = Field(ge=0)
    name: str
    available: bool = True
    backend: str | None = None


class GestureCameraListResponse(BaseModel):
    """Response containing all discoverable gesture camera devices."""

    devices: list[GestureCameraDeviceResponse] = Field(default_factory=list)


class GestureStatusResponse(BaseModel):
    """Current gesture recognition runtime status."""

    available: bool
    running: bool
    camera_index: int | None = None
    camera_name: str | None = None
    last_gesture: GestureType | None = None
    last_gesture_at: datetime | None = None
    last_confidence: float | None = Field(default=None, ge=0, le=1)
    last_tracking_source: str | None = None
    tracking_quality: float | None = Field(default=None, ge=0, le=1)
    active_phase: (
        Literal["idle", "preparing", "holding", "committing", "releasing", "cooldown"]
        | None
    ) = None
    candidate_scores: dict[str, float] = Field(default_factory=dict)
    sequence_scores: dict[str, float] = Field(default_factory=dict)
    sequence_distances: dict[str, float] = Field(default_factory=dict)
    sequence_margins: dict[str, float] = Field(default_factory=dict)
    sequence_profile_ids: dict[str, str] = Field(default_factory=dict)
    sequence_shadow_mode: bool = False
    sequence_matching_enabled: bool = False
    reject_reason: str | None = None
    spec_id: str | None = None
    dominant_hand_pose: str | None = None
    primitive_hits: dict[str, float] = Field(default_factory=dict)
    debug_frame_available: bool = False
    last_error: str | None = None


class GestureFrameResponse(BaseModel):
    """Latest camera preview frame encoded as a data URL."""

    image: str
    captured_at: datetime | None = None
    frame_age_ms: int | None = None


class GestureEventPayload(BaseModel):
    """Payload published when a camera gesture is detected."""

    gesture: GestureType
    timestamp: datetime
    source: Literal["camera"] = "camera"
    hand: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    tracking_source: str | None = None
    tracking_quality: float | None = Field(default=None, ge=0, le=1)
    active_phase: (
        Literal["idle", "preparing", "holding", "committing", "releasing", "cooldown"]
        | None
    ) = None
    candidate_scores: dict[str, float] = Field(default_factory=dict)
    reject_reason: str | None = None
    spec_id: str | None = None
    dominant_hand_pose: str | None = None
    primitive_hits: dict[str, float] = Field(default_factory=dict)


class GestureEventEnvelope(BaseModel):
    """Realtime envelope for gesture detection events."""

    eventType: Literal["GestureDetected"] = "GestureDetected"
    payload: GestureEventPayload


class GestureVideoProcessingResponse(BaseModel):
    """Summary returned after processing a gesture video file."""

    gestures: list[GestureType] = Field(default_factory=list)
    frames_processed: int = Field(ge=0)
    trajectory_points: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    tracking_source: str | None = None


class GestureDevCaptureResponse(BaseModel):
    """Response returned when a developer frame capture starts."""

    status: Literal["started"]
    output_dir: str
    duration_seconds: float = Field(gt=0, le=10)
    target_fps: float = Field(gt=0, le=60)
    frames_target: int = Field(gt=0, le=600)


class GestureConfig(BaseModel):
    """Runtime gesture detector thresholds and resolver configuration."""

    smoothing_alpha: float = Field(default=settings.GESTURE_SMOOTHING_ALPHA, ge=0, le=1)
    max_trajectory_points: int = Field(
        default=settings.GESTURE_MAX_TRAJECTORY_POINTS, ge=6, le=512
    )
    cooldown_seconds: float = Field(
        default=settings.GESTURE_COOLDOWN_SECONDS, ge=0, le=10
    )
    swipe_threshold: float = Field(default=settings.GESTURE_SWIPE_THRESHOLD, gt=0, le=1)
    down_threshold: float = Field(default=settings.GESTURE_DOWN_THRESHOLD, gt=0, le=1)
    up_threshold: float = Field(default=settings.GESTURE_UP_THRESHOLD, gt=0, le=1)
    swipe_min_span: float = Field(default=settings.GESTURE_SWIPE_MIN_SPAN, gt=0, le=1)
    circle_sweep_min: float = Field(default=settings.GESTURE_CIRCLE_SWEEP_MIN, gt=0)
    circle_radius_cv_max: float = Field(
        default=settings.GESTURE_CIRCLE_RADIUS_CV_MAX, gt=0
    )
    circle_min_radius: float = Field(
        default=settings.GESTURE_CIRCLE_MIN_RADIUS, gt=0, le=1
    )
    min_detection_points: int = Field(
        default=settings.GESTURE_MIN_DETECTION_POINTS, ge=4, le=128
    )
    min_confidence: float = Field(default=settings.GESTURE_MIN_CONFIDENCE, ge=0, le=1)
    hand_size_reference: float = Field(
        default=settings.GESTURE_HAND_SIZE_REFERENCE, gt=0, le=1
    )
    hand_size_scale_min: float = Field(
        default=settings.GESTURE_HAND_SIZE_SCALE_MIN, gt=0, le=4
    )
    hand_size_scale_max: float = Field(
        default=settings.GESTURE_HAND_SIZE_SCALE_MAX, gt=0, le=4
    )
    push_depth_threshold: float = Field(
        default=settings.GESTURE_PUSH_DEPTH_THRESHOLD, gt=0, le=1
    )
    push_release_threshold: float = Field(
        default=settings.GESTURE_PUSH_RELEASE_THRESHOLD, ge=0, le=1
    )
    push_pose_extension_ratio: float = Field(
        default=settings.GESTURE_PUSH_POSE_EXTENSION_RATIO, gt=1, le=3
    )
    center_tolerance: float = Field(
        default=settings.GESTURE_CENTER_TOLERANCE, gt=0, le=0.5
    )
    long_click_seconds: float = Field(
        default=settings.GESTURE_LONG_CLICK_SECONDS, gt=0, le=3
    )
    push_required_folded_fingers: int = Field(
        default=settings.GESTURE_PUSH_REQUIRED_FOLDED_FINGERS, ge=1, le=5
    )
    push_folded_distance_ratio: float = Field(
        default=settings.GESTURE_PUSH_FOLDED_DISTANCE_RATIO, gt=0, le=3
    )
    push_relaxed_center_tolerance_multiplier: float = Field(
        default=settings.GESTURE_PUSH_RELAXED_CENTER_TOLERANCE_MULTIPLIER, gt=0, le=3
    )
    push_relaxed_center_tolerance_max: float = Field(
        default=settings.GESTURE_PUSH_RELAXED_CENTER_TOLERANCE_MAX, gt=0, le=1
    )
    push_depth_assist_min_threshold: float = Field(
        default=settings.GESTURE_PUSH_DEPTH_ASSIST_MIN_THRESHOLD, ge=0, le=1
    )
    push_depth_assist_threshold_ratio: float = Field(
        default=settings.GESTURE_PUSH_DEPTH_ASSIST_THRESHOLD_RATIO, ge=0, le=2
    )
    click_pose_center_tolerance_multiplier: float = Field(
        default=settings.GESTURE_CLICK_POSE_CENTER_TOLERANCE_MULTIPLIER, gt=0, le=3
    )
    click_pose_extension_ratio_multiplier: float = Field(
        default=settings.GESTURE_CLICK_POSE_EXTENSION_RATIO_MULTIPLIER, gt=0, le=3
    )
    click_pose_extension_ratio_floor: float = Field(
        default=settings.GESTURE_CLICK_POSE_EXTENSION_RATIO_FLOOR, gt=0, le=3
    )
    push_transient_pose_gap_max_seconds: float = Field(
        default=settings.GESTURE_PUSH_TRANSIENT_POSE_GAP_MAX_SECONDS, ge=0, le=3
    )
    push_transient_pose_gap_long_ratio: float = Field(
        default=settings.GESTURE_PUSH_TRANSIENT_POSE_GAP_LONG_RATIO, ge=0, le=1
    )
    push_short_click_min_duration: float = Field(
        default=settings.GESTURE_PUSH_SHORT_CLICK_MIN_DURATION, ge=0, le=3
    )
    push_long_release_max_gap_seconds: float = Field(
        default=settings.GESTURE_PUSH_LONG_RELEASE_MAX_GAP_SECONDS, ge=0, le=3
    )
    zoom_distance_delta_threshold: float = Field(
        default=settings.GESTURE_ZOOM_DISTANCE_DELTA_THRESHOLD, gt=0, le=1
    )
    zoom_start_near_distance: float = Field(
        default=settings.GESTURE_ZOOM_START_NEAR_DISTANCE, gt=0, le=1
    )
    zoom_start_far_distance: float = Field(
        default=settings.GESTURE_ZOOM_START_FAR_DISTANCE, gt=0, le=2
    )
    two_hand_min_frames: int = Field(
        default=settings.GESTURE_TWO_HAND_MIN_FRAMES, ge=2, le=64
    )
    pinch_close_threshold: float = Field(
        default=settings.GESTURE_PINCH_CLOSE_THRESHOLD, gt=0, le=1
    )
    pinch_open_threshold: float = Field(
        default=settings.GESTURE_PINCH_OPEN_THRESHOLD, gt=0, le=1
    )
    pinch_smoothing_window: int = Field(
        default=settings.GESTURE_PINCH_SMOOTHING_WINDOW, ge=1, le=24
    )
    pinch_cooldown_seconds: float = Field(
        default=settings.GESTURE_PINCH_COOLDOWN_SECONDS, ge=0, le=3
    )
    pinch_confidence: float = Field(
        default=settings.GESTURE_PINCH_CONFIDENCE, ge=0, le=1
    )
    runtime_circle_pose_max_openness: float = Field(
        default=settings.GESTURE_RUNTIME_CIRCLE_POSE_MAX_OPENNESS, ge=0, le=1
    )
    runtime_swipe_block_max_openness: float = Field(
        default=settings.GESTURE_RUNTIME_SWIPE_BLOCK_MAX_OPENNESS, ge=0, le=1
    )
    runtime_circle_hold_radius_cv_ratio: float = Field(
        default=settings.GESTURE_RUNTIME_CIRCLE_HOLD_RADIUS_CV_RATIO, gt=0, le=2
    )
    runtime_circle_hold_sweep_ratio: float = Field(
        default=settings.GESTURE_RUNTIME_CIRCLE_HOLD_SWEEP_RATIO, gt=0, le=2
    )
    runtime_circle_hold_min_aspect_ratio: float = Field(
        default=settings.GESTURE_RUNTIME_CIRCLE_HOLD_MIN_ASPECT_RATIO, ge=0, le=1
    )
    runtime_upstroke_start_y_min: float = Field(
        default=settings.GESTURE_RUNTIME_UPSTROKE_START_Y_MIN, ge=0, le=1
    )
    runtime_upstroke_end_y_max: float = Field(
        default=settings.GESTURE_RUNTIME_UPSTROKE_END_Y_MAX, ge=0, le=1
    )
    runtime_vertical_displacement_min: float = Field(
        default=settings.GESTURE_RUNTIME_VERTICAL_DISPLACEMENT_MIN, ge=0, le=1
    )
    runtime_downstroke_start_y_max: float = Field(
        default=settings.GESTURE_RUNTIME_DOWNSTROKE_START_Y_MAX, ge=0, le=1
    )
    runtime_downstroke_end_y_min: float = Field(
        default=settings.GESTURE_RUNTIME_DOWNSTROKE_END_Y_MIN, ge=0, le=1
    )
    primitive_hand_centered_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_HAND_CENTERED_THRESHOLD, ge=0, le=1
    )
    primitive_stable_hold_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_STABLE_HOLD_THRESHOLD, ge=0, le=1
    )
    primitive_index_primary_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_INDEX_PRIMARY_THRESHOLD, ge=0, le=1
    )
    primitive_all_fingers_open_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_ALL_FINGERS_OPEN_THRESHOLD, ge=0, le=1
    )
    primitive_fist_like_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_FIST_LIKE_THRESHOLD, ge=0, le=1
    )
    primitive_push_forward_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_PUSH_FORWARD_THRESHOLD, ge=0, le=2
    )
    primitive_palm_visible_score: float = Field(
        default=settings.GESTURE_PRIMITIVE_PALM_VISIBLE_SCORE, ge=0, le=1
    )
    primitive_palm_visible_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_PALM_VISIBLE_THRESHOLD, ge=0, le=1
    )
    primitive_swipe_jitter_damping: float = Field(
        default=settings.GESTURE_PRIMITIVE_SWIPE_JITTER_DAMPING, ge=0, le=2
    )
    primitive_circle_motion_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_CIRCLE_MOTION_THRESHOLD, ge=0, le=1
    )
    primitive_two_hand_threshold: float = Field(
        default=settings.GESTURE_PRIMITIVE_TWO_HAND_THRESHOLD, ge=0, le=1
    )
    resolver_push_centered_score_floor: float = Field(
        default=settings.GESTURE_RESOLVER_PUSH_CENTERED_SCORE_FLOOR, ge=0, le=1
    )
    resolver_tracking_quality_trajectory_weight: float = Field(
        default=settings.GESTURE_RESOLVER_TRACKING_QUALITY_TRAJECTORY_WEIGHT, ge=0, le=1
    )
    resolver_tracking_quality_pose_weight: float = Field(
        default=settings.GESTURE_RESOLVER_TRACKING_QUALITY_POSE_WEIGHT, ge=0, le=1
    )
    resolver_tracking_quality_hand_weight: float = Field(
        default=settings.GESTURE_RESOLVER_TRACKING_QUALITY_HAND_WEIGHT, ge=0, le=1
    )
    resolver_candidate_confidence_weight: float = Field(
        default=settings.GESTURE_RESOLVER_CANDIDATE_CONFIDENCE_WEIGHT, ge=0, le=1
    )
    resolver_candidate_primitive_weight: float = Field(
        default=settings.GESTURE_RESOLVER_CANDIDATE_PRIMITIVE_WEIGHT, ge=0, le=1
    )
    resolver_candidate_phase_weight: float = Field(
        default=settings.GESTURE_RESOLVER_CANDIDATE_PHASE_WEIGHT, ge=0, le=1
    )
    resolver_required_primitive_min_score: float = Field(
        default=settings.GESTURE_RESOLVER_REQUIRED_PRIMITIVE_MIN_SCORE, ge=0, le=1
    )
    sequence_matching_enabled: bool = settings.GESTURE_SEQUENCE_MATCHING_ENABLED
    sequence_shadow_mode: bool = settings.GESTURE_SEQUENCE_SHADOW_MODE
    sequence_resample_points: int = Field(
        default=settings.GESTURE_SEQUENCE_RESAMPLE_POINTS, ge=4, le=128
    )
    sequence_window: int = Field(default=settings.GESTURE_SEQUENCE_WINDOW, ge=1, le=64)
    sequence_min_margin: float = Field(
        default=settings.GESTURE_SEQUENCE_MIN_MARGIN, ge=0, le=10
    )
    sequence_score_weight: float = Field(
        default=settings.GESTURE_SEQUENCE_SCORE_WEIGHT, ge=0, le=1
    )
    candidate_horizontal_dominance_ratio: float = Field(
        default=settings.GESTURE_CANDIDATE_HORIZONTAL_DOMINANCE_RATIO, gt=0, le=10
    )
    candidate_horizontal_max_off_axis_span_ratio: float = Field(
        default=settings.GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_SPAN_RATIO,
        gt=0,
        le=10,
    )
    candidate_horizontal_max_off_axis_motion_ratio: float = Field(
        default=settings.GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_MOTION_RATIO,
        gt=0,
        le=10,
    )
    candidate_vertical_dominance_ratio: float = Field(
        default=settings.GESTURE_CANDIDATE_VERTICAL_DOMINANCE_RATIO, gt=0, le=10
    )
    candidate_vertical_max_off_axis_span_ratio: float = Field(
        default=settings.GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_SPAN_RATIO, gt=0, le=10
    )
    candidate_vertical_max_off_axis_motion_ratio: float = Field(
        default=settings.GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_MOTION_RATIO,
        gt=0,
        le=10,
    )
    candidate_circle_min_aspect_ratio: float = Field(
        default=settings.GESTURE_CANDIDATE_CIRCLE_MIN_ASPECT_RATIO, ge=0, le=1
    )
    phase_hold_max_peak_speed: float = Field(
        default=settings.GESTURE_PHASE_HOLD_MAX_PEAK_SPEED, ge=0, le=10
    )
    phase_hold_min_stability: float = Field(
        default=settings.GESTURE_PHASE_HOLD_MIN_STABILITY, ge=0, le=1
    )
    phase_preparing_max_seconds: float = Field(
        default=settings.GESTURE_PHASE_PREPARING_MAX_SECONDS, ge=0, le=3
    )
    phase_release_max_recent_speed: float = Field(
        default=settings.GESTURE_PHASE_RELEASE_MAX_RECENT_SPEED, ge=0, le=10
    )
    phase_release_speed_ratio: float = Field(
        default=settings.GESTURE_PHASE_RELEASE_SPEED_RATIO, ge=0, le=1
    )
    phase_commit_distance_threshold: float = Field(
        default=settings.GESTURE_PHASE_COMMIT_DISTANCE_THRESHOLD, ge=0, le=2
    )
    pending_timeout_seconds: float = Field(
        default=settings.GESTURE_PENDING_TIMEOUT_SECONDS, ge=0, le=3
    )
    pending_finalize_seconds: float = Field(
        default=settings.GESTURE_PENDING_FINALIZE_SECONDS, ge=0, le=3
    )
    pending_long_finalize_seconds: float = Field(
        default=settings.GESTURE_PENDING_LONG_FINALIZE_SECONDS, ge=0, le=3
    )
    post_fire_grace_seconds: float = Field(
        default=settings.GESTURE_POST_FIRE_GRACE_SECONDS, ge=0, le=3
    )
    offline_swipe_min_cycle_points: int = Field(
        default=settings.GESTURE_OFFLINE_SWIPE_MIN_CYCLE_POINTS, ge=2, le=128
    )
    offline_swipe_motion_step_threshold: float = Field(
        default=settings.GESTURE_OFFLINE_SWIPE_MOTION_STEP_THRESHOLD, gt=0, le=1
    )
    offline_swipe_edge_speed_threshold: float = Field(
        default=settings.GESTURE_OFFLINE_SWIPE_EDGE_SPEED_THRESHOLD, gt=0, le=10
    )
    offline_swipe_active_gap_seconds: float = Field(
        default=settings.GESTURE_OFFLINE_SWIPE_ACTIVE_GAP_SECONDS, ge=0, le=3
    )
    offline_swipe_axis_ratio_threshold: float = Field(
        default=settings.GESTURE_OFFLINE_SWIPE_AXIS_RATIO_THRESHOLD, gt=0, le=10
    )
    offline_swipe_edge_gap_ratio: float = Field(
        default=settings.GESTURE_OFFLINE_SWIPE_EDGE_GAP_RATIO, gt=0, le=2
    )
    offline_swipe_edge_gap_max_seconds: float = Field(
        default=settings.GESTURE_OFFLINE_SWIPE_EDGE_GAP_MAX_SECONDS, ge=0, le=3
    )
    offline_push_min_cycle_points: int = Field(
        default=settings.GESTURE_OFFLINE_PUSH_MIN_CYCLE_POINTS, ge=2, le=128
    )
    offline_push_active_gap_seconds: float = Field(
        default=settings.GESTURE_OFFLINE_PUSH_ACTIVE_GAP_SECONDS, ge=0, le=3
    )
    offline_push_min_pose_valid_ratio: float = Field(
        default=settings.GESTURE_OFFLINE_PUSH_MIN_POSE_VALID_RATIO, ge=0, le=1
    )
    offline_push_inactive_grace_seconds: float = Field(
        default=settings.GESTURE_OFFLINE_PUSH_INACTIVE_GRACE_SECONDS, ge=0, le=3
    )
    updated_at: datetime | None = None

    def offline_swipe_cycle_kwargs(self) -> dict[str, float | int]:
        """Return swipe-cycle detector options derived from the config."""

        return {
            "min_cycle_points": self.offline_swipe_min_cycle_points,
            "motion_step_threshold": self.offline_swipe_motion_step_threshold,
            "edge_speed_threshold": self.offline_swipe_edge_speed_threshold,
            "active_gap_seconds": self.offline_swipe_active_gap_seconds,
            "axis_ratio_threshold": self.offline_swipe_axis_ratio_threshold,
            "min_cycle_displacement": self.swipe_threshold,
            "edge_gap_ratio": self.offline_swipe_edge_gap_ratio,
            "edge_gap_max_seconds": self.offline_swipe_edge_gap_max_seconds,
        }

    def offline_push_cycle_kwargs(self) -> dict[str, float | int]:
        """Return push-cycle detector options derived from the config."""

        return {
            "min_cycle_points": self.offline_push_min_cycle_points,
            "activation_depth_threshold": self.push_depth_threshold,
            "release_depth_threshold": self.push_release_threshold,
            "active_gap_seconds": self.offline_push_active_gap_seconds,
            "min_pose_valid_ratio": self.offline_push_min_pose_valid_ratio,
            "min_index_extension_ratio": self.push_pose_extension_ratio,
            "min_folded_fingers": self.push_required_folded_fingers,
            "center_distance_max": self.center_tolerance,
            "long_click_seconds": self.long_click_seconds,
            "inactive_grace_seconds": self.offline_push_inactive_grace_seconds,
        }

    def trajectory_detection_kwargs(self) -> TrajectoryDetectionKwargs:
        """Return options for trajectory-only gesture detection."""

        return {
            "swipe_threshold": self.swipe_threshold,
            "down_threshold": self.down_threshold,
            "circle_sweep_min": self.circle_sweep_min,
            "circle_cv_max": self.circle_radius_cv_max,
            "min_detection_points": self.min_detection_points,
            "swipe_min_span": self.swipe_min_span,
            "circle_min_radius": self.circle_min_radius,
            "min_confidence": self.min_confidence,
            "hand_size_reference": self.hand_size_reference,
            "hand_size_scale_min": self.hand_size_scale_min,
            "hand_size_scale_max": self.hand_size_scale_max,
            "up_threshold": self.up_threshold,
            "horizontal_dominance_ratio": self.candidate_horizontal_dominance_ratio,
            "horizontal_max_off_axis_span_ratio": self.candidate_horizontal_max_off_axis_span_ratio,
            "horizontal_max_off_axis_motion_ratio": (
                self.candidate_horizontal_max_off_axis_motion_ratio
            ),
            "vertical_dominance_ratio": self.candidate_vertical_dominance_ratio,
            "vertical_max_off_axis_span_ratio": self.candidate_vertical_max_off_axis_span_ratio,
            "vertical_max_off_axis_motion_ratio": self.candidate_vertical_max_off_axis_motion_ratio,
            "circle_min_aspect_ratio": self.candidate_circle_min_aspect_ratio,
        }

    def runtime_analysis_kwargs(self) -> RuntimeAnalysisKwargs:
        """Return options for runtime gesture analysis."""

        return {
            "swipe_threshold": self.swipe_threshold,
            "circle_sweep_min": self.circle_sweep_min,
            "circle_cv_max": self.circle_radius_cv_max,
            "center_tolerance": self.center_tolerance,
            "push_depth_threshold": self.push_depth_threshold,
            "zoom_delta_threshold": self.zoom_distance_delta_threshold,
            "hand_size_reference": self.hand_size_reference,
            "phase_hold_max_peak_speed": self.phase_hold_max_peak_speed,
            "phase_hold_min_stability": self.phase_hold_min_stability,
            "phase_preparing_max_seconds": self.phase_preparing_max_seconds,
            "phase_release_max_recent_speed": self.phase_release_max_recent_speed,
            "phase_release_speed_ratio": self.phase_release_speed_ratio,
            "phase_commit_distance_threshold": self.phase_commit_distance_threshold,
            "primitive_hand_centered_threshold": self.primitive_hand_centered_threshold,
            "primitive_stable_hold_threshold": self.primitive_stable_hold_threshold,
            "primitive_index_primary_threshold": self.primitive_index_primary_threshold,
            "primitive_all_fingers_open_threshold": self.primitive_all_fingers_open_threshold,
            "primitive_fist_like_threshold": self.primitive_fist_like_threshold,
            "primitive_push_forward_threshold": self.primitive_push_forward_threshold,
            "primitive_palm_visible_score": self.primitive_palm_visible_score,
            "primitive_palm_visible_threshold": self.primitive_palm_visible_threshold,
            "primitive_swipe_jitter_damping": self.primitive_swipe_jitter_damping,
            "primitive_circle_motion_threshold": self.primitive_circle_motion_threshold,
            "primitive_two_hand_threshold": self.primitive_two_hand_threshold,
            "resolver_push_centered_score_floor": self.resolver_push_centered_score_floor,
            "resolver_tracking_quality_trajectory_weight": (
                self.resolver_tracking_quality_trajectory_weight
            ),
            "resolver_tracking_quality_pose_weight": self.resolver_tracking_quality_pose_weight,
            "resolver_tracking_quality_hand_weight": self.resolver_tracking_quality_hand_weight,
            "resolver_candidate_confidence_weight": self.resolver_candidate_confidence_weight,
            "resolver_candidate_primitive_weight": self.resolver_candidate_primitive_weight,
            "resolver_candidate_phase_weight": self.resolver_candidate_phase_weight,
            "resolver_required_primitive_min_score": self.resolver_required_primitive_min_score,
            "sequence_matching_enabled": self.sequence_matching_enabled,
            "sequence_min_margin": self.sequence_min_margin,
            "sequence_score_weight": self.sequence_score_weight,
        }


class GestureConfigEnvelope(BaseModel):
    """Response envelope for gesture detector configuration."""

    config: GestureConfig
