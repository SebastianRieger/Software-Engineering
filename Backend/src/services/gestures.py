import base64
import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Protocol

from core.config import settings
from core.realtime import RealtimeHub, realtime_hub


logger = logging.getLogger(__name__)


try:
    import cv2
except Exception:
    cv2 = None

try:
    import mediapipe as mp
except Exception:
    mp = None


GestureName = str


@dataclass(slots=True)
class GestureObservation:
    point: tuple[float, float] | None
    hand: str | None = None
    preview_bytes: bytes | None = None


class GestureAdapterError(Exception):
    pass


class GestureServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class GestureAdapter(Protocol):
    def is_available(self) -> bool:
        ...

    def open(self, camera_index: int) -> None:
        ...

    def read(self) -> GestureObservation | None:
        ...

    def close(self) -> None:
        ...

    def process_video(
        self,
        video_path: str,
        classifier: Callable[[list[tuple[float, float]]], GestureName | None],
    ) -> dict[str, int | list[GestureName]]:
        ...


def smooth_point(
    previous_point: tuple[float, float] | None,
    point: tuple[float, float],
    alpha: float,
) -> tuple[float, float]:
    if previous_point is None:
        return point

    return (
        alpha * point[0] + (1 - alpha) * previous_point[0],
        alpha * point[1] + (1 - alpha) * previous_point[1],
    )


def detect_gesture_from_trajectory(
    trajectory: list[tuple[float, float]],
    swipe_threshold: float,
    down_threshold: float,
    circle_sweep_min: float,
    circle_cv_max: float,
) -> GestureName | None:
    if len(trajectory) < 6:
        return None

    xs = [point[0] for point in trajectory]
    ys = [point[1] for point in trajectory]

    dx_total = xs[-1] - xs[0]
    dy_total = ys[-1] - ys[0]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)

    if (
        abs(dx_total) > swipe_threshold
        and abs(dx_total) > abs(dy_total) * 1.5
        and span_x > 0.06
    ):
        return "swipe_right" if dx_total > 0 else "swipe_left"

    if (
        dy_total > down_threshold
        and dy_total > abs(dx_total) * 1.2
        and span_y > 0.06
    ):
        return "swipe_down"

    center_x = mean(xs)
    center_y = mean(ys)
    vectors = [(x - center_x, y - center_y) for x, y in trajectory]
    radii = [math.hypot(x, y) for x, y in vectors]

    if not radii or mean(radii) < 0.01:
        return None

    angles = [math.atan2(y, x) for x, y in vectors]
    total_sweep = 0.0
    previous_angle = angles[0]
    for angle in angles[1:]:
        delta = angle - previous_angle
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        total_sweep += delta
        previous_angle = angle

    radius_mean = mean(radii)
    radius_cv = pstdev(radii) / (radius_mean + 1e-6)

    if abs(total_sweep) > circle_sweep_min and radius_cv < circle_cv_max:
        return "circle"

    return None


class MediaPipeHandsAdapter:
    def __init__(self) -> None:
        self.cap = None
        self.hands = None

    def is_available(self) -> bool:
        return cv2 is not None and mp is not None

    def open(self, camera_index: int) -> None:
        if not self.is_available():
            raise GestureAdapterError(
                "MediaPipe Hands oder OpenCV ist in dieser Umgebung nicht verfuegbar."
            )

        self.cap = cv2.VideoCapture(camera_index)
        if not (self.cap and self.cap.isOpened()):
            if self.cap is not None:
                self.cap.release()
            self.cap = None
            raise GestureAdapterError("Kamera konnte nicht geoeffnet werden.")

        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def read(self) -> GestureObservation | None:
        if self.cap is None or self.hands is None:
            return None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return GestureObservation(point=None)

        point, hand = self._extract_observation(frame)
        preview_bytes = None
        try:
            ok, jpeg = cv2.imencode(".jpg", frame)
            if ok:
                preview_bytes = jpeg.tobytes()
        except Exception:
            preview_bytes = None

        return GestureObservation(point=point, hand=hand, preview_bytes=preview_bytes)

    def close(self) -> None:
        if self.hands is not None:
            self.hands.close()
            self.hands = None
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def process_video(
        self,
        video_path: str,
        classifier: Callable[[list[tuple[float, float]]], GestureName | None],
    ) -> dict[str, int | list[GestureName]]:
        if not self.is_available():
            raise GestureAdapterError(
                "MediaPipe Hands oder OpenCV ist in dieser Umgebung nicht verfuegbar."
            )

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise GestureAdapterError(f"Video konnte nicht geoeffnet werden: {video_path}")

        hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        trajectory: list[tuple[float, float]] = []
        smoothed_point: tuple[float, float] | None = None
        frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                frame_count += 1
                point, _ = self._extract_observation(frame, hands_instance=hands)
                if point is None:
                    continue

                smoothed_point = smooth_point(
                    previous_point=smoothed_point,
                    point=point,
                    alpha=settings.GESTURE_SMOOTHING_ALPHA,
                )
                trajectory.append(smoothed_point)

            gesture = classifier(trajectory)
            gestures = [gesture] if gesture is not None else []
            return {
                "gestures": gestures,
                "frames_processed": frame_count,
                "trajectory_points": len(trajectory),
            }
        finally:
            hands.close()
            cap.release()

    def _extract_observation(
        self,
        frame,
        hands_instance=None,
    ) -> tuple[tuple[float, float] | None, str | None]:
        hands_instance = hands_instance or self.hands
        if hands_instance is None:
            return None, None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_instance.process(rgb)
        if not results.multi_hand_landmarks:
            return None, None

        hand_landmarks = results.multi_hand_landmarks[0]
        wrist = hand_landmarks.landmark[0]
        handedness = None
        if results.multi_handedness:
            handedness = results.multi_handedness[0].classification[0].label.lower()

        return (float(wrist.x), float(wrist.y)), handedness


class GestureService:
    def __init__(
        self,
        adapter_factory: Callable[[], GestureAdapter] | None = None,
        realtime: RealtimeHub | None = None,
    ) -> None:
        self.adapter_factory = adapter_factory or MediaPipeHandsAdapter
        self.realtime = realtime or realtime_hub
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._adapter: GestureAdapter | None = None
        self.running = False
        self.camera_index: int | None = None
        self.latest_frame_data_url: str | None = None
        self.smoothed_point: tuple[float, float] | None = None
        self.trajectory: list[tuple[float, float]] = []
        self.last_gesture: GestureName | None = None
        self.last_gesture_at: datetime | None = None
        self.last_gesture_time_by_name: dict[str, float] = {}
        self.last_hand: str | None = None

    def is_available(self) -> bool:
        try:
            adapter = self.adapter_factory()
            return adapter.is_available()
        except Exception:
            return False

    def start(self, camera_index: int = 0) -> dict[str, object]:
        with self._lock:
            if self.running:
                return self.get_status()

            if not self.is_available():
                raise GestureServiceError(
                    "Gestenerkennung ist in dieser Umgebung nicht verfuegbar.",
                    status_code=503,
                )

            adapter = self.adapter_factory()
            try:
                adapter.open(camera_index)
            except GestureAdapterError as exc:
                raise GestureServiceError(str(exc), status_code=503) from exc

            self._reset_runtime_state()
            self._adapter = adapter
            self.camera_index = camera_index
            self.running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

        return self.get_status()

    def stop(self) -> dict[str, object]:
        thread = None
        adapter = None
        with self._lock:
            self.running = False
            self._stop_event.set()
            thread = self._thread
            adapter = self._adapter
            self._thread = None
            self._adapter = None

        if thread is not None:
            thread.join(timeout=2.0)

        if adapter is not None:
            adapter.close()

        with self._lock:
            self.camera_index = None

        return self.get_status()

    def shutdown(self) -> None:
        self.stop()

    def get_status(self) -> dict[str, object]:
        return {
            "available": self.is_available(),
            "running": self.running,
            "camera_index": self.camera_index,
            "last_gesture": self.last_gesture,
            "last_gesture_at": self.last_gesture_at,
            "debug_frame_available": self.latest_frame_data_url is not None,
        }

    def get_frame(self) -> str | None:
        return self.latest_frame_data_url

    def process_video(self, video_path: str) -> dict[str, int | list[GestureName]]:
        if not self.is_available():
            raise GestureServiceError(
                "Gestenerkennung ist in dieser Umgebung nicht verfuegbar.",
                status_code=503,
            )

        if not Path(video_path).exists():
            raise GestureServiceError(
                f"Video nicht gefunden: {video_path}",
                status_code=404,
            )

        adapter = self.adapter_factory()
        try:
            return adapter.process_video(video_path, classifier=self._detect_gesture)
        except GestureAdapterError as exc:
            raise GestureServiceError(str(exc), status_code=503) from exc

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            adapter = self._adapter
            if adapter is None:
                break

            try:
                observation = adapter.read()
            except GestureAdapterError as exc:
                logger.warning("Gesture adapter read failed: %s", exc)
                break

            if observation is None:
                time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
                continue

            self._update_preview(observation.preview_bytes)

            if observation.point is None:
                self.smoothed_point = None
                self.trajectory.clear()
                time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
                continue

            self.last_hand = observation.hand
            self.smoothed_point = smooth_point(
                previous_point=self.smoothed_point,
                point=observation.point,
                alpha=settings.GESTURE_SMOOTHING_ALPHA,
            )
            self.trajectory.append(self.smoothed_point)
            if len(self.trajectory) > settings.GESTURE_MAX_TRAJECTORY_POINTS:
                self.trajectory.pop(0)

            gesture = self._detect_gesture(self.trajectory)
            if gesture is not None and self._cooldown_elapsed(gesture):
                self.last_gesture = gesture
                self.last_gesture_at = datetime.now(timezone.utc)
                self._publish_gesture_event(gesture=gesture, hand=observation.hand)

        self.running = False

    def _publish_gesture_event(self, gesture: GestureName, hand: str | None) -> None:
        if self.last_gesture_at is None:
            return

        self.realtime.publish_from_thread(
            {
                "eventType": "GestureDetected",
                "payload": {
                    "gesture": gesture,
                    "timestamp": self.last_gesture_at.isoformat(),
                    "source": "camera",
                    "hand": hand,
                },
            }
        )

    def _cooldown_elapsed(self, gesture: GestureName) -> bool:
        now = time.time()
        last_seen = self.last_gesture_time_by_name.get(gesture, 0.0)
        if now - last_seen <= settings.GESTURE_COOLDOWN_SECONDS:
            return False

        self.last_gesture_time_by_name[gesture] = now
        return True

    def _detect_gesture(
        self,
        trajectory: list[tuple[float, float]],
    ) -> GestureName | None:
        return detect_gesture_from_trajectory(
            trajectory=trajectory,
            swipe_threshold=settings.GESTURE_SWIPE_THRESHOLD,
            down_threshold=settings.GESTURE_DOWN_THRESHOLD,
            circle_sweep_min=settings.GESTURE_CIRCLE_SWEEP_MIN,
            circle_cv_max=settings.GESTURE_CIRCLE_RADIUS_CV_MAX,
        )

    def _update_preview(self, preview_bytes: bytes | None) -> None:
        if preview_bytes is None:
            return

        encoded = base64.b64encode(preview_bytes).decode("ascii")
        self.latest_frame_data_url = f"data:image/jpeg;base64,{encoded}"

    def _reset_runtime_state(self) -> None:
        self.latest_frame_data_url = None
        self.smoothed_point = None
        self.trajectory = []
        self.last_gesture = None
        self.last_gesture_at = None
        self.last_hand = None
        self.last_gesture_time_by_name = {}


gesture_service = GestureService()
