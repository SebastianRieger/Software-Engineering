import asyncio
import math
import threading
import time
from concurrent.futures import Future
from datetime import datetime, timezone

import pytest
from fastapi import WebSocketDisconnect

from core.config import settings
from core.realtime import realtime_hub
from main import websocket_endpoint
from schemas.gestures import GestureConfig
from schemas.interactions import InputActionConfig, InputActionMapping
from services.gesture.detection import (
    GestureDetectionResult,
    analyze_runtime_gesture,
    detect_gesture_candidates,
    detect_gesture_with_confidence,
    detect_gesture_from_trajectory,
    extract_gesture_features,
    select_best_gesture_candidate,
)
from services.gesture.runtime import GestureService, GestureServiceError
from services.gesture.tracking import (
    HandPoseFeatures,
    GestureAdapterError,
    GestureObservation,
    TrackedHandObservation,
    build_hand_landmark_map,
    compute_hand_size_scale,
    compute_hand_tracking_point,
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
    ):
        self.config = config or GestureConfig()
        self.input_action_config = input_action_config or InputActionConfig()

    def get_gesture_config(self):
        return self.config

    def get_input_action_config(self):
        return self.input_action_config


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
            "tracking_source": detection.tracking_source if detection else tracking_source,
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


def make_push_observation(index_tip_depth: float, captured_at: float) -> GestureObservation:
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


def test_extract_hand_pose_features_builds_finger_scores_for_push_like_pose():
    observation = make_push_observation(index_tip_depth=-0.16, captured_at=time.monotonic())

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
        TrackedHandObservation(point=left_point, hand="left", hand_size=0.16, tracking_source="palm_center"),
        TrackedHandObservation(point=right_point, hand="right", hand_size=0.16, tracking_source="palm_center"),
    ]
    return GestureObservation(
        point=((left_point[0] + right_point[0]) / 2, (left_point[1] + right_point[1]) / 2),
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
    assert gesture == "swipe_right"


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
    assert gesture == "swipe_left"


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
        (0.5 + 0.08 * math.cos(angle), 0.5 + 0.08 * math.sin(angle))
        for angle in angles
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
            (0.54, 0.70),
            (0.58, 0.66),
            (0.62, 0.60),
            (0.60, 0.55),
            (0.57, 0.49),
            (0.52, 0.45),
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
    assert best.gesture == "swipe_right"
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
    assert detection.gesture == "swipe_right"
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
    assert detection.gesture == "swipe_right"


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
        adapter_factory=lambda: ResolvedIndexAdapter(observations=[GestureObservation(point=None)]),
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
    service = GestureService(
        adapter_factory=lambda: FailingAdapter(observations=[]),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    started = service.start(camera_index=0)
    assert started["running"] is True

    assert wait_until(lambda: service.get_status()["running"] is False)
    assert service.get_status()["last_error"] == "camera read failed"


def test_service_retries_transient_adapter_failure_and_recovers():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(point=(0.2, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.3, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.4, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.5, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.6, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.8, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
    ]
    adapter = FlakyAdapter(observations=observations, failures_before_success=1)
    service = GestureService(
        adapter_factory=lambda: adapter,
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(lambda: len(hub.messages) >= 1)
    service.stop()

    assert adapter.failures_seen == 1
    assert hub.messages[0]["payload"]["gesture"] == "swipe_right"


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
    assert stopped["last_error"] == "Gesten-Thread konnte nicht rechtzeitig beendet werden."


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
        GestureObservation(point=(0.20, 0.5), hand="right", hand_size=0.08, tracking_source="palm_center"),
        GestureObservation(point=(0.22, 0.5), hand="right", hand_size=0.08, tracking_source="palm_center"),
        GestureObservation(point=(0.24, 0.5), hand="right", hand_size=0.08, tracking_source="palm_center"),
        GestureObservation(point=(0.26, 0.5), hand="right", hand_size=0.08, tracking_source="palm_center"),
        GestureObservation(point=(0.28, 0.5), hand="right", hand_size=0.08, tracking_source="palm_center"),
        GestureObservation(point=(0.30, 0.5), hand="right", hand_size=0.08, tracking_source="palm_center"),
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

    assert wait_until(lambda: len(hub.messages) >= 1)
    status = service.get_status()
    service.stop()

    assert status["last_gesture"] == "swipe_right"


def test_service_instances_keep_separate_configs():
    left_service = GestureService(
        adapter_factory=lambda: SequenceAdapter(),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(GestureConfig(swipe_threshold=0.11)),
    )
    right_service = GestureService(
        adapter_factory=lambda: SequenceAdapter(),
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: StaticGestureConfigRepository(GestureConfig(swipe_threshold=0.25)),
    )

    left_service.reload_config()
    right_service.reload_config()

    assert left_service._active_config.swipe_threshold == pytest.approx(0.11)
    assert right_service._active_config.swipe_threshold == pytest.approx(0.25)


def test_service_detects_and_exposes_confidence_metadata():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(point=(0.2, 0.5), hand="right", tracking_source="palm_center"),
        GestureObservation(point=(0.3, 0.5), hand="right", tracking_source="palm_center"),
        GestureObservation(point=(0.4, 0.5), hand="right", tracking_source="palm_center"),
        GestureObservation(point=(0.5, 0.5), hand="right", tracking_source="palm_center"),
        GestureObservation(point=(0.6, 0.5), hand="right", tracking_source="palm_center"),
        GestureObservation(point=(0.8, 0.5), hand="right", tracking_source="palm_center"),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(lambda: len(hub.messages) >= 1)
    status = service.get_status()
    service.stop()

    assert status["last_gesture"] == "swipe_right"
    assert status["last_confidence"] is not None
    assert status["last_confidence"] > 0.9
    assert status["last_tracking_source"] == "palm_center"


def test_cooldown_prevents_spam_and_emits_event():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(point=(0.2, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.3, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.4, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.5, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.6, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.8, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.2, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.3, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.4, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.5, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.6, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
        GestureObservation(point=(0.8, 0.5), hand="right", preview_bytes=b"frame", tracking_source="palm_center"),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
    )

    service.start()
    assert wait_until(lambda: len(hub.messages) >= 1)
    service.stop()

    gesture_messages = filter_messages(hub.messages, "GestureDetected")
    action_messages = filter_messages(hub.messages, "UIActionRequested")
    assert len(gesture_messages) == 1
    assert len(action_messages) == 1
    assert gesture_messages[0]["payload"]["confidence"] is not None
    assert gesture_messages[0]["payload"]["tracking_source"] == "palm_center"
    assert action_messages[0]["payload"]["action"] == "move_focus_right"
    assert service.get_frame() is not None


def test_service_publishes_ui_action_requested_event_for_swipe():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(point=(0.2, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.3, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.4, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.5, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.6, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
        GestureObservation(point=(0.8, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center"),
    ]
    repository = StaticGestureConfigRepository(
        input_action_config=InputActionConfig(
            mappings=[
                InputActionMapping(
                    input_source="gesture",
                    raw_input="swipe_right",
                    action="move_focus_right",
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
    assert wait_until(lambda: len(filter_messages(hub.messages, "UIActionRequested")) >= 1)
    service.stop()

    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert action_message["payload"]["raw_input"] == "swipe_right"
    assert action_message["payload"]["action"] == "move_focus_right"


def test_service_gates_ui_actions_while_calibration_is_active():
    hub = CapturingRealtimeHub()
    calibration_runtime = CapturingCalibrationRuntime()
    observations = [
        GestureObservation(point=(0.2, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.00),
        GestureObservation(point=(0.3, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.05),
        GestureObservation(point=(0.4, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.10),
        GestureObservation(point=(0.5, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.15),
        GestureObservation(point=(0.6, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.20),
        GestureObservation(point=(0.8, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.25),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
        config_repository_factory=lambda: StaticGestureConfigRepository(),
        calibration_runtime=calibration_runtime,
    )

    service.start()
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
    service.stop()

    assert filter_messages(hub.messages, "UIActionRequested") == []
    assert len(calibration_runtime.samples) == 1
    assert calibration_runtime.samples[0].target_id == "swipe_right"


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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_short"
    assert action_message["payload"]["action"] == "primary_click"


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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    action_message = filter_messages(hub.messages, "UIActionRequested")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_long"
    assert action_message["payload"]["action"] == "secondary_select"


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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    assert gesture_message["payload"]["gesture"] == "push_click_long"


def test_service_defers_swipe_event_until_motion_finishes():
    hub = CapturingRealtimeHub()
    adapter = PausingSequenceAdapter(
        observations=[
            GestureObservation(point=(0.72, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.00),
            GestureObservation(point=(0.64, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.08),
            GestureObservation(point=(0.56, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.16),
            GestureObservation(point=(0.48, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.24),
            GestureObservation(point=(0.36, 0.5), hand="right", hand_size=0.16, tracking_source="palm_center", captured_at=0.32),
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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
    service.stop()

    gesture_message = filter_messages(hub.messages, "GestureDetected")[0]
    assert gesture_message["payload"]["gesture"] == "swipe_left"


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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
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
    assert wait_until(lambda: len(filter_messages(hub.messages, "GestureDetected")) >= 1)
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
        observation=GestureObservation(point=trajectory[-1], tracking_source="palm_center"),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is not None
    assert detection.gesture == "swipe_left"


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
        observation=GestureObservation(point=trajectory[-1], tracking_source="palm_center"),
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
        observation=make_push_observation(index_tip_depth=-0.12, captured_at=timestamps[-1]),
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
        observation=make_push_observation(index_tip_depth=-0.01, captured_at=timestamps[-1]),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is not None
    assert detection.gesture == "swipe_right"


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
        observation=GestureObservation(point=trajectory[-1], tracking_source="palm_center"),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is not None
    assert detection.gesture == "swipe_down"


def test_service_holds_swipe_when_recent_window_already_looks_circular():
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

    detection = service._detect_runtime_gesture(
        observation=GestureObservation(point=trajectory[-1], tracking_source="palm_center"),
        observed_at=timestamps[-1],
        trajectory=trajectory,
        trajectory_timestamps=timestamps,
        hand_size=0.16,
    )

    assert detection is not None
    assert detection.gesture == "circle"


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
        observation=GestureObservation(point=trajectory[-1], tracking_source="palm_center"),
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
        observation=GestureObservation(point=trajectory[-1], tracking_source="palm_center"),
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
async def test_dev_process_video_endpoint_disabled(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.post("/api/v1/gestures/dev/process-video?video_path=/tmp/demo.mp4")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_process_video_requires_absolute_path(client, override_gesture_dependency):
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
