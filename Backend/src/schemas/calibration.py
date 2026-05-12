from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from schemas.gestures import GestureConfig, GestureType
from schemas.voice import VoiceConfig


CalibrationModality = Literal["gesture", "voice"]
CalibrationSessionStatus = Literal[
    "collecting",
    "analysis_ready",
    "applied",
    "rolled_back",
    "cancelled",
]
CalibrationTakeStatus = Literal["prepared", "recording", "pending_review"]
CalibrationEventType = Literal[
    "CalibrationSessionStarted",
    "CalibrationTargetArmed",
    "CalibrationTakePrepared",
    "CalibrationRecordingStarted",
    "CalibrationRecordingStopped",
    "CalibrationTakeAccepted",
    "CalibrationTakeDiscarded",
    "CalibrationSampleAccepted",
    "CalibrationSampleRejected",
    "CalibrationTargetCompleted",
    "CalibrationAnalysisReady",
    "CalibrationProfileApplied",
    "CalibrationProfileRolledBack",
]


class CalibrationMetricSummary(BaseModel):
    name: str = Field(min_length=1)
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    median_value: float | None = None
    p10_value: float | None = None
    p90_value: float | None = None
    sample_count: int = Field(default=0, ge=0)


class CalibrationRecommendation(BaseModel):
    parameter: str = Field(min_length=1)
    current_value: float
    recommended_value: float
    min_bound: float | None = None
    max_bound: float | None = None
    rationale: str = Field(min_length=1)


class CalibrationTargetDefinition(BaseModel):
    id: str = Field(min_length=1)
    modality: CalibrationModality
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    recommended_repetitions_min: int = Field(default=10, ge=1, le=100)
    recommended_repetitions_max: int = Field(default=20, ge=1, le=100)
    supported: bool = True


class CalibrationModalityDefinition(BaseModel):
    modality: CalibrationModality
    display_name: str = Field(min_length=1)
    supported: bool = True


class CalibrationDefinitionsResponse(BaseModel):
    modalities: list[CalibrationModalityDefinition] = Field(default_factory=list)
    targets: list[CalibrationTargetDefinition] = Field(default_factory=list)


class GestureTrajectorySummary(BaseModel):
    point_count: int = Field(ge=0)
    dx_total: float
    dy_total: float
    span_x: float = Field(ge=0)
    span_y: float = Field(ge=0)
    radius_mean: float | None = Field(default=None, ge=0)
    radius_cv: float | None = Field(default=None, ge=0)
    total_sweep: float | None = None


class GesturePushSampleMetrics(BaseModel):
    pose_valid: bool = False
    forward_depth: float = Field(default=0, ge=0)
    release_depth: float = Field(default=0, ge=0)
    hold_duration_seconds: float | None = Field(default=None, ge=0)
    max_depth: float | None = Field(default=None, ge=0)


class GestureZoomSampleMetrics(BaseModel):
    start_distance: float = Field(ge=0)
    end_distance: float = Field(ge=0)
    delta_distance: float
    frame_count: int = Field(ge=0)


class GestureFingerStateSnapshot(BaseModel):
    extended_score: float = Field(ge=0, le=1)
    curled_score: float = Field(ge=0, le=1)
    spread_score: float = Field(ge=0, le=1)
    tip_depth_relative: float | None = None
    tip_to_palm_distance: float | None = Field(default=None, ge=0)
    label: str


class GesturePoseSnapshot(BaseModel):
    center_distance: float = Field(ge=0)
    hand_openness: float = Field(ge=0, le=1)
    index_extension_ratio: float = Field(ge=0)
    push_depth: float = Field(ge=0)
    dominant_hand_pose: str | None = None
    finger_states: dict[str, GestureFingerStateSnapshot] = Field(default_factory=dict)


class GestureTemporalWindowSummary(BaseModel):
    duration_seconds: float = Field(ge=0)
    frame_count: int = Field(ge=0)
    avg_velocity_x: float
    avg_velocity_y: float
    peak_speed: float = Field(ge=0)
    direction_stability: float = Field(ge=0, le=1)
    hold_stability: float = Field(ge=0, le=1)
    jitter: float = Field(ge=0, le=1)
    active_phase: str
    delta_distance: float | None = None


class GestureSequenceFrame(BaseModel):
    t: float = Field(ge=0)
    x: float
    y: float
    velocity_x: float | None = None
    velocity_y: float | None = None
    hand_openness: float | None = Field(default=None, ge=0, le=1)
    index_extension_ratio: float | None = Field(default=None, ge=0)
    push_depth: float | None = Field(default=None, ge=0)
    center_distance: float | None = Field(default=None, ge=0)
    distance_value: float | None = Field(default=None, ge=0)
    active_phase: str | None = None


class GestureSequenceArtifact(BaseModel):
    point_count: int = Field(ge=0)
    frame_count: int = Field(ge=0)
    anchor_index: int = Field(default=0, ge=0)
    anchor_phase: str | None = None
    origin_x: float
    origin_y: float
    normalized_by_hand_size: bool = False
    frames: list[GestureSequenceFrame] = Field(default_factory=list)


class GestureSequenceProfile(BaseModel):
    profile_id: str = Field(min_length=1)
    gesture: GestureType
    source_sample_ids: list[str] = Field(default_factory=list)
    medoid_sample_id: str = Field(min_length=1)
    distance_threshold: float = Field(ge=0)
    median_distance: float | None = Field(default=None, ge=0)
    p90_distance: float | None = Field(default=None, ge=0)
    sequence: GestureSequenceArtifact


class GestureSequenceProfileSet(BaseModel):
    generated_at: datetime
    resample_points: int = Field(ge=2, le=256)
    window: int | None = Field(default=None, ge=1, le=256)
    channel_names: list[str] = Field(default_factory=list)
    profiles: list[GestureSequenceProfile] = Field(default_factory=list)


class GestureCalibrationSamplePayload(BaseModel):
    gesture: GestureType
    confidence: float = Field(ge=0, le=1)
    tracking_source: str | None = None
    hand: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    hand_size: float | None = Field(default=None, ge=0)
    hand_size_scale: float | None = Field(default=None, ge=0)
    trajectory: GestureTrajectorySummary | None = None
    push: GesturePushSampleMetrics | None = None
    zoom: GestureZoomSampleMetrics | None = None
    pose: GesturePoseSnapshot | None = None
    temporal: GestureTemporalWindowSummary | None = None
    sequence: GestureSequenceArtifact | None = None
    feature_windows: dict[str, Any] = Field(default_factory=dict)


class CalibrationCollectedSample(BaseModel):
    sample_id: str = Field(min_length=1)
    modality: CalibrationModality
    target_id: str = Field(min_length=1)
    accepted: bool = True
    collected_at: datetime
    gesture_payload: GestureCalibrationSamplePayload | None = None


class CalibrationAdvisoryRecognition(BaseModel):
    recognized_target_id: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    tracking_source: str | None = None


class CalibrationTakeRecord(BaseModel):
    take_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    status: CalibrationTakeStatus
    prepared_at: datetime
    countdown_seconds: int = Field(default=3, ge=0, le=30)
    ready_at: datetime | None = None
    recording_started_at: datetime | None = None
    recording_stopped_at: datetime | None = None
    trimmed_tail_ms: int = Field(default=750, ge=0, le=5000)
    sample: CalibrationCollectedSample | None = None
    advisory_recognition: CalibrationAdvisoryRecognition | None = None
    notes: list[str] = Field(default_factory=list)


class CalibrationTargetProgress(BaseModel):
    target_id: str = Field(min_length=1)
    collected_samples: int = Field(default=0, ge=0)
    rejected_samples: int = Field(default=0, ge=0)
    target_repetitions: int = Field(default=0, ge=0)
    completed: bool = False
    last_feedback: str | None = None
    quality_metrics: dict[str, float] = Field(default_factory=dict)


class CalibrationTargetAnalysis(BaseModel):
    target_id: str = Field(min_length=1)
    sample_count: int = Field(default=0, ge=0)
    metrics: list[CalibrationMetricSummary] = Field(default_factory=list)
    recommendations: list[CalibrationRecommendation] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class CalibrationConfigPatchOperation(BaseModel):
    parameter: str = Field(min_length=1)
    path: str = Field(min_length=1)
    current_value: Any = None
    new_value: Any = None
    rationale: str | None = None
    source_targets: list[str] = Field(default_factory=list)


class CalibrationConfigPatch(BaseModel):
    modality: CalibrationModality
    operations: list[CalibrationConfigPatchOperation] = Field(default_factory=list)
    summary: str | None = None


class CalibrationAnalysisResult(BaseModel):
    modality: CalibrationModality
    generated_at: datetime
    targets: list[CalibrationTargetAnalysis] = Field(default_factory=list)
    candidate_gesture_config: GestureConfig | None = None
    candidate_voice_config: VoiceConfig | None = None
    gesture_sequence_profile_set: GestureSequenceProfileSet | None = None
    gesture_config_patch: CalibrationConfigPatch | None = None
    summary: str | None = None


class CalibrationConfigSnapshot(BaseModel):
    modality: CalibrationModality
    profile: str = Field(default="default", min_length=1)
    captured_at: datetime
    gesture_config: GestureConfig | None = None
    gesture_sequence_profile_set: GestureSequenceProfileSet | None = None
    voice_config: VoiceConfig | None = None


class CalibrationSessionRecord(BaseModel):
    session_id: str = Field(min_length=1)
    modality: CalibrationModality
    profile: str = Field(default="default", min_length=1)
    status: CalibrationSessionStatus = "collecting"
    target_repetitions: int = Field(default=10, ge=1, le=100)
    selected_targets: list[str] = Field(default_factory=list)
    active_target_id: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    analysis_ready_at: datetime | None = None
    applied_at: datetime | None = None
    rolled_back_at: datetime | None = None
    cancelled_at: datetime | None = None
    original_snapshot: CalibrationConfigSnapshot
    candidate_snapshot: CalibrationConfigSnapshot | None = None
    applied_snapshot: CalibrationConfigSnapshot | None = None
    active_take: CalibrationTakeRecord | None = None
    pending_take: CalibrationTakeRecord | None = None
    samples: list[CalibrationCollectedSample] = Field(default_factory=list)
    progress: list[CalibrationTargetProgress] = Field(default_factory=list)
    analysis: CalibrationAnalysisResult | None = None
    notes: list[str] = Field(default_factory=list)


class CalibrationProfile(BaseModel):
    modality: CalibrationModality
    profile: str = Field(default="default", min_length=1)
    source_session_id: str = Field(min_length=1)
    saved_at: datetime
    gesture_config: GestureConfig | None = None
    gesture_sequence_profile_set: GestureSequenceProfileSet | None = None
    voice_config: VoiceConfig | None = None
    analysis: CalibrationAnalysisResult | None = None


class CalibrationAppliedSnapshot(BaseModel):
    modality: CalibrationModality
    profile: str = Field(default="default", min_length=1)
    source_session_id: str = Field(min_length=1)
    captured_at: datetime
    original_snapshot: CalibrationConfigSnapshot
    applied_snapshot: CalibrationConfigSnapshot


class CalibrationSessionCreateRequest(BaseModel):
    modality: CalibrationModality
    selected_targets: list[str] = Field(default_factory=list, min_length=1)
    target_repetitions: int = Field(default=10, ge=1, le=100)
    profile: str = Field(default="default", min_length=1)
    camera_index: int | None = Field(default=None, ge=0)


class CalibrationSessionResponse(BaseModel):
    session: CalibrationSessionRecord


class CalibrationApplyResponse(BaseModel):
    session: CalibrationSessionRecord
    applied_profile: CalibrationProfile


class CalibrationRollbackResponse(BaseModel):
    session: CalibrationSessionRecord
    restored_snapshot: CalibrationAppliedSnapshot


class CalibrationEventPayload(BaseModel):
    session_id: str = Field(min_length=1)
    modality: CalibrationModality
    status: CalibrationSessionStatus | None = None
    target_id: str | None = None
    take_id: str | None = None
    sample_id: str | None = None
    collected_samples: int | None = Field(default=None, ge=0)
    target_repetitions: int | None = Field(default=None, ge=0)
    message: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalibrationEventEnvelope(BaseModel):
    eventType: CalibrationEventType
    payload: CalibrationEventPayload