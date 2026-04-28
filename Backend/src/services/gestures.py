import base64
import math
import logging
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from core.config import settings
from core.realtime import RealtimeHub, realtime_hub
from repositories.config import ConfigRepository
from schemas.gestures import GestureConfig
from schemas.interactions import InputActionConfig
logger = logging.getLogger(__name__)

from services.gestures_detection import (
    GestureDetectionCandidate,
    GestureDetectionResult,
    GestureFeatures,
    detect_gesture_candidates,
    detect_gesture_from_trajectory,
    detect_gesture_with_confidence,
    extract_gesture_features,
    select_best_gesture_candidate,
)
from services.gestures_tracking import (
    GestureAdapter,
    GestureAdapterError,
    GestureName,
    GestureObservation,
    MediaPipeHandsAdapter,
    TrackedHandObservation,
    build_hand_landmark_map,
    compute_hand_size_scale,
    compute_hand_tracking_point,
    estimate_hand_size,
    smooth_point,
)


class GestureServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class PushGestureState:
    started_at: float
    last_seen_at: float
    emitted_long: bool = False
    max_depth: float = 0.0


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
        self._input_action_config = InputActionConfig()
        self.running = False
        self.camera_index: int | None = None
        self.latest_frame_data_url: str | None = None
        self.smoothed_point: tuple[float, float] | None = None
        self.trajectory: list[tuple[float, float]] = []
        self.hand_size_samples: list[float | None] = []
        self.two_hand_distance_history: list[tuple[float, float]] = []
        self._push_state: PushGestureState | None = None
        self.last_gesture: GestureName | None = None
        self.last_gesture_at: datetime | None = None
        self.last_confidence: float | None = None
        self.last_gesture_time_by_name: dict[str, float] = {}
        self.last_hand: str | None = None
        self.last_tracking_source: str | None = None
        self.last_error: str | None = None

    def is_available(self) -> bool:
        adapter = self.adapter_factory()
        return adapter.is_available()

    def reload_config(self) -> GestureConfig:
        repository = self.config_repository_factory()
        try:
            config = repository.get_gesture_config()
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            logger.warning("Could not reload gesture config, using defaults: %s", exc)
            config = GestureConfig()

        try:
            input_action_config = (
                repository.get_input_action_config()
                if hasattr(repository, "get_input_action_config")
                else InputActionConfig()
            )
        except (AttributeError, OSError, sqlite3.Error, TypeError, ValueError) as exc:
            logger.warning("Could not reload input action config, using defaults: %s", exc)
            input_action_config = InputActionConfig()

        with self._lock:
            self._active_config = config
            self._input_action_config = input_action_config
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
            thread.join(timeout=settings.GESTURE_STOP_JOIN_TIMEOUT_SECONDS)
            if thread.is_alive():
                logger.warning("Gesture thread did not stop within %.2f seconds.", settings.GESTURE_STOP_JOIN_TIMEOUT_SECONDS)
                with self._lock:
                    self.last_error = "Gesten-Thread konnte nicht rechtzeitig beendet werden."

        if adapter is not None:
            try:
                adapter.close()
            except (GestureAdapterError, OSError, RuntimeError, ValueError) as exc:
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
                "last_confidence": self.last_confidence,
                "last_tracking_source": self.last_tracking_source,
                "debug_frame_available": self.latest_frame_data_url is not None,
                "last_error": self.last_error,
            }

    def get_frame(self) -> str | None:
        with self._lock:
            return self.latest_frame_data_url

    def process_video(
        self,
        video_path: str,
    ) -> dict[str, int | list[GestureName] | float | str | None]:
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
                classifier=lambda trajectory, hand_size: self._detect_gesture(
                    trajectory,
                    hand_size=hand_size,
                    tracking_source="palm_center",
                ),
                smoothing_alpha=active_config.smoothing_alpha,
                tracking_source="palm_center",
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
                    observation = self._read_observation_with_retry(adapter)
                except GestureAdapterError:
                    break

                if observation is None:
                    time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
                    continue

                self._update_preview(observation.preview_bytes)
                observed_at = observation.captured_at if observation.captured_at is not None else time.monotonic()

                if observation.point is None:
                    self._reset_sequence_state()
                    with self._lock:
                        self.smoothed_point = None
                        self.trajectory.clear()
                        self.hand_size_samples.clear()
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
                    self.hand_size_samples.append(observation.hand_size)
                    if len(self.trajectory) > active_config.max_trajectory_points:
                        self.trajectory.pop(0)
                        self.hand_size_samples.pop(0)
                    trajectory_snapshot = list(self.trajectory)
                    hand_size_snapshot = self._average_hand_size(self.hand_size_samples)

                detection = self._detect_runtime_gesture(
                    observation=observation,
                    observed_at=observed_at,
                    trajectory=trajectory_snapshot,
                    hand_size=hand_size_snapshot,
                )
                if detection is not None and self._cooldown_elapsed(detection.gesture):
                    detected_at = datetime.now(timezone.utc)
                    with self._lock:
                        self.last_gesture = detection.gesture
                        self.last_gesture_at = detected_at
                        self.last_confidence = detection.confidence
                        self.last_tracking_source = detection.tracking_source
                    self._publish_gesture_event(
                        detection=detection,
                        hand=observation.hand,
                    )
                    self._publish_ui_action_event(
                        detection=detection,
                        hand=observation.hand,
                    )
        finally:
            with self._lock:
                self.running = False

    def _publish_gesture_event(
        self,
        detection: GestureDetectionResult,
        hand: str | None,
    ) -> None:
        with self._lock:
            last_gesture_at = self.last_gesture_at

        if last_gesture_at is None:
            return

        self.realtime.publish_from_thread(
            {
                "eventType": "GestureDetected",
                "payload": {
                    "gesture": detection.gesture,
                    "timestamp": last_gesture_at.isoformat(),
                    "source": "camera",
                    "hand": hand,
                    "confidence": detection.confidence,
                    "tracking_source": detection.tracking_source,
                },
            }
        )

    def _publish_ui_action_event(
        self,
        detection: GestureDetectionResult,
        hand: str | None,
    ) -> None:
        with self._lock:
            last_gesture_at = self.last_gesture_at
            mappings = list(self._input_action_config.mappings)

        if last_gesture_at is None:
            return

        mapping = next(
            (
                item
                for item in mappings
                if item.enabled and item.input_source == "gesture" and item.raw_input == detection.gesture
            ),
            None,
        )
        if mapping is None:
            return

        metadata = {
            **mapping.metadata,
            "confidence": detection.confidence,
            "hand": hand,
            "tracking_source": detection.tracking_source,
        }
        self.realtime.publish_from_thread(
            {
                "eventType": "UIActionRequested",
                "payload": {
                    "action": mapping.action,
                    "timestamp": last_gesture_at.isoformat(),
                    "input_source": "gesture",
                    "raw_input": detection.gesture,
                    "metadata": metadata,
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
        hand_size: float | None = None,
        tracking_source: str | None = None,
    ) -> GestureDetectionResult | None:
        with self._lock:
            active_config = self._active_config

        return detect_gesture_with_confidence(
            trajectory=trajectory,
            swipe_threshold=active_config.swipe_threshold,
            down_threshold=active_config.down_threshold,
            circle_sweep_min=active_config.circle_sweep_min,
            circle_cv_max=active_config.circle_radius_cv_max,
            min_detection_points=active_config.min_detection_points,
            swipe_min_span=active_config.swipe_min_span,
            circle_min_radius=active_config.circle_min_radius,
            min_confidence=active_config.min_confidence,
            hand_size=hand_size,
            hand_size_reference=active_config.hand_size_reference,
            hand_size_scale_min=active_config.hand_size_scale_min,
            hand_size_scale_max=active_config.hand_size_scale_max,
            tracking_source=tracking_source,
            up_threshold=active_config.up_threshold,
        )

    def _detect_runtime_gesture(
        self,
        observation: GestureObservation,
        observed_at: float,
        trajectory: list[tuple[float, float]],
        hand_size: float | None,
    ) -> GestureDetectionResult | None:
        zoom_detection = self._detect_zoom_gesture(observation, observed_at)
        if zoom_detection is not None:
            return zoom_detection

        push_detection = self._detect_push_gesture(observation, observed_at)
        if push_detection is not None:
            return push_detection

        return self._detect_gesture(
            trajectory,
            hand_size=hand_size,
            tracking_source=observation.tracking_source,
        )

    def _detect_push_gesture(
        self,
        observation: GestureObservation,
        observed_at: float,
    ) -> GestureDetectionResult | None:
        with self._lock:
            active_config = self._active_config

        push_depth = self._compute_push_depth(observation)
        pose_valid = self._is_push_pose(observation, active_config.center_tolerance, active_config.push_pose_extension_ratio)
        is_forward = pose_valid and push_depth >= active_config.push_depth_threshold
        is_released = push_depth <= active_config.push_release_threshold

        if is_forward:
            if self._push_state is None:
                self._push_state = PushGestureState(
                    started_at=observed_at,
                    last_seen_at=observed_at,
                    max_depth=push_depth,
                )
                return None

            self._push_state.last_seen_at = observed_at
            self._push_state.max_depth = max(self._push_state.max_depth, push_depth)

            if (
                not self._push_state.emitted_long
                and observed_at - self._push_state.started_at >= active_config.long_click_seconds
            ):
                self._push_state.emitted_long = True
                confidence = min(1.0, self._push_state.max_depth / max(active_config.push_depth_threshold, 1e-6))
                return GestureDetectionResult(
                    gesture="push_click_long",
                    confidence=confidence,
                    tracking_source="index_push",
                )
            return None

        if self._push_state is None:
            return None

        state = self._push_state
        self._push_state = None
        if state.emitted_long:
            return None

        duration = state.last_seen_at - state.started_at
        if pose_valid or is_released:
            if 0.08 <= duration < active_config.long_click_seconds:
                confidence = min(1.0, state.max_depth / max(active_config.push_depth_threshold, 1e-6))
                return GestureDetectionResult(
                    gesture="push_click_short",
                    confidence=confidence,
                    tracking_source="index_push",
                )

        return None

    def _detect_zoom_gesture(
        self,
        observation: GestureObservation,
        observed_at: float,
    ) -> GestureDetectionResult | None:
        with self._lock:
            active_config = self._active_config

        if not observation.hands or len(observation.hands) < 2:
            self.two_hand_distance_history.clear()
            return None

        tracked_hands: list[TrackedHandObservation] = sorted(
            [hand for hand in observation.hands if hand.point is not None],
            key=lambda hand: hand.point[0] if hand.point is not None else float("inf"),
        )
        if len(tracked_hands) < 2:
            self.two_hand_distance_history.clear()
            return None

        left_hand, right_hand = tracked_hands[0], tracked_hands[-1]
        if left_hand.point is None or right_hand.point is None:
            self.two_hand_distance_history.clear()
            return None
        distance = math.hypot(
            right_hand.point[0] - left_hand.point[0],
            right_hand.point[1] - left_hand.point[1],
        )
        self.two_hand_distance_history.append((observed_at, distance))
        while len(self.two_hand_distance_history) > active_config.max_trajectory_points:
            self.two_hand_distance_history.pop(0)

        if len(self.two_hand_distance_history) < active_config.two_hand_min_frames:
            return None

        start_distance = self.two_hand_distance_history[0][1]
        end_distance = self.two_hand_distance_history[-1][1]
        delta = end_distance - start_distance
        threshold = active_config.zoom_distance_delta_threshold

        if start_distance <= active_config.zoom_start_near_distance and delta >= threshold:
            self.two_hand_distance_history.clear()
            return GestureDetectionResult(
                gesture="zoom_out_hands",
                confidence=min(1.0, delta / max(threshold, 1e-6)),
                tracking_source="dual_hand_distance",
            )

        if start_distance >= active_config.zoom_start_far_distance and -delta >= threshold:
            self.two_hand_distance_history.clear()
            return GestureDetectionResult(
                gesture="zoom_in_hands",
                confidence=min(1.0, (-delta) / max(threshold, 1e-6)),
                tracking_source="dual_hand_distance",
            )

        return None

    @staticmethod
    def _compute_push_depth(observation: GestureObservation) -> float:
        if observation.landmark_depths is None:
            return 0.0

        index_tip_depth = observation.landmark_depths.get("index_tip")
        index_mcp_depth = observation.landmark_depths.get("index_mcp")
        if index_tip_depth is None or index_mcp_depth is None:
            return 0.0
        return max(0.0, index_mcp_depth - index_tip_depth)

    @staticmethod
    def _is_push_pose(
        observation: GestureObservation,
        center_tolerance: float,
        extension_ratio: float,
    ) -> bool:
        if observation.landmarks is None or observation.point is None:
            return False

        point_x, point_y = observation.point
        if abs(point_x - 0.5) > center_tolerance or abs(point_y - 0.5) > center_tolerance:
            return False

        landmarks = observation.landmarks
        wrist = landmarks.get("wrist")
        index_tip = landmarks.get("index_tip")
        index_mcp = landmarks.get("index_mcp")
        if wrist is None or index_tip is None or index_mcp is None:
            return False

        def _distance(left: tuple[float, float], right: tuple[float, float]) -> float:
            return math.hypot(left[0] - right[0], left[1] - right[1])

        index_extended = _distance(index_tip, wrist) > _distance(index_mcp, wrist) * extension_ratio
        if not index_extended:
            return False

        folded_checks = 0
        for finger_tip, finger_mcp in (("middle_tip", "middle_mcp"), ("ring_tip", "ring_mcp"), ("pinky_tip", "pinky_mcp")):
            tip = landmarks.get(finger_tip)
            mcp = landmarks.get(finger_mcp)
            if tip is None or mcp is None:
                continue
            if _distance(tip, wrist) <= _distance(mcp, wrist) * 1.12:
                folded_checks += 1

        return folded_checks >= 2

    def _read_observation_with_retry(
        self,
        adapter: GestureAdapter,
    ) -> GestureObservation | None:
        attempts = max(1, settings.GESTURE_READ_RETRY_ATTEMPTS + 1)
        for attempt in range(1, attempts + 1):
            try:
                return adapter.read()
            except GestureAdapterError as exc:
                logger.warning(
                    "Gesture adapter read failed (attempt %s/%s): %s",
                    attempt,
                    attempts,
                    exc,
                )
                with self._lock:
                    self.last_error = str(exc)

                if attempt >= attempts or self._stop_event.is_set():
                    raise

                time.sleep(settings.GESTURE_READ_RETRY_DELAY_SECONDS)

        return None

    @staticmethod
    def _average_hand_size(hand_sizes: list[float | None]) -> float | None:
        available_sizes = [value for value in hand_sizes if value is not None]
        if not available_sizes:
            return None
        return mean(available_sizes)

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
        self.hand_size_samples = []
        self._reset_sequence_state()
        self.last_gesture = None
        self.last_gesture_at = None
        self.last_confidence = None
        self.last_hand = None
        self.last_tracking_source = None
        self.last_error = None
        self.last_gesture_time_by_name = {}

    def _reset_sequence_state(self) -> None:
        self.two_hand_distance_history = []
        self._push_state = None


gesture_service = GestureService()


__all__ = [
    "GestureAdapter",
    "GestureAdapterError",
    "GestureConfig",
    "GestureDetectionCandidate",
    "GestureDetectionResult",
    "GestureFeatures",
    "GestureName",
    "GestureObservation",
    "GestureService",
    "GestureServiceError",
    "TrackedHandObservation",
    "build_hand_landmark_map",
    "compute_hand_size_scale",
    "compute_hand_tracking_point",
    "detect_gesture_candidates",
    "detect_gesture_from_trajectory",
    "detect_gesture_with_confidence",
    "estimate_hand_size",
    "extract_gesture_features",
    "gesture_service",
    "select_best_gesture_candidate",
]
