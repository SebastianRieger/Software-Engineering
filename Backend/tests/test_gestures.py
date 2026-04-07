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
    GestureService,
    GestureServiceError,
    detect_gesture_from_trajectory,
)


class CapturingRealtimeHub:
    def __init__(self):
        self.messages = []

    def publish_from_thread(self, message):
        self.messages.append(message)
        future = Future()
        future.set_result(None)
        return future


class SequenceAdapter:
    def __init__(self, observations=None, available=True):
        self.observations = list(observations or [])
        self.available = available
        self.opened = False
        self.closed = False

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

    def process_video(self, video_path, classifier):
        trajectory = [
            (0.5, 0.2),
            (0.5, 0.3),
            (0.5, 0.4),
            (0.5, 0.5),
            (0.5, 0.6),
            (0.5, 0.8),
        ]
        gesture = classifier(trajectory)
        return {
            "gestures": [gesture] if gesture else [],
            "frames_processed": 6,
            "trajectory_points": len(trajectory),
        }


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
    service = GestureService(adapter_factory=lambda: adapter, realtime=hub)

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
    )

    with pytest.raises(GestureServiceError) as exc_info:
        service.start(camera_index=0)

    assert exc_info.value.status_code == 503


def test_cooldown_prevents_spam_and_emits_event():
    hub = CapturingRealtimeHub()
    observations = [
        GestureObservation(point=(0.2, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.3, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.4, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.5, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.6, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.8, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.2, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.3, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.4, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.5, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.6, 0.5), hand="right", preview_bytes=b"frame"),
        GestureObservation(point=(0.8, 0.5), hand="right", preview_bytes=b"frame"),
    ]
    service = GestureService(
        adapter_factory=lambda: SequenceAdapter(observations=observations),
        realtime=hub,
    )

    service.start()
    assert wait_until(lambda: len(hub.messages) >= 1)
    service.stop()

    assert len(hub.messages) == 1
    assert hub.messages[0]["eventType"] == "GestureDetected"
    assert service.get_frame() is not None


@pytest.mark.asyncio
async def test_get_gesture_status(client, override_gesture_dependency):
    response = await client.get("/api/v1/gestures/status")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["running"] is False


@pytest.mark.asyncio
async def test_start_gesture_detection(client, override_gesture_dependency):
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
    response = await client.post("/api/v1/gestures/start", json={"camera_index": 0})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_stop_gesture_detection(client, override_gesture_dependency):
    response = await client.post("/api/v1/gestures/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False


@pytest.mark.asyncio
async def test_get_preview_frame_not_found(client, override_gesture_dependency):
    response = await client.get("/api/v1/gestures/frame")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_process_video_endpoint_disabled(client, override_gesture_dependency):
    response = await client.post("/api/v1/gestures/dev/process-video?video_path=/tmp/demo.mp4")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dev_process_video_endpoint_enabled(client, override_gesture_dependency):
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


@pytest.mark.asyncio
async def test_shared_websocket_receives_gesture_event():
    payload = {
        "eventType": "GestureDetected",
        "payload": {
            "gesture": "swipe_right",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "camera",
            "hand": "right",
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
