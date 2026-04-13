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
from repositories.config import ConfigRepository
from schemas.gestures import GestureConfig


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
GesturePoint = tuple[float, float]
GestureLandmarks = dict[str, GesturePoint]


HAND_LANDMARK_NAMES = {
    "wrist": 0,
    "thumb_tip": 4,
    "index_mcp": 5,
    "index_tip": 8,
    "middle_mcp": 9,
    "middle_tip": 12,
    "ring_mcp": 13,
    "ring_tip": 16,
    "pinky_mcp": 17,
    "pinky_tip": 20,
}

PALM_CENTER_LANDMARKS = (
    "wrist",
    "index_mcp",
    "middle_mcp",
    "ring_mcp",
    "pinky_mcp",
)


@dataclass(slots=True)
class GestureObservation:
    point: GesturePoint | None
    hand: str | None = None
    preview_bytes: bytes | None = None
    landmarks: GestureLandmarks | None = None
    hand_size: float | None = None
    tracking_source: str | None = None


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
        smoothing_alpha: float,
    ) -> dict[str, int | list[GestureName]]:
        ...


def build_hand_landmark_map(hand_landmarks) -> GestureLandmarks:
    return {
        name: (
            float(hand_landmarks.landmark[index].x),
            float(hand_landmarks.landmark[index].y),
        )
        for name, index in HAND_LANDMARK_NAMES.items()
    }


def compute_hand_tracking_point(landmarks: GestureLandmarks) -> GesturePoint | None:
    points = [landmarks[name] for name in PALM_CENTER_LANDMARKS if name in landmarks]
    if not points:
        return None

    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def estimate_hand_size(landmarks: GestureLandmarks) -> float | None:
    if "index_mcp" in landmarks and "pinky_mcp" in landmarks:
        index_mcp = landmarks["index_mcp"]
        pinky_mcp = landmarks["pinky_mcp"]
        return math.hypot(index_mcp[0] - pinky_mcp[0], index_mcp[1] - pinky_mcp[1])

    tracking_point = compute_hand_tracking_point(landmarks)
    wrist = landmarks.get("wrist")
    if wrist is None or tracking_point is None:
        return None

    return math.hypot(wrist[0] - tracking_point[0], wrist[1] - tracking_point[1])


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
    min_detection_points: int = settings.GESTURE_MIN_DETECTION_POINTS,
    swipe_min_span: float = settings.GESTURE_SWIPE_MIN_SPAN,
    circle_min_radius: float = settings.GESTURE_CIRCLE_MIN_RADIUS,
) -> GestureName | None:
    if len(trajectory) < min_detection_points:
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
        and span_x > swipe_min_span
    ):
        return "swipe_right" if dx_total > 0 else "swipe_left"

    if (
        dy_total > down_threshold
        and dy_total > abs(dx_total) * 1.2
        and span_y > swipe_min_span
    ):
        return "swipe_down"

    center_x = mean(xs)
    center_y = mean(ys)
    vectors = [(x - center_x, y - center_y) for x, y in trajectory]
    radii = [math.hypot(x, y) for x, y in vectors]

    if not radii or mean(radii) < circle_min_radius:
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

        observation = self._extract_observation(frame)
        preview_bytes = None
        try:
            ok, jpeg = cv2.imencode(".jpg", frame)
            if ok:
                preview_bytes = jpeg.tobytes()
        except Exception:
            preview_bytes = None

        observation.preview_bytes = preview_bytes
        return observation

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
        smoothing_alpha: float,
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
                observation = self._extract_observation(frame, hands_instance=hands)
                if observation.point is None:
                    continue

                smoothed_point = smooth_point(
                    previous_point=smoothed_point,
                    point=observation.point,
                    alpha=smoothing_alpha,
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
    ) -> GestureObservation:
        hands_instance = hands_instance or self.hands
        if hands_instance is None:
            return GestureObservation(point=None)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_instance.process(rgb)
        if not results.multi_hand_landmarks:
            return GestureObservation(point=None)

        hand_landmarks = results.multi_hand_landmarks[0]
        landmarks = build_hand_landmark_map(hand_landmarks)
        tracking_point = compute_hand_tracking_point(landmarks)
        handedness = None
        if results.multi_handedness:
            handedness = results.multi_handedness[0].classification[0].label.lower()

        return GestureObservation(
            point=tracking_point,
            hand=handedness,
            landmarks=landmarks,
            hand_size=estimate_hand_size(landmarks),
            tracking_source="palm_center",
        )


class GestureService:
    def __init__(
        self,
        adapter_factory: Callable[[], GestureAdapter] | None = None,
        realtime: RealtimeHub | None = None,
        config_repository_factory: Callable[[], ConfigRepository] | None = None,
    ) -> None:
        self.adapter_factory = adapter_factory or MediaPipeHandsAdapter
        self.realtime = realtime or realtime_hub
        self.config_repository_factory = config_repository_factory or ConfigRepository
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._adapter: GestureAdapter | None = None
        self._active_config = GestureConfig()
        self.running = False
        self.camera_index: int | None = None
        self.latest_frame_data_url: str | None = None
        self.smoothed_point: tuple[float, float] | None = None
        self.trajectory: list[tuple[float, float]] = []
        self.last_gesture: GestureName | None = None
        self.last_gesture_at: datetime | None = None
        self.last_gesture_time_by_name: dict[str, float] = {}
        self.last_hand: str | None = None
        self.last_error: str | None = None

    def is_available(self) -> bool:
        try:
            adapter = self.adapter_factory()
            return adapter.is_available()
        except Exception:
            return False

    def reload_config(self) -> GestureConfig:
        try:
            config = self.config_repository_factory().get_gesture_config()
        except Exception as exc:
            logger.warning("Could not reload gesture config, using defaults: %s", exc)
            config = GestureConfig()

        with self._lock:
            self._active_config = config
        return config

    def start(self, camera_index: int = 0) -> dict[str, object]:
        with self._lock:
            if self.running:
                return self.get_status()

            if not self.is_available():
                self.last_error = "Gestenerkennung ist in dieser Umgebung nicht verfuegbar."
                raise GestureServiceError(
                    "Gestenerkennung ist in dieser Umgebung nicht verfuegbar.",
                    status_code=503,
                )

            adapter = self.adapter_factory()
            try:
                adapter.open(camera_index)
            except GestureAdapterError as exc:
                self.last_error = str(exc)
                raise GestureServiceError(str(exc), status_code=503) from exc

            self.reload_config()
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
            try:
                adapter.close()
            except Exception as exc:
                logger.warning("Gesture adapter close failed: %s", exc)
                with self._lock:
                    self.last_error = str(exc)

        with self._lock:
            self.camera_index = None

        return self.get_status()

    def shutdown(self) -> None:
        self.stop()

    def get_status(self) -> dict[str, object]:
        with self._lock:
            return {
                "available": self.is_available(),
                "running": self.running,
                "camera_index": self.camera_index,
                "last_gesture": self.last_gesture,
                "last_gesture_at": self.last_gesture_at,
                "debug_frame_available": self.latest_frame_data_url is not None,
                "last_error": self.last_error,
            }

    def get_frame(self) -> str | None:
        with self._lock:
            return self.latest_frame_data_url

    def process_video(self, video_path: str) -> dict[str, int | list[GestureName]]:
        if not self.is_available():
            with self._lock:
                self.last_error = "Gestenerkennung ist in dieser Umgebung nicht verfuegbar."
            raise GestureServiceError(
                "Gestenerkennung ist in dieser Umgebung nicht verfuegbar.",
                status_code=503,
            )

        if not Path(video_path).exists():
            raise GestureServiceError(
                f"Video nicht gefunden: {video_path}",
                status_code=404,
            )

        active_config = self.reload_config()
        adapter = self.adapter_factory()
        try:
            with self._lock:
                self.last_error = None
            return adapter.process_video(
                video_path,
                classifier=self._detect_gesture,
                smoothing_alpha=active_config.smoothing_alpha,
            )
        except GestureAdapterError as exc:
            with self._lock:
                self.last_error = str(exc)
            raise GestureServiceError(str(exc), status_code=503) from exc

    def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                with self._lock:
                    adapter = self._adapter
                    active_config = self._active_config

                if adapter is None:
                    break

                try:
                    observation = adapter.read()
                except GestureAdapterError as exc:
                    logger.warning("Gesture adapter read failed: %s", exc)
                    with self._lock:
                        self.last_error = str(exc)
                    break

                if observation is None:
                    time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
                    continue

                self._update_preview(observation.preview_bytes)

                if observation.point is None:
                    with self._lock:
                        self.smoothed_point = None
                        self.trajectory.clear()
                    time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
                    continue

                with self._lock:
                    self.last_error = None
                    self.last_hand = observation.hand
                    self.smoothed_point = smooth_point(
                        previous_point=self.smoothed_point,
                        point=observation.point,
                        alpha=active_config.smoothing_alpha,
                    )
                    self.trajectory.append(self.smoothed_point)
                    if len(self.trajectory) > active_config.max_trajectory_points:
                        self.trajectory.pop(0)
                    trajectory_snapshot = list(self.trajectory)

                gesture = self._detect_gesture(trajectory_snapshot)
                if gesture is not None and self._cooldown_elapsed(gesture):
                    detected_at = datetime.now(timezone.utc)
                    with self._lock:
                        self.last_gesture = gesture
                        self.last_gesture_at = detected_at
                    self._publish_gesture_event(gesture=gesture, hand=observation.hand)
        finally:
            with self._lock:
                self.running = False

    def _publish_gesture_event(self, gesture: GestureName, hand: str | None) -> None:
        with self._lock:
            last_gesture_at = self.last_gesture_at

        if last_gesture_at is None:
            return

        self.realtime.publish_from_thread(
            {
                "eventType": "GestureDetected",
                "payload": {
                    "gesture": gesture,
                    "timestamp": last_gesture_at.isoformat(),
                    "source": "camera",
                    "hand": hand,
                },
            }
        )

    def _cooldown_elapsed(self, gesture: GestureName) -> bool:
        now = time.time()
        with self._lock:
            cooldown_seconds = self._active_config.cooldown_seconds
            last_seen = self.last_gesture_time_by_name.get(gesture, 0.0)
            if now - last_seen <= cooldown_seconds:
                return False

            self.last_gesture_time_by_name[gesture] = now
            return True

    def _detect_gesture(
        self,
        trajectory: list[tuple[float, float]],
    ) -> GestureName | None:
        with self._lock:
            active_config = self._active_config

        return detect_gesture_from_trajectory(
            trajectory=trajectory,
            swipe_threshold=active_config.swipe_threshold,
            down_threshold=active_config.down_threshold,
            circle_sweep_min=active_config.circle_sweep_min,
            circle_cv_max=active_config.circle_radius_cv_max,
            min_detection_points=active_config.min_detection_points,
            swipe_min_span=active_config.swipe_min_span,
            circle_min_radius=active_config.circle_min_radius,
        )

    def _update_preview(self, preview_bytes: bytes | None) -> None:
        if preview_bytes is None:
            return

        encoded = base64.b64encode(preview_bytes).decode("ascii")
        with self._lock:
            self.latest_frame_data_url = f"data:image/jpeg;base64,{encoded}"

    def _reset_runtime_state(self) -> None:
        self.latest_frame_data_url = None
        self.smoothed_point = None
        self.trajectory = []
        self.last_gesture = None
        self.last_gesture_at = None
        self.last_hand = None
        self.last_error = None
        self.last_gesture_time_by_name = {}


gesture_service = GestureService()
