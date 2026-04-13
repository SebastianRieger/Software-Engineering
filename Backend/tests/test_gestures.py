import asyncio
import math
import time
from concurrent.futures import Future
from datetime import datetime, timezone

import pytest
from fastapi import WebSocketDisconnect

from core.config import settings
from core.realtime import realtime_hub
from main import websocket_endpoint
from services.gestures import (
    GestureObservation,
    GestureAdapterError,
    GestureConfig,
    GestureService,
    GestureServiceError,
    build_hand_landmark_map,
    compute_hand_tracking_point,
    detect_gesture_candidates,
    detect_gesture_with_confidence,
    detect_gesture_from_trajectory,
    estimate_hand_size,
    extract_gesture_features,
    select_best_gesture_candidate,
)


class CapturingRealtimeHub:
    def __init__(self):
        self.messages = []

    def publish_from_thread(self, message):
        self.messages.append(message)
        future = Future()
        future.set_result(None)
        return future


class StaticGestureConfigRepository:
    def __init__(self, config: GestureConfig | None = None):
        self.config = config or GestureConfig()

    def get_gesture_config(self):
        return self.config


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
        detection = classifier(trajectory)
        return {
            "gestures": [detection.gesture] if detection else [],
            "frames_processed": 6,
            "trajectory_points": len(trajectory),
            "confidence": detection.confidence if detection else None,
            "tracking_source": detection.tracking_source if detection else tracking_source,
        }


class FailingAdapter(SequenceAdapter):
    def read(self):
        raise GestureAdapterError("camera read failed")


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
        circle_min_radius=0.01,
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
        circle_min_radius=0.01,
    )
    assert features is not None

    candidates = detect_gesture_candidates(
        features=features,
        swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
        down_threshold=settings.GESTURE_DOWN_THRESHOLD,
        circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
        circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        swipe_min_span=settings.GESTURE_SWIPE_MIN_SPAN,
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

    assert len(hub.messages) == 1
    assert hub.messages[0]["eventType"] == "GestureDetected"
    assert hub.messages[0]["payload"]["confidence"] is not None
    assert hub.messages[0]["payload"]["tracking_source"] == "palm_center"
    assert service.get_frame() is not None


@pytest.mark.asyncio
async def test_get_gesture_status(client, override_gesture_dependency):
    _ = override_gesture_dependency
    response = await client.get("/api/v1/gestures/status")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["running"] is False
    assert data["last_confidence"] is None


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
