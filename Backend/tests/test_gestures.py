import asyncio
import math
import threading
import time
from concurrent.futures import Future
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect

from core.config import settings
from core.realtime import realtime_hub
from main import websocket_endpoint
from schemas.calibration import (
    GestureSequenceArtifact,
    GestureSequenceFrame,
    GestureSequenceProfile,
    GestureSequenceProfileSet,
)
from schemas.gestures import GestureConfig
from schemas.interactions import InputActionConfig, InputActionMapping
from services.gesture.detection import (
    build_detection_context,
    build_runtime_gesture_specs,
    GestureDetectionResult,
    analyze_runtime_gesture,
    detect_gesture_candidates,
    detect_gesture_with_confidence,
    detect_gesture_from_trajectory,
    extract_temporal_gesture_window,
    extract_gesture_features,
    select_best_gesture_candidate,
)
from services.gesture.push_runtime import (
    compute_push_pose_snapshot,
    detect_push_gesture,
)
from services.gesture.pinch_runtime import PinchGestureState, detect_pinch_gesture
from services.gesture.runtime import GestureService, GestureServiceError
from services.gesture.tracking import (
    HAND_LANDMARK_NAMES,
    FingerState,
    HandPoseFeatures,
    GestureAdapterError,
    GestureObservation,
    TrackedHandObservation,
    build_hand_landmark_map,
    compute_hand_size_scale,
    compute_hand_tracking_point,
    PinchContactMetrics,
    compute_pinch_contact_metrics,
    estimate_hand_size,
    extract_hand_pose_features,
)


class CapturingRealtimeHub:
    def __init__(self):
        self.messages = []

    def publish_from_thread(self, message):
        self.messages.append(message)
        future = Future()
        future.set_result(None)
        return future


class CapturingCalibrationRuntime:
    def __init__(self):
        self.samples = []

    def has_active_session(self, modality="gesture"):
        return modality == "gesture"

    def capture_gesture_sample(self, sample):
        self.samples.append(sample)
        return None


class StaticGestureConfigRepository:
    def __init__(
        self,
        config: GestureConfig | None = None,
        input_action_config: InputActionConfig | None = None,
        sequence_profile_set: GestureSequenceProfileSet | None = None,
    ):
        self.config = config or GestureConfig()
        self.input_action_config = input_action_config or InputActionConfig()
        self.sequence_profile_set = sequence_profile_set

    def get_gesture_config(self):
        return self.config

    def get_input_action_config(self):
        return self.input_action_config

    def get_active_gesture_sequence_profile_set(self):
        return self.sequence_profile_set


class MutableGestureConfigRepository(StaticGestureConfigRepository):
    def set_config(self, config: GestureConfig):
        self.config = config


class SequenceAdapter:
    def __init__(self, observations=None, available=True):
        self.observations = list(observations or [])
        self.available = available
        self.opened = False
        self.closed = False
        self.camera_index = None

    def is_available(self):
        return self.available

    def open(self, camera_index: int):
        if not self.available:
            raise RuntimeError("adapter unavailable")
        self.opened = True
        self.camera_index = camera_index

    def read(self):
        if not self.opened:
            return None
        if self.observations:
            return self.observations.pop(0)
        time.sleep(0.01)
        return GestureObservation(point=None)

    def close(self):
        self.closed = True

    def process_video(self, _video_path, classifier, _smoothing_alpha, tracking_source):
        trajectory = [
            (0.5, 0.2),
            (0.5, 0.3),
            (0.5, 0.4),
            (0.5, 0.5),
            (0.5, 0.6),
            (0.5, 0.8),
        ]
        detection = classifier(trajectory, None)
        return {
            "gestures": [detection.gesture] if detection else [],
            "frames_processed": 6,
            "trajectory_points": len(trajectory),
            "confidence": detection.confidence if detection else None,
            "tracking_source": (
                detection.tracking_source if detection else tracking_source
            ),
        }


class PausingSequenceAdapter(SequenceAdapter):
    def __init__(self, observations=None, available=True, pause_after_reads=0):
        super().__init__(observations=observations, available=available)
        self.pause_after_reads = pause_after_reads
        self.pause_event = threading.Event()
        self.resume_event = threading.Event()
        self._pause_consumed = False
        self._reads = 0

    def read(self):
        if not self._pause_consumed and self._reads >= self.pause_after_reads:
            self._pause_consumed = True
            self.pause_event.set()
            self.resume_event.wait(timeout=1.0)
        observation = super().read()
        if observation is not None and observation.point is not None:
            self._reads += 1
        return observation


class FailingAdapter(SequenceAdapter):
    def read(self):
        raise GestureAdapterError("camera read failed")


class FlakyAdapter(SequenceAdapter):
    def __init__(self, observations=None, failures_before_success=1):
        super().__init__(observations=observations)
        self.failures_before_success = failures_before_success
        self.failures_seen = 0

    def read(self):
        if self.failures_seen < self.failures_before_success:
            self.failures_seen += 1
            raise GestureAdapterError(f"transient failure {self.failures_seen}")
        return super().read()


class ResolvedIndexAdapter(SequenceAdapter):
    def open(self, camera_index: int):
        super().open(camera_index)
        self.camera_index = camera_index + 1


class TimedObservationAdapter(SequenceAdapter):
    def __init__(self, observations=None, event_after=None):
        super().__init__(observations=observations)
        self.event_after = event_after
        self.read_count = 0

    def read(self):
        self.read_count += 1
        if self.event_after is not None and self.read_count == self.event_after:
            time.sleep(0.05)
        return super().read()


class FakeLandmark:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class FakeHandLandmarks:
    def __init__(self):
        self.landmark = [FakeLandmark(0.0, 0.0) for _ in range(21)]
        self.landmark[0] = FakeLandmark(0.4, 0.6)
        self.landmark[5] = FakeLandmark(0.45, 0.45)
        self.landmark[9] = FakeLandmark(0.5, 0.4)
        self.landmark[13] = FakeLandmark(0.55, 0.45)
        self.landmark[17] = FakeLandmark(0.6, 0.5)
        self.landmark[4] = FakeLandmark(0.38, 0.48)
        self.landmark[8] = FakeLandmark(0.46, 0.25)
        self.landmark[12] = FakeLandmark(0.5, 0.22)
        self.landmark[16] = FakeLandmark(0.55, 0.27)
        self.landmark[20] = FakeLandmark(0.62, 0.34)


def filter_messages(messages, event_type: str):
    return [message for message in messages if message["eventType"] == event_type]


def make_sequence_profile_set(gesture: str = "swipe_left") -> GestureSequenceProfileSet:
    return GestureSequenceProfileSet(
        generated_at=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
        resample_points=24,
        window=6,
        channel_names=[
            "x",
            "y",
            "velocity_x",
            "velocity_y",
            "hand_openness",
            "index_extension_ratio",
            "push_depth",
            "center_distance",
        ],
        profiles=[
            GestureSequenceProfile(
                profile_id=f"{gesture}:primary",
                gesture=gesture,
                source_sample_ids=[f"sample-{gesture}-1", f"sample-{gesture}-2"],
                medoid_sample_id=f"sample-{gesture}-1",
                distance_threshold=100.0,
                median_distance=0.16,
                p90_distance=0.22,
                sequence=GestureSequenceArtifact(
                    point_count=3,
                    frame_count=3,
                    anchor_index=0,
                    anchor_phase="preparing",
                    origin_x=0.2,
                    origin_y=0.5,
                    normalized_by_hand_size=True,
                    frames=[
                        GestureSequenceFrame(
                            t=0.0, x=0.0, y=0.0, active_phase="preparing"
                        ),
                        GestureSequenceFrame(
                            t=0.1,
                            x=0.75,
                            y=0.0,
                            velocity_x=7.5,
                            velocity_y=0.0,
                            hand_openness=0.3,
                            index_extension_ratio=1.2,
                            center_distance=0.14,
                            active_phase="committing",
                        ),
                        GestureSequenceFrame(
                            t=0.2,
                            x=1.5,
                            y=0.0,
                            velocity_x=7.5,
                            velocity_y=0.0,
                            hand_openness=0.3,
                            index_extension_ratio=1.2,
                            center_distance=0.14,
                            active_phase="releasing",
                        ),
                    ],
                ),
            )
        ],
    )


def build_push_landmarks():
    return {
        "wrist": (0.5, 0.72),
        "index_mcp": (0.5, 0.56),
        "index_tip": (0.5, 0.28),
        "middle_mcp": (0.56, 0.58),
        "middle_tip": (0.56, 0.64),
        "ring_mcp": (0.61, 0.6),
        "ring_tip": (0.61, 0.67),
        "pinky_mcp": (0.66, 0.62),
        "pinky_tip": (0.66, 0.69),
    }


def make_push_observation(
    index_tip_depth: float, captured_at: float
) -> GestureObservation:
    landmarks = build_push_landmarks()
    landmark_depths = {
        "index_mcp": 0.0,
        "index_tip": index_tip_depth,
        "middle_mcp": 0.0,
        "middle_tip": 0.02,
        "ring_mcp": 0.0,
        "ring_tip": 0.02,
        "pinky_mcp": 0.0,
        "pinky_tip": 0.02,
    }
    return GestureObservation(
        point=(0.5, 0.5),
        hand="right",
        landmarks=landmarks,
        landmark_depths=landmark_depths,
        hand_size=0.16,
        tracking_source="palm_center",
        captured_at=captured_at,
    )


def make_circle_pose_features(
    *,
    hand_openness: float,
    center_distance: float = 0.05,
    index_extension_ratio: float = 0.82,
    hand: str = "right",
) -> HandPoseFeatures:
    open_commit = hand_openness >= 0.55

    def finger_state(
        name: str,
        *,
        extended: float,
        curled: float,
        label: str,
    ) -> FingerState:
        return FingerState(
            name=name,
            extended_score=extended,
            curled_score=curled,
            spread_score=0.2 if open_commit else 0.05,
            tip_depth_relative=0.0,
            tip_to_palm_distance=0.06,
            label=label,
        )

    return HandPoseFeatures(
        hand=hand,
        point=(0.5, 0.5),
        palm_center=(0.5, 0.5),
        hand_size=0.16,
        palm_span=0.11,
        center_distance=center_distance,
        hand_openness=hand_openness,
        index_extension_ratio=index_extension_ratio,
        push_depth=0.0,
        finger_states={
            "thumb": finger_state(
                "thumb",
                extended=0.85 if open_commit else 0.35,
                curled=0.05 if open_commit else 0.35,
                label="extended" if open_commit else "neutral",
            ),
            "index": finger_state(
                "index",
                extended=0.8 if open_commit else 0.2,
                curled=0.05 if open_commit else 0.5,
                label="extended" if open_commit else "curled",
            ),
            "middle": finger_state(
                "middle",
                extended=0.7 if hand_openness > 0.8 else 0.1,
                curled=0.05 if hand_openness > 0.8 else 0.6,
                label="extended" if hand_openness > 0.8 else "curled",
            ),
            "ring": finger_state(
                "ring",
                extended=0.65 if hand_openness > 0.8 else 0.1,
                curled=0.05 if hand_openness > 0.8 else 0.6,
                label="extended" if hand_openness > 0.8 else "curled",
            ),
            "pinky": finger_state(
                "pinky",
                extended=0.6 if hand_openness > 0.8 else 0.1,
                curled=0.05 if hand_openness > 0.8 else 0.6,
                label="extended" if hand_openness > 0.8 else "curled",
            ),
        },
        tracking_source="palm_center",
    )


def make_pinch_pose_features(
    *,
    hand_openness: float = 0.64,
    thumb_extended: float = 0.72,
    index_extended: float = 0.84,
    support_curled_scores: tuple[float, float, float] = (0.18, 0.16, 0.14),
) -> HandPoseFeatures:
    support_labels = [
        "curled" if score >= 0.6 else "neutral" if score >= 0.35 else "extended"
        for score in support_curled_scores
    ]

    def finger_state(
        name: str,
        *,
        extended: float,
        curled: float,
        label: str,
        spread: float = 0.08,
    ) -> FingerState:
        return FingerState(
            name=name,
            extended_score=extended,
            curled_score=curled,
            spread_score=spread,
            tip_depth_relative=0.0,
            tip_to_palm_distance=0.06,
            label=label,
        )

    return HandPoseFeatures(
        hand="right",
        point=(0.5, 0.5),
        palm_center=(0.5, 0.5),
        hand_size=0.16,
        palm_span=0.11,
        center_distance=0.04,
        hand_openness=hand_openness,
        index_extension_ratio=1.08,
        push_depth=0.0,
        finger_states={
            "thumb": finger_state(
                "thumb",
                extended=thumb_extended,
                curled=max(0.0, 1.0 - thumb_extended),
                label="extended" if thumb_extended >= 0.6 else "neutral",
            ),
            "index": finger_state(
                "index",
                extended=index_extended,
                curled=max(0.0, 1.0 - index_extended),
                label="extended" if index_extended >= 0.6 else "neutral",
            ),
            "middle": finger_state(
                "middle",
                extended=0.48,
                curled=support_curled_scores[0],
                label=support_labels[0],
            ),
            "ring": finger_state(
                "ring",
                extended=0.44,
                curled=support_curled_scores[1],
                label=support_labels[1],
            ),
            "pinky": finger_state(
                "pinky",
                extended=0.4,
                curled=support_curled_scores[2],
                label=support_labels[2],
            ),
        },
        tracking_source="palm_center",
    )


def test_extract_hand_pose_features_builds_finger_scores_for_push_like_pose():
    observation = make_push_observation(
        index_tip_depth=-0.16, captured_at=time.monotonic()
    )

    pose = extract_hand_pose_features(observation)

    assert pose is not None
    assert pose.push_depth == pytest.approx(0.16)
    assert pose.center_distance == pytest.approx(0.0)
    assert pose.index_extension_ratio > 1.4
    assert pose.finger_states["index"].label == "extended"
    assert pose.finger_states["middle"].label == "curled"
    assert pose.finger_states["ring"].label == "curled"
    assert pose.finger_states["pinky"].label == "curled"


def test_extract_hand_pose_features_normalizes_missing_point_to_palm_center():
    observation = GestureObservation(
        point=None,
        hand="right",
        landmarks=build_push_landmarks(),
        landmark_depths={"index_mcp": 0.0, "index_tip": 0.12},
        hand_size=0.16,
        tracking_source="palm_center",
    )

    pose = extract_hand_pose_features(observation)

    assert pose is not None
    assert pose.point == pytest.approx((0.566, 0.616), abs=0.01)
    assert pose.center_distance > 0.0


def test_compute_push_pose_snapshot_accepts_depth_assisted_pose_for_off_center_camera_angle(
    monkeypatch,
):
    observation = make_push_observation(index_tip_depth=-0.03, captured_at=0.12)
    observation.point = (0.89, 0.5)

    monkeypatch.setattr(
        "services.gesture.push_runtime.extract_hand_pose_features",
        lambda _: HandPoseFeatures(
            hand="right",
            point=observation.point,
            palm_center=(0.5, 0.5),
            hand_size=0.16,
            palm_span=0.11,
            center_distance=0.39,
            hand_openness=0.18,
            index_extension_ratio=0.74,
            push_depth=0.03,
            finger_states={},
            tracking_source="palm_center",
        ),
    )

    snapshot = compute_push_pose_snapshot(
        observation,
        center_tolerance=0.35,
        extension_ratio=1.05,
        push_depth_threshold=0.024,
    )

    assert snapshot.pose_valid is True


def test_detect_push_gesture_respects_configured_short_click_min_duration():
    observations = [
        make_push_observation(index_tip_depth=-0.15, captured_at=0.00),
        make_push_observation(index_tip_depth=-0.14, captured_at=0.14),
        make_push_observation(index_tip_depth=-0.01, captured_at=0.24),
    ]

    def run_sequence(config: GestureConfig):
        state = None
        detection = None
        for observation in observations:
            state, detection = detect_push_gesture(
                state=state,
                observation=observation,
                observed_at=observation.captured_at,
                config=config,
            )
        return detection

    default_detection = run_sequence(GestureConfig())
    strict_detection = run_sequence(GestureConfig(push_short_click_min_duration=0.25))

    assert default_detection is not None
    assert default_detection.gesture == "push_click_short"
    assert strict_detection is None


def test_extract_temporal_gesture_window_respects_configured_prepare_threshold():
    default_window = extract_temporal_gesture_window(
        trajectory=[(0.5, 0.5), (0.55, 0.5), (0.6, 0.5)],
        trajectory_timestamps=[0.0, 0.06, 0.12],
        hand_size=0.16,
    )

    tuned_window = extract_temporal_gesture_window(
        trajectory=[(0.5, 0.5), (0.55, 0.5), (0.6, 0.5)],
        trajectory_timestamps=[0.0, 0.06, 0.12],
        hand_size=0.16,
        phase_preparing_max_seconds=0.05,
    )

    assert default_window.phase == "preparing"
    assert tuned_window.phase == "committing"


def test_analyze_runtime_gesture_resolves_push_spec_with_phase_and_primitives():
    observation = make_push_observation(index_tip_depth=-0.16, captured_at=0.28)
    pose = extract_hand_pose_features(observation)
    detection = GestureDetectionResult(
        gesture="push_click_short",
        confidence=0.81,
        tracking_source="index_push",
        metrics={"duration_seconds": 0.18, "frame_count": 4},
    )

    analysis = analyze_runtime_gesture(
        candidates=[detection],
        trajectory=[(0.5, 0.5), (0.5, 0.49), (0.5, 0.5), (0.5, 0.51)],
        trajectory_timestamps=[0.0, 0.08, 0.16, 0.22],
        hand_count=1,
        pose_features=pose,
        hand_size=0.16,
        swipe_threshold=0.08,
        circle_sweep_min=4.2,
        circle_cv_max=0.45,
        center_tolerance=0.2,
        push_depth_threshold=0.09,
        zoom_delta_threshold=0.12,
    )

    assert analysis.detection is not None
    assert analysis.detection.gesture == "push_click_short"
    assert analysis.active_phase in {"holding", "releasing", "committing"}
    assert analysis.spec_id == "gesture.push_click_short.v1"
    assert analysis.primitive_hits["push_forward"] >= 1.0
    assert analysis.primitive_hits["index_primary"] >= 0.6


def test_analyze_runtime_gesture_accepts_valid_push_when_slightly_off_center():
    observation = make_push_observation(index_tip_depth=-0.16, captured_at=0.28)
    observation.point = (0.62, 0.5)
    pose = extract_hand_pose_features(observation)
    assert pose is not None
    detection = GestureDetectionResult(
        gesture="push_click_short",
        confidence=0.81,
        tracking_source="index_push",
        metrics={
            "duration_seconds": 0.18,
            "frame_count": 4,
            "center_distance": pose.center_distance,
            "forward_depth": pose.push_depth,
        },
    )

    analysis = analyze_runtime_gesture(
        candidates=[detection],
        trajectory=[(0.62, 0.5), (0.62, 0.49), (0.62, 0.5), (0.62, 0.51)],
        trajectory_timestamps=[0.0, 0.08, 0.16, 0.22],
        hand_count=1,
        pose_features=pose,
        hand_size=0.16,
        swipe_threshold=0.08,
        circle_sweep_min=4.2,
        circle_cv_max=0.45,
        center_tolerance=0.2,
        push_depth_threshold=0.09,
        zoom_delta_threshold=0.12,
    )

    assert analysis.detection is not None
    assert analysis.detection.gesture == "push_click_short"
    assert analysis.primitive_hits["hand_centered"] >= 0.6


def test_analyze_runtime_gesture_rejects_push_when_configured_push_forward_threshold_is_stricter():
    observation = make_push_observation(index_tip_depth=-0.16, captured_at=0.28)
    pose = extract_hand_pose_features(observation)
    assert pose is not None
    detection = GestureDetectionResult(
        gesture="push_click_short",
        confidence=0.81,
        tracking_source="index_push",
        metrics={
            "duration_seconds": 0.18,
            "frame_count": 4,
            "forward_depth": pose.push_depth,
            "center_distance": pose.center_distance,
        },
    )

    analysis = analyze_runtime_gesture(
        candidates=[detection],
        trajectory=[(0.5, 0.5), (0.5, 0.49), (0.5, 0.5), (0.5, 0.51)],
        trajectory_timestamps=[0.0, 0.08, 0.16, 0.22],
        hand_count=1,
        pose_features=pose,
        hand_size=0.16,
        swipe_threshold=0.08,
        circle_sweep_min=4.2,
        circle_cv_max=0.45,
        center_tolerance=0.2,
        push_depth_threshold=0.09,
        zoom_delta_threshold=0.12,
        primitive_push_forward_threshold=1.1,
    )

    assert analysis.detection is None
    assert analysis.reject_reason == "push_depth_too_small"


def test_analyze_runtime_gesture_tracking_quality_respects_configured_weights():
    analysis = analyze_runtime_gesture(
        candidates=[],
        trajectory=[(0.5, 0.5), (0.55, 0.5)],
        trajectory_timestamps=[0.0, 0.1],
        hand_count=1,
        pose_features=None,
        hand_size=0.16,
        swipe_threshold=0.08,
        circle_sweep_min=4.2,
        circle_cv_max=0.45,
        center_tolerance=0.2,
        push_depth_threshold=0.09,
        zoom_delta_threshold=0.12,
        resolver_tracking_quality_trajectory_weight=0.2,
        resolver_tracking_quality_pose_weight=0.5,
        resolver_tracking_quality_hand_weight=0.1,
    )

    assert analysis.tracking_quality == pytest.approx(0.3)


def test_build_runtime_gesture_specs_assigns_detector_groups():
    specs = build_runtime_gesture_specs()

    assert specs["swipe_left"].group == "single_hand_motion"
    assert specs["push_click_short"].group == "push"
    assert specs["zoom_in_hands"].group == "two_hand_zoom"


def test_build_detection_context_promotes_two_hand_distance_to_committing_phase():
    context = build_detection_context(
        trajectory=[(0.50, 0.46), (0.50, 0.42), (0.50, 0.37)],
        trajectory_timestamps=[0.0, 0.05, 0.10],
        hand_count=2,
        pose_features=None,
        hand_size=0.16,
        cooldown_active=False,
        distance_window=[(0.0, 0.12), (0.05, 0.22), (0.10, 0.34)],
        swipe_threshold=0.08,
        circle_sweep_min=4.2,
        circle_cv_max=0.45,
        center_tolerance=0.2,
        push_depth_threshold=0.09,
        zoom_delta_threshold=0.12,
        hand_size_reference=settings.GESTURE_HAND_SIZE_REFERENCE,
        phase_hold_max_peak_speed=settings.GESTURE_PHASE_HOLD_MAX_PEAK_SPEED,
        phase_hold_min_stability=settings.GESTURE_PHASE_HOLD_MIN_STABILITY,
        phase_preparing_max_seconds=settings.GESTURE_PHASE_PREPARING_MAX_SECONDS,
        phase_release_max_recent_speed=settings.GESTURE_PHASE_RELEASE_MAX_RECENT_SPEED,
        phase_release_speed_ratio=settings.GESTURE_PHASE_RELEASE_SPEED_RATIO,
        phase_commit_distance_threshold=settings.GESTURE_PHASE_COMMIT_DISTANCE_THRESHOLD,
        primitive_hand_centered_threshold=settings.GESTURE_PRIMITIVE_HAND_CENTERED_THRESHOLD,
        primitive_stable_hold_threshold=settings.GESTURE_PRIMITIVE_STABLE_HOLD_THRESHOLD,
        primitive_index_primary_threshold=settings.GESTURE_PRIMITIVE_INDEX_PRIMARY_THRESHOLD,
        primitive_all_fingers_open_threshold=settings.GESTURE_PRIMITIVE_ALL_FINGERS_OPEN_THRESHOLD,
        primitive_fist_like_threshold=settings.GESTURE_PRIMITIVE_FIST_LIKE_THRESHOLD,
        primitive_push_forward_threshold=settings.GESTURE_PRIMITIVE_PUSH_FORWARD_THRESHOLD,
        primitive_palm_visible_score=settings.GESTURE_PRIMITIVE_PALM_VISIBLE_SCORE,
        primitive_palm_visible_threshold=settings.GESTURE_PRIMITIVE_PALM_VISIBLE_THRESHOLD,
        primitive_swipe_jitter_damping=settings.GESTURE_PRIMITIVE_SWIPE_JITTER_DAMPING,
        primitive_circle_motion_threshold=settings.GESTURE_PRIMITIVE_CIRCLE_MOTION_THRESHOLD,
        primitive_two_hand_threshold=settings.GESTURE_PRIMITIVE_TWO_HAND_THRESHOLD,
        resolver_tracking_quality_trajectory_weight=settings.GESTURE_RESOLVER_TRACKING_QUALITY_TRAJECTORY_WEIGHT,
        resolver_tracking_quality_pose_weight=settings.GESTURE_RESOLVER_TRACKING_QUALITY_POSE_WEIGHT,
        resolver_tracking_quality_hand_weight=settings.GESTURE_RESOLVER_TRACKING_QUALITY_HAND_WEIGHT,
    )

    assert context.temporal_window.phase == "committing"
    assert context.primitives["two_hand_expand"].passed is True


def test_detect_gesture_with_confidence_respects_configured_horizontal_dominance_ratio():
    trajectory = [
        (0.20, 0.20),
        (0.28, 0.26),
        (0.36, 0.32),
        (0.44, 0.38),
        (0.52, 0.44),
        (0.60, 0.50),
    ]

    default_detection = detect_gesture_with_confidence(
        trajectory=trajectory,
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        min_detection_points=settings.GESTURE_MIN_DETECTION_POINTS,
        swipe_min_span=settings.GESTURE_SWIPE_MIN_SPAN,
        circle_min_radius=settings.GESTURE_CIRCLE_MIN_RADIUS,
        min_confidence=0.1,
    )
    tuned_detection = detect_gesture_with_confidence(
        trajectory=trajectory,
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        min_detection_points=settings.GESTURE_MIN_DETECTION_POINTS,
        swipe_min_span=settings.GESTURE_SWIPE_MIN_SPAN,
        circle_min_radius=settings.GESTURE_CIRCLE_MIN_RADIUS,
        min_confidence=0.1,
        horizontal_dominance_ratio=1.1,
    )

    assert default_detection is None
    assert tuned_detection is not None
    assert tuned_detection.gesture == "swipe_left"


def test_analyze_runtime_gesture_rejects_swipe_on_phase_mismatch():
    detection = GestureDetectionResult(
        gesture="swipe_left",
        confidence=0.84,
        tracking_source="palm_center",
    )

    analysis = analyze_runtime_gesture(
        candidates=[detection],
        trajectory=[(0.5, 0.5), (0.505, 0.5), (0.507, 0.5), (0.508, 0.5)],
        trajectory_timestamps=[0.0, 0.2, 0.4, 0.6],
        hand_count=1,
        pose_features=None,
        hand_size=0.16,
        swipe_threshold=0.08,
        circle_sweep_min=4.2,
        circle_cv_max=0.45,
        center_tolerance=0.2,
        push_depth_threshold=0.09,
        zoom_delta_threshold=0.12,
    )

    assert analysis.detection is None
    assert analysis.reject_reason == "phase_mismatch"
    assert analysis.candidate_scores["swipe_left"] < 0.6


def make_two_hand_observation(
    left_point: tuple[float, float],
    right_point: tuple[float, float],
    captured_at: float,
) -> GestureObservation:
    hands = [
        TrackedHandObservation(
            point=left_point, hand="left", hand_size=0.16, tracking_source="palm_center"
        ),
        TrackedHandObservation(
            point=right_point,
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
    ]
    return GestureObservation(
        point=(
            (left_point[0] + right_point[0]) / 2,
            (left_point[1] + right_point[1]) / 2,
        ),
        hand="right",
        hand_size=0.16,
        hands=hands,
        tracking_source="palm_center",
        captured_at=captured_at,
    )


def wait_until(predicate, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []
        self._incoming: asyncio.Queue[object] = asyncio.Queue()

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        item = await self._incoming.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def send_json(self, message):
        self.messages.append(message)

    def queue_text(self, message: str):
        self._incoming.put_nowait(message)

    def queue_disconnect(self):
        self._incoming.put_nowait(WebSocketDisconnect())


def test_detect_swipe_right():
    gesture = detect_gesture_from_trajectory(
        trajectory=[
            (0.2, 0.5),
            (0.3, 0.5),
            (0.4, 0.5),
            (0.5, 0.5),
            (0.6, 0.5),
            (0.8, 0.5),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
    )
    assert gesture == "swipe_left"


def test_detect_swipe_left():
    gesture = detect_gesture_from_trajectory(
        trajectory=[
            (0.8, 0.5),
            (0.7, 0.5),
            (0.6, 0.5),
            (0.5, 0.5),
            (0.4, 0.5),
            (0.2, 0.5),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
    )
    assert gesture == "swipe_right"


def test_detect_swipe_down():
    gesture = detect_gesture_from_trajectory(
        trajectory=[
            (0.5, 0.2),
            (0.5, 0.3),
            (0.5, 0.4),
            (0.5, 0.5),
            (0.5, 0.6),
            (0.5, 0.8),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
    )
    assert gesture == "swipe_down"


def test_detect_swipe_up():
    gesture = detect_gesture_from_trajectory(
        trajectory=[
            (0.5, 0.8),
            (0.5, 0.7),
            (0.5, 0.6),
            (0.5, 0.5),
            (0.5, 0.4),
            (0.5, 0.2),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        up_threshold=settings.GESTURE_UP_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
    )
    assert gesture == "swipe_up"


def test_detect_circle():
    angles = [index * (2 * math.pi * 1.3 / 31) for index in range(32)]
    trajectory = [
        (0.5 + 0.08 * math.cos(angle), 0.5 + 0.08 * math.sin(angle)) for angle in angles
    ]
    gesture = detect_gesture_from_trajectory(
        trajectory=trajectory,
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
    )
    assert gesture == "circle"


def test_detect_circle_rejects_narrow_vertical_return_motion():
    gesture = detect_gesture_from_trajectory(
        trajectory=[
            (0.50, 0.18),
            (0.50, 0.30),
            (0.51, 0.44),
            (0.50, 0.58),
            (0.50, 0.44),
            (0.50, 0.29),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        up_threshold=settings.GESTURE_UP_THRESHOLD,
    )

    assert gesture is None


def test_detect_swipe_up_rejects_wide_off_axis_motion():
    gesture = detect_gesture_from_trajectory(
        trajectory=[
            (0.30, 0.75),
            (0.36, 0.69),
            (0.43, 0.63),
            (0.50, 0.57),
            (0.57, 0.51),
            (0.65, 0.45),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        up_threshold=settings.GESTURE_UP_THRESHOLD,
    )

    assert gesture is None


def test_detect_short_trajectory_returns_none():
    gesture = detect_gesture_from_trajectory(
        trajectory=[(0.5, 0.5), (0.51, 0.51)],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
    )
    assert gesture is None


def test_extract_gesture_features_returns_expected_metrics():
    features = extract_gesture_features(
        trajectory=[
            (0.2, 0.5),
            (0.3, 0.5),
            (0.4, 0.5),
            (0.5, 0.5),
            (0.6, 0.5),
            (0.8, 0.5),
        ],
        min_detection_points=6,
    )

    assert features is not None
    assert features.dx_total == pytest.approx(0.6)
    assert features.dy_total == pytest.approx(0.0)
    assert features.span_x == pytest.approx(0.6)


def test_detect_gesture_candidates_prefers_strong_horizontal_swipe():
    features = extract_gesture_features(
        trajectory=[
            (0.2, 0.5),
            (0.3, 0.5),
            (0.4, 0.5),
            (0.5, 0.5),
            (0.6, 0.5),
            (0.8, 0.5),
        ],
        min_detection_points=6,
    )
    assert features is not None

    candidates = detect_gesture_candidates(
        features=features,
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        swipe_min_span=settings.GESTURE_SWIPE_MIN_SPAN,
        circle_min_radius=settings.GESTURE_CIRCLE_MIN_RADIUS,
    )
    best = select_best_gesture_candidate(candidates, min_confidence=0.0)

    assert best is not None
    assert best.gesture == "swipe_left"
    assert best.confidence > 0.9


def test_detect_gesture_with_confidence_returns_metadata():
    detection = detect_gesture_with_confidence(
        trajectory=[
            (0.2, 0.5),
            (0.3, 0.5),
            (0.4, 0.5),
            (0.5, 0.5),
            (0.6, 0.5),
            (0.8, 0.5),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        min_detection_points=settings.GESTURE_MIN_DETECTION_POINTS,
        swipe_min_span=settings.GESTURE_SWIPE_MIN_SPAN,
        circle_min_radius=settings.GESTURE_CIRCLE_MIN_RADIUS,
        min_confidence=0.1,
        tracking_source="palm_center",
    )

    assert detection is not None
    assert detection.gesture == "swipe_left"
    assert detection.confidence > 0.9
    assert detection.tracking_source == "palm_center"


def test_compute_hand_size_scale_clamps_to_configured_bounds():
    assert compute_hand_size_scale(0.08, 0.16, 0.7, 1.6) == pytest.approx(0.7)
    assert compute_hand_size_scale(0.4, 0.16, 0.7, 1.6) == pytest.approx(1.6)


def test_hand_size_normalization_recovers_small_far_hand_swipe():
    detection = detect_gesture_with_confidence(
        trajectory=[
            (0.20, 0.5),
            (0.22, 0.5),
            (0.24, 0.5),
            (0.26, 0.5),
            (0.28, 0.5),
            (0.30, 0.5),
        ],
        swipe_threshold=0.12,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        min_detection_points=6,
        swipe_min_span=0.06,
        circle_min_radius=settings.GESTURE_CIRCLE_MIN_RADIUS,
        min_confidence=0.2,
        hand_size=0.08,
        hand_size_reference=0.16,
        hand_size_scale_min=0.5,
        hand_size_scale_max=1.8,
    )

    assert detection is not None
    assert detection.gesture == "swipe_left"


def test_small_far_hand_swipe_without_hand_size_normalization_is_rejected():
    detection = detect_gesture_with_confidence(
        trajectory=[
            (0.20, 0.5),
            (0.22, 0.5),
            (0.24, 0.5),
            (0.26, 0.5),
            (0.28, 0.5),
            (0.30, 0.5),
        ],
        swipe_threshold=0.12,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        min_detection_points=6,
        swipe_min_span=0.06,
        circle_min_radius=settings.GESTURE_CIRCLE_MIN_RADIUS,
        min_confidence=0.2,
        hand_size=None,
    )

    assert detection is None


def test_build_hand_landmark_map_and_tracking_point():
    landmarks = build_hand_landmark_map(FakeHandLandmarks())
    tracking_point = compute_hand_tracking_point(landmarks)

    assert tracking_point is not None
    assert tracking_point[0] == pytest.approx(0.5)
    assert tracking_point[1] == pytest.approx(0.48)


def test_estimate_hand_size_uses_palm_width():
    landmarks = build_hand_landmark_map(FakeHandLandmarks())
    hand_size = estimate_hand_size(landmarks)

    assert hand_size is not None
    assert hand_size == pytest.approx(0.1581, rel=1e-3)


def test_hand_landmark_map_includes_full_thumb_and_finger_chains():
    landmarks = build_hand_landmark_map(FakeHandLandmarks())

    assert {"thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip"}.issubset(
        HAND_LANDMARK_NAMES
    )
    assert {"index_pip", "index_dip", "middle_pip", "pinky_dip"}.issubset(
        HAND_LANDMARK_NAMES
    )
    assert "thumb_ip" in landmarks
    assert "index_dip" in landmarks


def test_compute_pinch_contact_metrics_prefers_thumb_index_contact_distance():
    landmarks = {
        "wrist": (0.50, 0.70),
        "thumb_cmc": (0.45, 0.62),
        "thumb_mcp": (0.42, 0.55),
        "thumb_ip": (0.40, 0.49),
        "thumb_tip": (0.42, 0.43),
        "index_mcp": (0.50, 0.52),
        "index_pip": (0.49, 0.45),
        "index_dip": (0.46, 0.42),
        "index_tip": (0.43, 0.43),
        "middle_mcp": (0.56, 0.54),
        "ring_mcp": (0.61, 0.56),
        "pinky_mcp": (0.66, 0.58),
    }
    metrics = compute_pinch_contact_metrics(
        GestureObservation(
            point=(0.5, 0.5),
            landmarks=landmarks,
            hand_size=0.16,
        )
    )

    assert metrics is not None
    assert metrics.distance == pytest.approx(0.0625, rel=1e-2)
    assert metrics.anchor == pytest.approx((0.425, 0.43), rel=1e-3)


def test_compute_pinch_contact_metrics_handles_short_tip_skeleton_with_segment_fallback():
    landmarks = {
        "wrist": (0.50, 0.70),
        "thumb_cmc": (0.45, 0.62),
        "thumb_mcp": (0.42, 0.55),
        "thumb_ip": (0.39, 0.48),
        "thumb_tip": (0.50, 0.41),
        "index_mcp": (0.50, 0.52),
        "index_pip": (0.50, 0.47),
        "index_dip": (0.48, 0.44),
        "index_tip": (0.44, 0.42),
        "middle_mcp": (0.56, 0.54),
        "ring_mcp": (0.61, 0.56),
        "pinky_mcp": (0.66, 0.58),
    }
    metrics = compute_pinch_contact_metrics(
        GestureObservation(point=(0.5, 0.5), landmarks=landmarks, hand_size=0.16)
    )

    assert metrics is not None
    assert metrics.contact_pair != ("thumb_tip", "index_tip")
    assert metrics.distance < (metrics.tip_distance or 1.0)


def test_detect_noise_returns_none():
    gesture = detect_gesture_from_trajectory(
        trajectory=[
            (0.5, 0.5),
            (0.503, 0.497),
            (0.498, 0.502),
            (0.501, 0.499),
            (0.502, 0.501),
            (0.499, 0.498),
        ],
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
    )
    assert gesture is None


def test_start_and_stop_session():
    hub = CapturingRealtimeHub()
    adapter = SequenceAdapter(observations=[GestureObservation(point=None)])
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    started = service.start(camera_index=2)
    assert started["running"] is True
    assert started["camera_index"] == 2

    stopped = service.stop()
    assert stopped["running"] is False
    assert stopped["camera_index"] is None
    assert adapter.closed is True


def test_service_uses_adapter_resolved_camera_index_on_start():
    service = GestureService(
        adapter_factory=lambda: ResolvedIndexAdapter(
            observations=[GestureObservation(point=None)]
        ),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    started = service.start(camera_index=2)

    assert started["camera_index"] == 3
    service.stop()


def test_service_uses_command_profile_camera_preference_when_no_runtime_preference_exists():
    class CommandProfileGestureRepository(StaticGestureConfigRepository):
        def get_active_command_profile(self):
            return type(
                "CommandProfileStub",
                (),
                {
                    "device_preferences": type(
                        "PreferencesStub",
                        (),
                        {"gesture_camera_index": 5},
                    )(),
                },
            )()

    service = GestureService(
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: CommandProfileGestureRepository(),
    )

    assert service.get_preferred_camera_index() == 5


def test_unavailable_adapter_raises_service_error():
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(available=False),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    with pytest.raises(GestureServiceError) as exc_info:
        service.start(camera_index=0)

    assert exc_info.value.status_code == 503


def test_service_reports_last_error_after_adapter_failure():
    adapter = FailingAdapter(observations=[])
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    started = service.start(camera_index=0)
    assert started["running"] is True

    assert wait_until(lambda: service.get_status()["running"] is False)
    assert service.get_status()["last_error"] == "camera read failed"
    assert adapter.closed is True
    assert service.get_status()["camera_index"] is None


def test_advance_pending_gesture_respects_configured_finalize_delay():
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=[]),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(
            GestureConfig(pending_finalize_seconds=0.0)
        ),
    )
    service.reload_config()
    advance_pending_gesture = getattr(service, "_advance_pending_gesture")
    detection = GestureDetectionResult(
        gesture="swipe_left",
        confidence=0.84,
        tracking_source="palm_center",
    )
    analysis = SimpleNamespace(detection=detection, active_phase="releasing")

    assert advance_pending_gesture(analysis=analysis, observed_at=1.0) is None

    finalized = advance_pending_gesture(analysis=analysis, observed_at=1.0)

    assert finalized is not None
    assert finalized.gesture == "swipe_left"


def test_advance_pending_gesture_fires_pinch_edges_immediately():
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=[]),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )
    service.reload_config()
    advance_pending_gesture = getattr(service, "_advance_pending_gesture")
    detection = GestureDetectionResult(
        gesture="pinch_close",
        confidence=0.92,
        tracking_source="pinch_state",
    )
    analysis = SimpleNamespace(detection=detection, active_phase="holding")

    finalized = advance_pending_gesture(analysis=analysis, observed_at=1.0)

    assert finalized is detection
    assert getattr(service, "_pending_gesture") is None


def test_advance_pending_gesture_fires_circle_commit_immediately():
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=[]),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )
    service.reload_config()
    advance_pending_gesture = getattr(service, "_advance_pending_gesture")
    detection = GestureDetectionResult(
        gesture="circle",
        confidence=0.95,
        tracking_source="palm_center",
        metrics={"finalize_immediately": True},
    )
    analysis = SimpleNamespace(detection=detection, active_phase="releasing")

    finalized = advance_pending_gesture(analysis=analysis, observed_at=1.0)

    assert finalized is detection
    assert getattr(service, "_pending_gesture") is None


def test_dev_capture_metadata_distinguishes_pending_and_published_detections():
    build_metadata = getattr(GestureService, "_build_dev_capture_metadata")
    pending_detection = GestureDetectionResult(
        gesture="pinch_close",
        confidence=0.92,
        tracking_source="pinch_state",
    )
    analysis = SimpleNamespace(
        active_phase="holding",
        tracking_quality=0.8,
        candidate_scores={"pinch_close": 0.92},
        primitive_hits={},
        reject_reason=None,
        dominant_hand_pose="pinching",
        detection=pending_detection,
    )

    suppressed = build_metadata(
        active_capture=SimpleNamespace(started_at=1.0),
        frame_index=1,
        observation=GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="pinch_state",
            captured_at=1.1,
        ),
        pose_features=None,
        analysis=analysis,
        detection=pending_detection,
        published_detection=None,
        publish_suppressed_reason="cooldown",
        observed_at=1.1,
        pinch_state=None,
        circle_state=None,
        image_file=None,
        raw_image_file=None,
    )

    assert suppressed["analysis_detection"]["gesture"] == "pinch_close"
    assert suppressed["pending_detection"]["gesture"] == "pinch_close"
    assert suppressed["published_detection"] is None
    assert suppressed["fired_detection"] is None
    assert suppressed["publish_suppressed_reason"] == "cooldown"

    published = build_metadata(
        active_capture=SimpleNamespace(started_at=1.0),
        frame_index=2,
        observation=GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="pinch_state",
            captured_at=1.2,
        ),
        pose_features=None,
        analysis=analysis,
        detection=pending_detection,
        published_detection=pending_detection,
        publish_suppressed_reason=None,
        observed_at=1.2,
        pinch_state=None,
        circle_state=None,
        image_file=None,
        raw_image_file=None,
    )

    assert published["published_detection"]["gesture"] == "pinch_close"
    assert published["fired_detection"]["gesture"] == "pinch_close"
    assert published["publish_suppressed_reason"] is None


def test_append_active_calibration_capture_frame_accepts_normalized_landmark_dicts():
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=[]),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.begin_calibration_take_capture(
        session_id="session-1",
        take_id="take-1",
        target_id="swipe_right",
    )

    observation = make_push_observation(
        index_tip_depth=-0.16, captured_at=time.monotonic()
    )

    service._append_active_calibration_capture_frame(
        observation=observation,
        analysis=SimpleNamespace(
            active_phase="holding", dominant_hand_pose="pointing", detection=None
        ),
        detection=None,
        observed_at=observation.captured_at or time.monotonic(),
    )

    assert service._active_calibration_capture is not None
    assert len(service._active_calibration_capture.frames) == 1


def test_stop_calibration_take_capture_builds_local_sequence_artifact():
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=[]),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.begin_calibration_take_capture(
        session_id="session-1",
        take_id="take-1",
        target_id="swipe_right",
        trimmed_tail_ms=0,
    )

    frames = [
        GestureObservation(
            point=(0.50, 0.50),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.0,
        ),
        GestureObservation(
            point=(0.62, 0.50),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.1,
        ),
        GestureObservation(
            point=(0.74, 0.50),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.2,
        ),
    ]

    for index, observation in enumerate(frames):
        service._append_active_calibration_capture_frame(
            observation=observation,
            analysis=SimpleNamespace(
                active_phase="preparing" if index == 0 else "committing",
                dominant_hand_pose="open_palm",
                detection=None,
            ),
            detection=None,
            observed_at=observation.captured_at or float(index) * 0.1,
        )

    sample, advisory = service.stop_calibration_take_capture(
        session_id="session-1",
        take_id="take-1",
        target_id="swipe_right",
    )

    assert advisory is None
    assert sample.gesture_payload is not None
    assert sample.gesture_payload.sequence is not None
    assert sample.gesture_payload.sequence.normalized_by_hand_size is True
    assert sample.gesture_payload.sequence.frames[0].x == pytest.approx(0.0)
    assert sample.gesture_payload.sequence.frames[1].x == pytest.approx(0.75)
    assert sample.gesture_payload.sequence.frames[2].velocity_x == pytest.approx(7.5)


def test_runtime_sequence_artifact_reanchors_at_first_stable_phase():
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=[]),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    artifact = service._build_sequence_artifact_from_runtime_window(
        trajectory=[(0.18, 0.50), (0.30, 0.50), (0.42, 0.50), (0.54, 0.50)],
        trajectory_timestamps=[0.00, 0.05, 0.10, 0.15],
        hand_size=0.12,
        active_phases=["idle", "preparing", "committing", "releasing"],
    )

    assert artifact is not None
    assert artifact.anchor_index == 1
    assert artifact.anchor_phase == "preparing"
    assert artifact.origin_x == pytest.approx(0.30)
    assert artifact.point_count == 3
    assert artifact.frames[0].x == pytest.approx(0.0)
    assert artifact.frames[1].x == pytest.approx(1.0)


def test_service_retries_transient_adapter_failure_and_recovers():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(
            point=(0.2, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.3, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.4, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.6, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.8, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
    ]
    adapter = FlakyAdapter(observations=observations, failures_before_success=1)
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    assert adapter.failures_seen == 1
    assert (
        filter_messages(hub.messages, "GestureDetected")[0]["payload"]["gesture"]
        == "swipe_left"
    )


def test_stop_sets_error_when_thread_does_not_finish_in_time():
    class StuckThread:
        def __init__(self):
            self.join_timeout = None

        def join(self, timeout=None):
            self.join_timeout = timeout

        def is_alive(self):
            return True

    adapter = SequenceAdapter()
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service._thread = StuckThread()
    service._adapter = adapter
    service.running = True

    stopped = service.stop()

    assert stopped["running"] is False
    assert (
        stopped["last_error"]
        == "Gesten-Thread konnte nicht rechtzeitig beendet werden."
    )


def test_reload_config_safe_during_detection():
    hub = CapturingRealtimeHub()
    repository = MutableGestureConfigRepository(
        GestureConfig(
            swipe_threshold=0.3,
            min_confidence=0.2,
            hand_size_reference=0.16,
            hand_size_scale_min=0.5,
            hand_size_scale_max=1.8,
        )
    )
    observations = [
        GestureObservation(point=None),
        GestureObservation(point=None),
        GestureObservation(
            point=(0.20, 0.5),
            hand="right",
            hand_size=0.08,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.22, 0.5),
            hand="right",
            hand_size=0.08,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.24, 0.5),
            hand="right",
            hand_size=0.08,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.26, 0.5),
            hand="right",
            hand_size=0.08,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.28, 0.5),
            hand="right",
            hand_size=0.08,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.30, 0.5),
            hand="right",
            hand_size=0.08,
            tracking_source="palm_center",
        ),
    ]
    adapter = TimedObservationAdapter(observations=observations, event_after=2)
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    service.start()
    repository.set_config(
        GestureConfig(
            swipe_threshold=0.12,
            min_confidence=0.2,
            hand_size_reference=0.16,
            hand_size_scale_min=0.5,
            hand_size_scale_max=1.8,
        )
    )
    service.reload_config()

    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    status = service.get_status()
    service.stop()

    assert status["last_gesture"] == "swipe_left"


def test_service_instances_keep_separate_configs():
    left_service = GestureService(
        adapter_factory=lambda: SequenceAdapter(),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(
            GestureConfig(swipe_threshold=0.11)
        ),
    )
    right_service = GestureService(
        adapter_factory=lambda: SequenceAdapter(),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(
            GestureConfig(swipe_threshold=0.25)
        ),
    )

    left_service.reload_config()
    right_service.reload_config()

    assert left_service._active_config.swipe_threshold == pytest.approx(0.11)
    assert right_service._active_config.swipe_threshold == pytest.approx(0.25)


def test_service_detects_and_exposes_confidence_metadata():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(
            point=(0.2, 0.5), hand="right", tracking_source="palm_center"
        ),
        GestureObservation(
            point=(0.3, 0.5), hand="right", tracking_source="palm_center"
        ),
        GestureObservation(
            point=(0.4, 0.5), hand="right", tracking_source="palm_center"
        ),
        GestureObservation(
            point=(0.5, 0.5), hand="right", tracking_source="palm_center"
        ),
        GestureObservation(
            point=(0.6, 0.5), hand="right", tracking_source="palm_center"
        ),
        GestureObservation(
            point=(0.8, 0.5), hand="right", tracking_source="palm_center"
        ),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    status = service.get_status()
    service.stop()

    assert status["last_gesture"] == "swipe_left"
    assert status["last_confidence"] is not None
    assert status["last_confidence"] > 0.9
    assert status["last_tracking_source"] == "palm_center"


def test_cooldown_prevents_spam_and_emits_event():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(
            point=(0.2, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.3, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.4, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.6, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.8, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.2, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.3, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.4, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.6, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.8, 0.5),
            hand="right",
            preview_bytes=b"frame",
            tracking_source="palm_center",
        ),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_messages = filter_messages(hub.messages, "GestureDetected")
    action_messages = filter_messages(hub.messages, "UIActionRequested")
    assert len(gesture_messages) == 1
    assert len(action_messages) == 1
    assert gesture_messages[0]["payload"]["confidence"] is not None
    assert gesture_messages[0]["payload"]["tracking_source"] == "palm_center"
    assert action_messages[0]["payload"]["action"] == "move_focus_left"
    assert service.get_frame() is not None


def test_service_publishes_ui_action_requested_event_for_swipe():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(
            point=(0.2, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.3, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.4, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.6, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        GestureObservation(
            point=(0.8, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
    ]
    repository = StaticGestureConfigRepository(
        input_action_config=InputActionConfig(
            mappings=[
                InputActionMapping(
                    input_source="gesture",
                    raw_input="swipe_left",
                    action="move_focus_left",
                )
            ]
        )
    )
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "UIActionRequested")) >= 1
    )
    service.stop()

    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert action_message["payload"]["raw_input"] == "swipe_left"
    assert action_message["payload"]["action"] == "move_focus_left"


def test_service_exposes_sequence_shadow_diagnostics_without_changing_action():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(
            point=(0.2, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.00,
        ),
        GestureObservation(
            point=(0.3, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.05,
        ),
        GestureObservation(
            point=(0.4, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.10,
        ),
        GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.15,
        ),
        GestureObservation(
            point=(0.6, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.20,
        ),
        GestureObservation(
            point=(0.8, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.25,
        ),
    ]
    repository = StaticGestureConfigRepository(
        config=GestureConfig(
            sequence_shadow_mode=True, sequence_matching_enabled=False
        ),
        input_action_config=InputActionConfig(
            mappings=[
                InputActionMapping(
                    input_source="gesture",
                    raw_input="swipe_left",
                    action="move_focus_left",
                )
            ]
        ),
        sequence_profile_set=make_sequence_profile_set("swipe_left"),
    )
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "UIActionRequested")) >= 1
    )
    service.stop()

    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    raw_input_message = filter_messages(hub.messages, "RawInputDetected")[0]
    status = service.get_status()

    assert action_message["payload"]["raw_input"] == "swipe_left"
    assert action_message["payload"]["action"] == "move_focus_left"
    assert (
        raw_input_message["payload"]["metadata"]["sequence_scores"].get(
            "swipe_left", 0.0
        )
        > 0.0
    )
    assert (
        raw_input_message["payload"]["metadata"]["sequence_profile_ids"]["swipe_left"]
        == "swipe_left:primary"
    )
    assert status["sequence_shadow_mode"] is True
    assert status["sequence_matching_enabled"] is False
    assert status["sequence_scores"].get("swipe_left", 0.0) > 0.0
    assert status["sequence_profile_ids"]["swipe_left"] == "swipe_left:primary"


def test_service_gates_ui_actions_while_calibration_is_active():
    hub = CapturingRealtimeHub()
    calibration_runtime = CapturingCalibrationRuntime()
    observations = [
        GestureObservation(
            point=(0.2, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.00,
        ),
        GestureObservation(
            point=(0.3, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.05,
        ),
        GestureObservation(
            point=(0.4, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.10,
        ),
        GestureObservation(
            point=(0.5, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.15,
        ),
        GestureObservation(
            point=(0.6, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.20,
        ),
        GestureObservation(
            point=(0.8, 0.5),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
            captured_at=0.25,
        ),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        calibration_runtime=calibration_runtime,
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    assert filter_messages(hub.messages, "UIActionRequested") == []
    assert len(calibration_runtime.samples) == 1
    assert calibration_runtime.samples[0].target_id == "swipe_left"


def test_service_detects_short_push_click():
    hub = CapturingRealtimeHub()
    observations = [
        make_push_observation(index_tip_depth=-0.15, captured_at=0.00),
        make_push_observation(index_tip_depth=-0.14, captured_at=0.14),
        make_push_observation(index_tip_depth=-0.01, captured_at=0.24),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_short"
    assert action_message["payload"]["action"] == "resize_expand"


def test_service_detects_long_push_click():
    hub = CapturingRealtimeHub()
    observations = [
        make_push_observation(index_tip_depth=-0.15, captured_at=0.00),
        make_push_observation(index_tip_depth=-0.16, captured_at=0.28),
        make_push_observation(index_tip_depth=-0.17, captured_at=0.62),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_long"
    assert action_message["payload"]["action"] == "delete_widget"


def test_service_detects_long_push_click_when_release_crosses_threshold():
    hub = CapturingRealtimeHub()
    observations = [
        make_push_observation(index_tip_depth=-0.15, captured_at=0.00),
        make_push_observation(index_tip_depth=-0.15, captured_at=0.46),
        make_push_observation(index_tip_depth=-0.01, captured_at=0.56),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_long"


def test_service_detects_long_push_click_despite_brief_tracking_gap():
    hub = CapturingRealtimeHub()
    observations = [
        make_push_observation(index_tip_depth=-0.15, captured_at=0.00),
        make_push_observation(index_tip_depth=-0.16, captured_at=0.24),
        GestureObservation(point=None, captured_at=0.36),
        make_push_observation(index_tip_depth=-0.15, captured_at=0.58),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_long"


def test_service_defers_swipe_event_until_motion_finishes():
    hub = CapturingRealtimeHub()
    adapter = PausingSequenceAdapter(
        observations=[
            GestureObservation(
                point=(0.72, 0.5),
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
                captured_at=0.00,
            ),
            GestureObservation(
                point=(0.64, 0.5),
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
                captured_at=0.08,
            ),
            GestureObservation(
                point=(0.56, 0.5),
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
                captured_at=0.16,
            ),
            GestureObservation(
                point=(0.48, 0.5),
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
                captured_at=0.24,
            ),
            GestureObservation(
                point=(0.36, 0.5),
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
                captured_at=0.32,
            ),
        ],
        pause_after_reads=5,
    )
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(adapter.pause_event.is_set)
    assert filter_messages(hub.messages, "GestureDetected") == []

    adapter.resume_event.set()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    assert gesture_message["payload"]["gesture"] == "swipe_right"


def test_service_defers_long_push_until_completion():
    hub = CapturingRealtimeHub()
    adapter = PausingSequenceAdapter(
        observations=[
            make_push_observation(index_tip_depth=-0.15, captured_at=0.00),
            make_push_observation(index_tip_depth=-0.16, captured_at=0.28),
            make_push_observation(index_tip_depth=-0.17, captured_at=0.62),
        ],
        pause_after_reads=3,
    )
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(adapter.pause_event.is_set)
    assert filter_messages(hub.messages, "GestureDetected") == []

    adapter.resume_event.set()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_long"


def test_service_detects_short_push_click_with_left_hand():
    hub = CapturingRealtimeHub()
    observations = [
        make_push_observation(index_tip_depth=-0.15, captured_at=0.00),
        make_push_observation(index_tip_depth=-0.14, captured_at=0.14),
        make_push_observation(index_tip_depth=-0.01, captured_at=0.24),
    ]
    for observation in observations:
        observation.hand = "left"
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_short"
    assert gesture_message["payload"]["hand"] == "left"


def test_service_detects_zoom_in_hands():
    hub = CapturingRealtimeHub()
    observations = [
        make_two_hand_observation((0.44, 0.46), (0.56, 0.46), 0.00),
        make_two_hand_observation((0.39, 0.42), (0.61, 0.42), 0.05),
        make_two_hand_observation((0.33, 0.37), (0.67, 0.37), 0.10),
        make_two_hand_observation((0.26, 0.30), (0.74, 0.30), 0.15),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert gesture_message["payload"]["gesture"] == "zoom_in_hands"
    assert action_message["payload"]["action"] == "resize_expand"


def test_service_detects_zoom_out_hands():
    hub = CapturingRealtimeHub()
    observations = [
        make_two_hand_observation((0.12, 0.20), (0.88, 0.20), 0.00),
        make_two_hand_observation((0.22, 0.28), (0.78, 0.28), 0.05),
        make_two_hand_observation((0.30, 0.35), (0.70, 0.35), 0.10),
        make_two_hand_observation((0.38, 0.42), (0.62, 0.42), 0.15),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(
        lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1
    )
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert gesture_message["payload"]["gesture"] == "zoom_out_hands"
    assert action_message["payload"]["action"] == "resize_shrink"


def test_service_prefers_recent_runtime_motion_window_for_swipes():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    trajectory = [
        (0.5, 0.82),
        (0.5, 0.74),
        (0.5, 0.66),
        (0.5, 0.58),
        (0.72, 0.5),
        (0.64, 0.5),
        (0.56, 0.5),
        (0.48, 0.5),
        (0.40, 0.5),
        (0.28, 0.5),
    ]
    timestamps = [0.00, 0.10, 0.20, 0.30, 0.72, 0.80, 0.88, 0.96, 1.04, 1.12]

    detection = service._detect_runtime_gesture(
        observation=GestureObservation(
            point=trajectory[-1], tracking_source="palm_center"
        ),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is not None
    assert detection.gesture == "swipe_right"


def test_service_runtime_motion_window_keeps_slow_recent_points():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(
            config=GestureConfig(min_detection_points=4)
        ),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    trajectory = [
        (0.50, 0.70),
        (0.50, 0.64),
        (0.50, 0.56),
        (0.50, 0.46),
        (0.50, 0.34),
    ]
    timestamps = [0.00, 0.40, 0.80, 1.20, 1.60]

    recent_window = service._select_runtime_single_hand_trajectory(
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        observed_at=timestamps[-1],
    )

    assert recent_window == trajectory[1:]


def test_service_runtime_motion_window_drops_recent_multi_hand_points():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(
            config=GestureConfig(min_detection_points=4)
        ),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    lifecycle = service._lifecycle
    lifecycle.trajectory = [
        (0.24, 0.50),
        (0.36, 0.50),
        (0.48, 0.50),
        (0.60, 0.50),
        (0.72, 0.50),
    ]
    lifecycle.trajectory_timestamps = [0.00, 0.10, 0.20, 0.30, 0.40]
    lifecycle.hand_size_samples = [0.16] * 5
    lifecycle.hand_count_samples = [1, 1, 1, 2, 2]

    recent_window = service._select_runtime_single_hand_trajectory(
        trajectory=list(lifecycle.trajectory),
        trajectory_timestamps=list(lifecycle.trajectory_timestamps),
        observed_at=0.40,
    )

    assert recent_window == []


def test_service_post_fire_grace_blocks_immediate_reaccumulation():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(
            config=GestureConfig(post_fire_grace_seconds=0.5)
        ),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    service._reset_calibration_motion_window(observed_at=1.0)

    blocked = service._lifecycle.append_point(
        point=(0.50, 0.50),
        observed_at=1.10,
        hand_size=0.16,
        hand_count=1,
        pose_features=None,
        smoothing_alpha=0.6,
        max_points=64,
    )
    allowed = service._lifecycle.append_point(
        point=(0.56, 0.50),
        observed_at=1.60,
        hand_size=0.16,
        hand_count=1,
        pose_features=None,
        smoothing_alpha=0.6,
        max_points=64,
    )

    assert blocked is None
    assert service.trajectory == [(0.56, 0.50)]
    assert allowed == (0.56, 0.50)


def test_service_detect_zoom_gesture_clears_history_on_hand_loss():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    first_observation = make_two_hand_observation((0.44, 0.46), (0.56, 0.46), 0.00)
    second_observation = GestureObservation(
        point=(0.50, 0.46),
        hands=[first_observation.hands[0]],
        captured_at=0.05,
    )

    assert service._detect_zoom_gesture(first_observation, 0.00) is None
    assert service.two_hand_distance_history != []

    assert service._detect_zoom_gesture(second_observation, 0.05) is None
    assert service.two_hand_distance_history == []


def test_service_rejects_upward_centering_motion_before_true_swipe_up():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    trajectory = [
        (0.50, 0.78),
        (0.50, 0.71),
        (0.50, 0.64),
        (0.50, 0.58),
        (0.50, 0.53),
        (0.50, 0.47),
    ]
    timestamps = [0.00, 0.10, 0.20, 0.30, 0.40, 0.50]

    detection = service._detect_runtime_gesture(
        observation=GestureObservation(
            point=trajectory[-1], tracking_source="palm_center"
        ),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is None


def test_service_global_cooldown_blocks_immediate_followup_gesture():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    assert service._cooldown_elapsed("swipe_up") is True
    assert service._cooldown_elapsed("swipe_down") is False


def test_service_allows_circle_immediately_after_swipe_navigation():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    assert service._cooldown_elapsed("swipe_right") is True
    assert service._cooldown_elapsed("circle") is True


def test_detect_pinch_gesture_rejects_fist_like_contact_pose():
    config = GestureConfig()
    pose_features = make_pinch_pose_features(
        hand_openness=0.22,
        thumb_extended=0.34,
        index_extended=0.42,
        support_curled_scores=(0.78, 0.75, 0.73),
    )

    state, detection = detect_pinch_gesture(
        state=PinchGestureState(
            pinch_closed=False,
            spread_window=[],
            last_fire_at=0.0,
            anchor=None,
            raw_distance=None,
            smoothed_distance=None,
            contact_pair=None,
        ),
        pose_features=pose_features,
        observed_at=1.0,
        config=config,
        contact_metrics=PinchContactMetrics(
            distance=0.12,
            anchor=(0.5, 0.5),
            contact_pair=("thumb_tip", "index_tip"),
            tip_distance=0.12,
        ),
    )

    assert detection is None
    assert state.pinch_closed is False


def test_detect_pinch_gesture_accepts_intentional_open_pinch_pose():
    config = GestureConfig()
    pose_features = make_pinch_pose_features()

    state, detection = detect_pinch_gesture(
        state=PinchGestureState(
            pinch_closed=False,
            spread_window=[],
            last_fire_at=0.0,
            anchor=None,
            raw_distance=None,
            smoothed_distance=None,
            contact_pair=None,
        ),
        pose_features=pose_features,
        observed_at=1.0,
        config=config,
        contact_metrics=PinchContactMetrics(
            distance=0.12,
            anchor=(0.5, 0.5),
            contact_pair=("thumb_tip", "index_tip"),
            tip_distance=0.12,
        ),
    )

    assert detection is not None
    assert detection.gesture == "pinch_close"
    assert state.pinch_closed is True


def test_service_suppresses_swipe_when_push_commit_is_active():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    trajectory = [
        (0.50, 0.72),
        (0.50, 0.66),
        (0.50, 0.60),
        (0.50, 0.54),
        (0.50, 0.48),
        (0.50, 0.43),
    ]
    timestamps = [0.00, 0.08, 0.16, 0.24, 0.32, 0.40]

    detection = service._detect_runtime_gesture(
        observation=make_push_observation(
            index_tip_depth=-0.12, captured_at=timestamps[-1]
        ),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is None


def test_service_allows_horizontal_swipe_during_click_pose_arming():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    trajectory = [
        (0.20, 0.50),
        (0.30, 0.50),
        (0.40, 0.50),
        (0.50, 0.50),
        (0.60, 0.50),
        (0.80, 0.50),
    ]
    timestamps = [0.00, 0.08, 0.16, 0.24, 0.32, 0.40]

    detection = service._detect_runtime_gesture(
        observation=make_push_observation(
            index_tip_depth=-0.01, captured_at=timestamps[-1]
        ),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is not None
    assert detection.gesture == "swipe_left"


def test_service_detects_swipe_down_from_recent_upper_turning_point():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    trajectory = [
        (0.50, 0.64),
        (0.50, 0.54),
        (0.50, 0.44),
        (0.50, 0.34),
        (0.50, 0.42),
        (0.50, 0.52),
        (0.50, 0.63),
    ]
    timestamps = [0.00, 0.12, 0.24, 0.36, 0.48, 0.60, 0.72]

    detection = service._detect_runtime_gesture(
        observation=GestureObservation(
            point=trajectory[-1], tracking_source="palm_center"
        ),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is not None
    assert detection.gesture == "swipe_down"


def test_service_requires_open_commit_before_circle_publication():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    trajectory = [
        (0.56, 0.74),
        (0.60, 0.63),
        (0.61, 0.53),
        (0.58, 0.44),
        (0.51, 0.41),
        (0.43, 0.46),
        (0.40, 0.53),
    ]
    timestamps = [0.00, 0.12, 0.24, 0.36, 0.48, 0.60, 0.72]

    analysis = None
    for point, observed_at in zip(trajectory, timestamps):
        analysis = service._analyze_runtime_gesture(
            observation=GestureObservation(
                point=point,
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
            ),
            observed_at=observed_at,
            trajectory=[p for p, t in zip(trajectory, timestamps) if t <= observed_at],
            trajectory_timestamps=[t for t in timestamps if t <= observed_at],
            hand_size=0.16,
            pose_features=make_circle_pose_features(hand_openness=0.2),
        )

    assert analysis is not None
    assert analysis.detection is None
    assert analysis.candidate_scores.get("circle", 0.0) > 0.0


def test_circle_runtime_state_commits_on_final_open():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    frames = [
        ((0.417, 0.543), 0.20),
        ((0.395, 0.620), 0.22),
        ((0.294, 0.587), 0.20),
        ((0.257, 0.520), 0.20),
        ((0.293, 0.375), 0.20),
        ((0.416, 0.291), 0.20),
        ((0.533, 0.425), 0.21),
        ((0.535, 0.572), 0.20),
        ((0.406, 0.576), 0.62),
    ]

    detection = None
    for index, (point, openness) in enumerate(frames):
        _, detection = service._update_circle_runtime_state(
            observation=GestureObservation(
                point=point,
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
            ),
            observed_at=index * 0.08,
            hand_size=0.16,
            pose_features=make_circle_pose_features(hand_openness=openness),
        )
        if index < len(frames) - 1:
            assert detection is None

    assert detection is not None
    assert detection.gesture == "circle"
    assert detection.metrics["finalize_immediately"] is True


def test_circle_runtime_state_tolerates_transient_open_spike():
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    frames = [
        ((0.417, 0.543), 0.20),
        ((0.395, 0.620), 0.22),
        ((0.294, 0.587), 0.20),
        ((0.257, 0.520), 0.20),
        ((0.293, 0.375), 0.20),
        ((0.416, 0.291), 0.20),
        ((0.533, 0.425), 1.00),
        ((0.535, 0.572), 0.20),
        ((0.406, 0.576), 0.62),
    ]

    detection = None
    for index, (point, openness) in enumerate(frames):
        state, detection = service._update_circle_runtime_state(
            observation=GestureObservation(
                point=point,
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
            ),
            observed_at=index * 0.08,
            hand_size=0.16,
            pose_features=make_circle_pose_features(hand_openness=openness),
        )
        if index == 6:
            assert state is not None
            assert state.ready_to_commit is False

    assert detection is not None
    assert detection.gesture == "circle"


def test_analyze_runtime_gesture_suppresses_push_during_active_circle(monkeypatch):
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    priming_points = [
        (0.417, 0.543),
        (0.395, 0.620),
        (0.294, 0.587),
        (0.257, 0.520),
        (0.293, 0.375),
        (0.416, 0.291),
    ]
    timestamps = [index * 0.08 for index in range(len(priming_points))]
    for point, observed_at in zip(priming_points, timestamps):
        service._update_circle_runtime_state(
            observation=GestureObservation(
                point=point,
                hand="right",
                hand_size=0.16,
                tracking_source="palm_center",
            ),
            observed_at=observed_at,
            hand_size=0.16,
            pose_features=make_circle_pose_features(hand_openness=0.2),
        )

    called = {"push": False}

    def fake_push(_observation, _observed_at):
        called["push"] = True
        return GestureDetectionResult(
            gesture="push_click_long",
            confidence=1.0,
            tracking_source="index_push",
        )

    monkeypatch.setattr(service, "_detect_push_gesture", fake_push)

    analysis = service._analyze_runtime_gesture(
        observation=GestureObservation(
            point=(0.533, 0.425),
            hand="right",
            hand_size=0.16,
            tracking_source="palm_center",
        ),
        observed_at=0.56,
        trajectory=priming_points + [(0.533, 0.425)],
        trajectory_timestamps=timestamps + [0.56],
        hand_size=0.16,
        pose_features=make_circle_pose_features(hand_openness=0.2),
    )

    assert called["push"] is False
    assert analysis.candidate_scores.get("circle", 0.0) > 0.0


def test_service_does_not_prefer_circle_for_open_hand_pose(monkeypatch):
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    monkeypatch.setattr(
        "services.gesture.runtime.extract_hand_pose_features",
        lambda observation: HandPoseFeatures(
            hand="right",
            point=observation.point,
            palm_center=observation.point,
            hand_size=0.16,
            palm_span=0.11,
            center_distance=0.02,
            hand_openness=0.78,
            index_extension_ratio=1.04,
            push_depth=0.0,
            finger_states={},
            tracking_source="palm_center",
        ),
    )

    trajectory = [
        (0.56, 0.74),
        (0.60, 0.63),
        (0.61, 0.53),
        (0.58, 0.44),
        (0.51, 0.41),
        (0.43, 0.46),
        (0.40, 0.53),
    ]

    candidates = service._collect_runtime_single_hand_candidates(
        observation=GestureObservation(
            point=trajectory[-1], tracking_source="palm_center"
        ),
        trajectory=trajectory,
        hand_size=0.16,
        tracking_source="palm_center",
    )

    assert all(candidate.gesture != "circle" for candidate in candidates)


def test_service_suppresses_swipe_candidates_for_closed_hand_pose(monkeypatch):
    service = GestureService(
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        realtime=CapturingRealtimeHub(),
    )
    service.reload_config()

    monkeypatch.setattr(
        "services.gesture.runtime.extract_hand_pose_features",
        lambda observation: HandPoseFeatures(
            hand="right",
            point=observation.point,
            palm_center=observation.point,
            hand_size=0.16,
            palm_span=0.10,
            center_distance=0.03,
            hand_openness=0.18,
            index_extension_ratio=0.96,
            push_depth=0.0,
            finger_states={},
            tracking_source="palm_center",
        ),
    )

    trajectory = [
        (0.20, 0.50),
        (0.30, 0.50),
        (0.40, 0.50),
        (0.50, 0.50),
        (0.60, 0.50),
        (0.80, 0.50),
    ]

    candidates = service._collect_runtime_single_hand_candidates(
        observation=GestureObservation(
            point=trajectory[-1], tracking_source="palm_center"
        ),
        trajectory=trajectory,
        hand_size=0.16,
        tracking_source="palm_center",
    )

    assert candidates == []


@pytest.mark.asyncio
async def test_get_gesture_status(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.get("/api/v1/gestures/status")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["running"] is False
    assert data["camera_name"] is None
    assert data["last_confidence"] is None


@pytest.mark.asyncio
async def test_get_gesture_devices(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.get("/api/v1/gestures/devices")
    assert response.status_code == 200
    data = response.json()
    assert len(data["devices"]) == 2
    assert data["devices"][1]["name"] == "Mock USB Camera"


@pytest.mark.asyncio
async def test_start_gesture_detection(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.post("/api/v1/gestures/start", json={"camera_index": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is True
    assert data["camera_index"] == 1


@pytest.mark.asyncio
async def test_start_gesture_detection_unavailable(
    client,
    override_unavailable_gesture_dependency,
):
    _ = override_unavailable_gesture_dependency
    response = await client.post("/api/v1/gestures/start", json={"camera_index": 0})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_stop_gesture_detection(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.post("/api/v1/gestures/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False


@pytest.mark.asyncio
async def test_get_preview_frame_not_found(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.get("/api/v1/gestures/frame")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_preview_frame_includes_freshness_metadata(
    client, override_gesture_dependency
):
    override_gesture_dependency.frame = "data:image/jpeg;base64,dGVzdA=="

    response = await client.get("/api/v1/gestures/frame")

    assert response.status_code == 200
    payload = response.json()
    assert payload["image"] == "data:image/jpeg;base64,dGVzdA=="
    assert payload["captured_at"] is None
    assert payload["frame_age_ms"] is None


@pytest.mark.asyncio
async def test_dev_capture_endpoint_starts_capture(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.post("/api/v1/gestures/dev/capture")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["frames_target"] == 72
    assert data["target_fps"] == 24.0
    assert data["output_dir"] == "/tmp/mock-gesture-capture"


@pytest.mark.asyncio
async def test_dev_process_video_endpoint_disabled(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.post(
        "/api/v1/gestures/dev/process-video?video_path=/tmp/demo.mp4"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_process_video_requires_absolute_path(
    client, override_gesture_dependency
):
    _ = override_gesture_dependency
    original_value = settings.GESTURES_DEV_ENDPOINT_ENABLED
    settings.GESTURES_DEV_ENDPOINT_ENABLED = True
    try:
        response = await client.post(
            "/api/v1/gestures/dev/process-video?video_path=relative/demo.mp4"
        )
    finally:
        settings.GESTURES_DEV_ENDPOINT_ENABLED = original_value

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_dev_process_video_endpoint_enabled(client, override_gesture_dependency):
    _ = override_gesture_dependency
    original_value = settings.GESTURES_DEV_ENDPOINT_ENABLED
    settings.GESTURES_DEV_ENDPOINT_ENABLED = True
    try:
        response = await client.post(
            "/api/v1/gestures/dev/process-video?video_path=/tmp/demo.mp4"
        )
    finally:
        settings.GESTURES_DEV_ENDPOINT_ENABLED = original_value

    assert response.status_code == 200
    data = response.json()
    assert data["gestures"] == ["circle"]
    assert data["confidence"] is not None
    assert data["tracking_source"] == "palm_center"


@pytest.mark.asyncio
async def test_shared_websocket_receives_gesture_event():
    payload = {
        "eventType": "GestureDetected",
        "payload": {
            "gesture": "swipe_right",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "camera",
            "hand": "right",
            "confidence": 0.87,
            "tracking_source": "palm_center",
        },
    }

    websocket = FakeWebSocket()
    task = asyncio.create_task(websocket_endpoint(websocket))
    await asyncio.sleep(0)

    websocket.queue_text("ping")
    await asyncio.sleep(0.05)
    await realtime_hub.broadcast(payload)
    await asyncio.sleep(0.05)
    websocket.queue_disconnect()
    await asyncio.wait_for(task, timeout=1.0)

    assert websocket.accepted is True
    assert websocket.messages[0]["eventType"] == "Pong"
    assert websocket.messages[1]["eventType"] == "GestureDetected"
    assert websocket.messages[1]["payload"]["gesture"] == "swipe_right"
    assert websocket.messages[1]["payload"]["confidence"] == 0.87
