import base64
import logging
import math
import sqlite3
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, cast

from core.config import settings
from core.realtime import RealtimeHub, realtime_hub
from repositories.config import ConfigRepository
from schemas.calibration import (
    CalibrationAdvisoryRecognition,
    CalibrationCollectedSample,
    GestureCalibrationSamplePayload,
    GestureFingerStateSnapshot,
    GesturePoseSnapshot,
    GesturePushSampleMetrics,
    GestureSequenceArtifact,
    GestureSequenceFrame,
    GestureSequenceProfileSet,
    GestureTemporalWindowSummary,
    GestureTrajectorySummary,
    GestureZoomSampleMetrics,
)
from schemas.gestures import GestureConfig
from schemas.gestures import GestureType
from services.calibration import CalibrationService, calibration_service
from services.gesture.detection import (
    GestureDetectionCandidate,
    GestureDetectionResult,
    GestureFeatures,
    GestureRuntimeAnalysis,
    analyze_runtime_gesture,
    detect_gesture_candidates,
    detect_gesture_from_trajectory,
    detect_gesture_with_confidence,
    extract_gesture_features,
    extract_temporal_gesture_window,
    select_best_gesture_candidate,
)
from services.gesture.push_runtime import (
    PushGestureState,
    detect_push_gesture,
    is_click_pose_candidate,
)
from services.gesture.sequence_features import is_sequence_supported_gesture
from services.gesture.sequence_matcher import GestureSequenceMatcher
from services.gesture.tracking import (
    GestureAdapter,
    GestureAdapterError,
    GestureName,
    GestureObservation,
    HandPoseFeatures,
    MediaPipeHandsAdapter,
    TrackedHandObservation,
    build_hand_landmark_map,
    compute_hand_size_scale,
    compute_hand_tracking_point,
    estimate_hand_size,
    extract_hand_pose_features,
    smooth_point,
)
from services.input.orchestrator import InputOrchestrator, input_orchestrator

logger = logging.getLogger(__name__)


class GestureServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class PendingGestureDetection:
    detection: GestureDetectionResult
    first_seen_at: float
    last_seen_at: float
    settled_at: float | None = None


@dataclass(slots=True)
class CalibrationCaptureFrame:
    observed_at: float
    point: tuple[float, float] | None
    hand_size: float | None
    hand: str | None
    hand_count: int
    tracking_source: str | None
    active_phase: str
    center_distance: float | None
    hand_openness: float | None
    index_extension_ratio: float | None
    push_depth: float | None
    dominant_hand_pose: str | None
    finger_states: dict[str, GestureFingerStateSnapshot] = field(default_factory=dict)
    distance_value: float | None = None
    recognition: GestureDetectionResult | None = None


@dataclass(slots=True)
class ActiveCalibrationCapture:
    session_id: str
    take_id: str
    target_id: str
    trimmed_tail_ms: int = 750
    frames: list[CalibrationCaptureFrame] = field(default_factory=list)


@dataclass(slots=True)
class TrajectoryLifecycleManager:
    smoothed_point: tuple[float, float] | None = None
    trajectory: list[tuple[float, float]] = field(default_factory=list)
    trajectory_timestamps: list[float] = field(default_factory=list)
    hand_size_samples: list[float | None] = field(default_factory=list)
    hand_count_samples: list[int] = field(default_factory=list)
    hand_openness_samples: list[float | None] = field(default_factory=list)
    index_extension_ratio_samples: list[float | None] = field(default_factory=list)
    push_depth_samples: list[float | None] = field(default_factory=list)
    center_distance_samples: list[float | None] = field(default_factory=list)
    active_phase_samples: list[str | None] = field(default_factory=list)
    two_hand_distance_history: list[tuple[float, float]] = field(default_factory=list)
    post_fire_until: float | None = None

    def reset_all(self) -> None:
        self.reset_motion_window(clear_post_fire=True)
        self.clear_two_hand_history()

    def reset_motion_window(self, *, clear_post_fire: bool = False) -> None:
        self.smoothed_point = None
        self.trajectory = []
        self.trajectory_timestamps = []
        self.hand_size_samples = []
        self.hand_count_samples = []
        self.hand_openness_samples = []
        self.index_extension_ratio_samples = []
        self.push_depth_samples = []
        self.center_distance_samples = []
        self.active_phase_samples = []
        if clear_post_fire:
            self.post_fire_until = None

    def begin_post_fire_grace(self, observed_at: float, grace_seconds: float) -> None:
        self.reset_motion_window(clear_post_fire=True)
        if grace_seconds > 0:
            self.post_fire_until = observed_at + grace_seconds

    def in_post_fire_grace(self, observed_at: float) -> bool:
        if self.post_fire_until is None:
            return False
        if observed_at >= self.post_fire_until:
            self.post_fire_until = None
            return False
        return True

    def append_point(
        self,
        *,
        point: tuple[float, float],
        observed_at: float,
        hand_size: float | None,
        hand_count: int,
        pose_features: HandPoseFeatures | None,
        smoothing_alpha: float,
        max_points: int,
    ) -> tuple[float, float] | None:
        if self.in_post_fire_grace(observed_at):
            return None

        self.smoothed_point = smooth_point(
            previous_point=self.smoothed_point,
            point=point,
            alpha=smoothing_alpha,
        )
        self.trajectory.append(self.smoothed_point)
        self.trajectory_timestamps.append(observed_at)
        self.hand_size_samples.append(hand_size)
        self.hand_count_samples.append(max(0, hand_count))
        self.hand_openness_samples.append(
            None if pose_features is None else pose_features.hand_openness
        )
        self.index_extension_ratio_samples.append(
            None if pose_features is None else pose_features.index_extension_ratio
        )
        self.push_depth_samples.append(
            None if pose_features is None else pose_features.push_depth
        )
        self.center_distance_samples.append(
            None if pose_features is None else pose_features.center_distance
        )
        self.active_phase_samples.append(None)
        while len(self.trajectory) > max_points:
            self.trajectory.pop(0)
            self.trajectory_timestamps.pop(0)
            self.hand_size_samples.pop(0)
            self.hand_count_samples.pop(0)
            self.hand_openness_samples.pop(0)
            self.index_extension_ratio_samples.pop(0)
            self.push_depth_samples.pop(0)
            self.center_distance_samples.pop(0)
            self.active_phase_samples.pop(0)
        return self.smoothed_point

    def set_last_active_phase(self, active_phase: str | None) -> None:
        if self.active_phase_samples:
            self.active_phase_samples[-1] = active_phase

    def average_hand_size(self) -> float | None:
        available_sizes = [
            value for value in self.hand_size_samples if value is not None
        ]
        if not available_sizes:
            return None
        return mean(available_sizes)

    def copy_motion_snapshot(
        self,
    ) -> tuple[list[tuple[float, float]], list[float], float | None]:
        return (
            list(self.trajectory),
            list(self.trajectory_timestamps),
            self.average_hand_size(),
        )

    def copy_sequence_channel_snapshot(self) -> dict[str, list[float | None]]:
        return {
            "hand_openness": list(self.hand_openness_samples),
            "index_extension_ratio": list(self.index_extension_ratio_samples),
            "push_depth": list(self.push_depth_samples),
            "center_distance": list(self.center_distance_samples),
        }

    def copy_active_phase_snapshot(self) -> list[str | None]:
        return list(self.active_phase_samples)

    def latest_two_hand_distance(self) -> float | None:
        return (
            self.two_hand_distance_history[-1][1]
            if self.two_hand_distance_history
            else None
        )

    def clear_two_hand_history(self) -> None:
        self.two_hand_distance_history = []

    def copy_two_hand_history(self) -> list[tuple[float, float]]:
        return list(self.two_hand_distance_history)

    def append_two_hand_distance(
        self, observed_at: float, distance: float, max_points: int
    ) -> list[tuple[float, float]]:
        self.two_hand_distance_history.append((observed_at, distance))
        while len(self.two_hand_distance_history) > max_points:
            self.two_hand_distance_history.pop(0)
        return list(self.two_hand_distance_history)

    def select_single_hand_trajectory(
        self,
        *,
        observed_at: float,
        cooldown_seconds: float,
        min_detection_points: int,
    ) -> list[tuple[float, float]]:
        window_seconds = min(1.5, max(0.9, cooldown_seconds * 1.25))
        window_start = observed_at - window_seconds

        if (
            not self.trajectory
            or len(self.trajectory) != len(self.trajectory_timestamps)
            or len(self.trajectory) != len(self.hand_count_samples)
        ):
            start_index = 0
            for index, timestamp in enumerate(self.trajectory_timestamps):
                if timestamp >= window_start:
                    start_index = index
                    break
            else:
                start_index = max(0, len(self.trajectory) - min_detection_points)

            max_start = max(0, len(self.trajectory) - min_detection_points)
            start_index = min(start_index, max_start)
            return self.trajectory[start_index:]

        end_index = len(self.trajectory) - 1
        if self.hand_count_samples[end_index] != 1:
            return []

        last_multi_hand_index = -1
        for index in range(end_index, -1, -1):
            if self.hand_count_samples[index] != 1:
                last_multi_hand_index = index
                break

        start_index = 0
        for index, timestamp in enumerate(self.trajectory_timestamps[: end_index + 1]):
            if timestamp >= window_start:
                start_index = index
                break
        else:
            start_index = max(0, (end_index + 1) - min_detection_points)

        start_index = max(start_index, last_multi_hand_index + 1)
        if (end_index + 1) - start_index < min_detection_points:
            return []
        return self.trajectory[start_index : end_index + 1]


class GestureService:
    def __init__(
        self,
        adapter_factory: Callable[[], GestureAdapter] | None = None,
        realtime: RealtimeHub | None = None,
        config_repository_factory: Callable[[], ConfigRepository] | None = None,
        calibration_runtime: CalibrationService | None = None,
        input_orchestrator_service: InputOrchestrator | None = None,
    ) -> None:
        self.adapter_factory = adapter_factory or MediaPipeHandsAdapter
        self.realtime = realtime or realtime_hub
        self.config_repository_factory = config_repository_factory or ConfigRepository
        self.calibration_runtime = calibration_runtime or calibration_service
        self.input_orchestrator = input_orchestrator_service or InputOrchestrator(
            realtime=self.realtime,
            config_repository_factory=self.config_repository_factory,
        )
        self._lifecycle = TrajectoryLifecycleManager()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._adapter: GestureAdapter | None = None
        self._active_config = GestureConfig()
        self._active_sequence_profile_set: GestureSequenceProfileSet | None = None
        self.running = False
        self.camera_index: int | None = None
        self.camera_name: str | None = None
        self._preferred_camera_index: int | None = None
        self.latest_frame_data_url: str | None = None
        self.latest_frame_captured_at: datetime | None = None
        self._push_state: PushGestureState | None = None
        self._pending_gesture: PendingGestureDetection | None = None
        self._last_detectable_observation: GestureObservation | None = None
        self.last_gesture: GestureName | None = None
        self.last_gesture_at: datetime | None = None
        self.last_confidence: float | None = None
        self.last_gesture_time_by_name: dict[str, float] = {}
        self.last_hand: str | None = None
        self.last_tracking_source: str | None = None
        self.last_tracking_quality: float | None = None
        self.last_active_phase: str | None = None
        self.last_candidate_scores: dict[str, float] = {}
        self.last_sequence_scores: dict[str, float] = {}
        self.last_sequence_distances: dict[str, float] = {}
        self.last_sequence_margins: dict[str, float] = {}
        self.last_sequence_profile_ids: dict[str, str] = {}
        self.last_reject_reason: str | None = None
        self.last_spec_id: str | None = None
        self.last_dominant_hand_pose: str | None = None
        self.last_primitive_hits: dict[str, float] = {}
        self.last_error: str | None = None
        self._active_calibration_capture: ActiveCalibrationCapture | None = None
        self._last_landmark_broadcast: float = 0.0

    @property
    def smoothed_point(self) -> tuple[float, float] | None:
        return self._lifecycle.smoothed_point

    @smoothed_point.setter
    def smoothed_point(self, value: tuple[float, float] | None) -> None:
        self._lifecycle.smoothed_point = value

    @property
    def trajectory(self) -> list[tuple[float, float]]:
        return self._lifecycle.trajectory

    @trajectory.setter
    def trajectory(self, value: list[tuple[float, float]]) -> None:
        self._lifecycle.trajectory = list(value)

    @property
    def trajectory_timestamps(self) -> list[float]:
        return self._lifecycle.trajectory_timestamps

    @trajectory_timestamps.setter
    def trajectory_timestamps(self, value: list[float]) -> None:
        self._lifecycle.trajectory_timestamps = list(value)

    @property
    def hand_size_samples(self) -> list[float | None]:
        return self._lifecycle.hand_size_samples

    @hand_size_samples.setter
    def hand_size_samples(self, value: list[float | None]) -> None:
        self._lifecycle.hand_size_samples = list(value)

    @property
    def two_hand_distance_history(self) -> list[tuple[float, float]]:
        return self._lifecycle.two_hand_distance_history

    @two_hand_distance_history.setter
    def two_hand_distance_history(self, value: list[tuple[float, float]]) -> None:
        self._lifecycle.two_hand_distance_history = list(value)

    def is_available(self) -> bool:
        adapter = self.adapter_factory()
        return adapter.is_available()

    def list_camera_devices(self) -> list[dict[str, object]]:
        adapter = self.adapter_factory()
        if hasattr(adapter, "list_available_cameras"):
            try:
                return list(getattr(adapter, "list_available_cameras")())
            except (GestureAdapterError, OSError, RuntimeError, ValueError, TypeError):
                return []
        return []

    def reload_config(self) -> GestureConfig:
        repository = self.config_repository_factory()
        try:
            config = repository.get_gesture_config()
            sequence_profile_getter = getattr(
                repository,
                "get_active_gesture_sequence_profile_set",
                None,
            )
            sequence_profile_set = (
                sequence_profile_getter() if callable(sequence_profile_getter) else None
            )
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            logger.warning("Could not reload gesture config, using defaults: %s", exc)
            config = GestureConfig()
            sequence_profile_set = None
        self.input_orchestrator.reload_config()

        with self._lock:
            self._active_config = config
            self._active_sequence_profile_set = sequence_profile_set
        return config

    def start(self, camera_index: int = 0) -> dict[str, object]:
        with self._lock:
            if self.running:
                return self.get_status()

            if not self.is_available():
                self.last_error = (
                    "Gestenerkennung ist in dieser Umgebung nicht verfuegbar."
                )
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
            resolved_camera_index = cast(
                int | None, getattr(adapter, "camera_index", camera_index)
            )
            if resolved_camera_index is None:
                resolved_camera_index = camera_index
            self._adapter = adapter
            self.camera_index = resolved_camera_index
            self.camera_name = cast(
                str | None, getattr(adapter, "camera_name", None)
            ) or self._resolve_camera_name(resolved_camera_index)
            self._preferred_camera_index = resolved_camera_index
            self.running = True
            self.last_error = None
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
                logger.warning(
                    "Gesture thread did not stop within %.2f seconds.",
                    settings.GESTURE_STOP_JOIN_TIMEOUT_SECONDS,
                )
                with self._lock:
                    self.last_error = (
                        "Gesten-Thread konnte nicht rechtzeitig beendet werden."
                    )

        if adapter is not None:
            try:
                adapter.close()
            except (GestureAdapterError, OSError, RuntimeError, ValueError) as exc:
                logger.warning("Gesture adapter close failed: %s", exc)
                with self._lock:
                    self.last_error = str(exc)

        with self._lock:
            self.camera_index = None
            self.camera_name = None
            self._active_calibration_capture = None

        return self.get_status()

    def shutdown(self) -> None:
        self.stop()

    def get_status(self) -> dict[str, object]:
        with self._lock:
            active_config = self._active_config
            return {
                "available": self.is_available(),
                "running": self.running,
                "camera_index": self.camera_index,
                "camera_name": self.camera_name,
                "last_gesture": self.last_gesture,
                "last_gesture_at": self.last_gesture_at,
                "last_confidence": self.last_confidence,
                "last_tracking_source": self.last_tracking_source,
                "tracking_quality": self.last_tracking_quality,
                "active_phase": self.last_active_phase,
                "candidate_scores": self.last_candidate_scores,
                "sequence_scores": self.last_sequence_scores,
                "sequence_distances": self.last_sequence_distances,
                "sequence_margins": self.last_sequence_margins,
                "sequence_profile_ids": self.last_sequence_profile_ids,
                "sequence_shadow_mode": active_config.sequence_shadow_mode,
                "sequence_matching_enabled": active_config.sequence_matching_enabled,
                "reject_reason": self.last_reject_reason,
                "spec_id": self.last_spec_id,
                "dominant_hand_pose": self.last_dominant_hand_pose,
                "primitive_hits": self.last_primitive_hits,
                "debug_frame_available": self.latest_frame_data_url is not None,
                "last_error": self.last_error,
            }

    def get_preferred_camera_index(self) -> int | None:
        with self._lock:
            preferred_camera_index = self._preferred_camera_index

        if preferred_camera_index is not None:
            return preferred_camera_index

        try:
            repository = self.config_repository_factory()
            active_profile_getter = getattr(
                repository, "get_active_command_profile", None
            )
            if callable(active_profile_getter):
                active_profile = active_profile_getter()
                device_preferences = getattr(active_profile, "device_preferences", None)
                gesture_camera_index = getattr(
                    device_preferences, "gesture_camera_index", None
                )
                if isinstance(gesture_camera_index, int):
                    return gesture_camera_index
        except (AttributeError, OSError, sqlite3.Error, TypeError, ValueError):
            return None

        return None

    def get_frame(self) -> dict[str, object] | None:
        with self._lock:
            if self.latest_frame_data_url is None:
                return None

            captured_at = self.latest_frame_captured_at
            frame_age_ms = None
            if captured_at is not None:
                frame_age_ms = max(
                    0,
                    int(
                        (datetime.now(timezone.utc) - captured_at).total_seconds()
                        * 1000
                    ),
                )

            return {
                "image": self.latest_frame_data_url,
                "captured_at": captured_at,
                "frame_age_ms": frame_age_ms,
            }

    def begin_calibration_take_capture(
        self,
        *,
        session_id: str,
        take_id: str,
        target_id: str,
        trimmed_tail_ms: int = 750,
    ) -> None:
        with self._lock:
            self._active_calibration_capture = ActiveCalibrationCapture(
                session_id=session_id,
                take_id=take_id,
                target_id=target_id,
                trimmed_tail_ms=trimmed_tail_ms,
            )

    def cancel_calibration_take_capture(
        self, session_id: str | None = None, take_id: str | None = None
    ) -> None:
        with self._lock:
            active_capture = self._active_calibration_capture
            if active_capture is None:
                return
            if session_id is not None and active_capture.session_id != session_id:
                return
            if take_id is not None and active_capture.take_id != take_id:
                return
            self._active_calibration_capture = None

    def stop_calibration_take_capture(
        self,
        *,
        session_id: str,
        take_id: str,
        target_id: str,
    ) -> tuple[CalibrationCollectedSample, CalibrationAdvisoryRecognition | None]:
        with self._lock:
            active_capture = self._active_calibration_capture
            if (
                active_capture is None
                or active_capture.session_id != session_id
                or active_capture.take_id != take_id
            ):
                raise GestureServiceError(
                    "Kein aktiver Kalibrierungs-Take vorhanden.", status_code=409
                )
            frames = list(active_capture.frames)
            trimmed_tail_ms = active_capture.trimmed_tail_ms
            self._active_calibration_capture = None

        trimmed_frames = self._trim_calibration_frames(frames, trimmed_tail_ms)
        if not trimmed_frames:
            raise GestureServiceError(
                "Nach dem serverseitigen Tail-Trim blieb kein verwertbarer Take uebrig.",
                status_code=422,
            )

        return self._build_source_of_truth_take_sample(
            target_id=target_id,
            take_id=take_id,
            frames=trimmed_frames,
        )

    def _append_active_calibration_capture_frame(
        self,
        *,
        observation: GestureObservation,
        analysis: GestureRuntimeAnalysis,
        detection: GestureDetectionResult | None,
        observed_at: float,
    ) -> None:
        with self._lock:
            active_capture = self._active_calibration_capture
        if active_capture is None:
            return

        pose_features = extract_hand_pose_features(observation)
        distance_value = self._lifecycle.latest_two_hand_distance()
        finger_states: dict[str, GestureFingerStateSnapshot] = {}
        if observation.landmarks is not None and pose_features is not None:
            landmark_map = (
                observation.landmarks
                if isinstance(observation.landmarks, dict)
                else build_hand_landmark_map(observation.landmarks)
            )
            for finger_name, finger_state in pose_features.finger_states.items():
                tip_name = f"{finger_name}_tip"
                tip_point = landmark_map.get(tip_name)
                palm_point = landmark_map.get("wrist")
                tip_distance = None
                if tip_point is not None and palm_point is not None:
                    tip_distance = math.hypot(
                        tip_point[0] - palm_point[0], tip_point[1] - palm_point[1]
                    )
                finger_states[finger_name] = GestureFingerStateSnapshot(
                    extended_score=finger_state.extended_score,
                    curled_score=finger_state.curled_score,
                    spread_score=finger_state.spread_score,
                    tip_depth_relative=finger_state.tip_depth_relative,
                    tip_to_palm_distance=tip_distance,
                    label=finger_state.label,
                )

        with self._lock:
            if self._active_calibration_capture is None:
                return
            self._active_calibration_capture.frames.append(
                CalibrationCaptureFrame(
                    observed_at=observed_at,
                    point=observation.point,
                    hand_size=observation.hand_size,
                    hand=observation.hand,
                    hand_count=(
                        len(observation.hands)
                        if observation.hands
                        else (1 if observation.point is not None else 0)
                    ),
                    tracking_source=observation.tracking_source,
                    active_phase=analysis.active_phase,
                    center_distance=(
                        pose_features.center_distance
                        if pose_features is not None
                        else None
                    ),
                    hand_openness=(
                        pose_features.hand_openness
                        if pose_features is not None
                        else None
                    ),
                    index_extension_ratio=(
                        pose_features.index_extension_ratio
                        if pose_features is not None
                        else None
                    ),
                    push_depth=(
                        pose_features.push_depth if pose_features is not None else None
                    ),
                    dominant_hand_pose=analysis.dominant_hand_pose,
                    finger_states=finger_states,
                    distance_value=distance_value,
                    recognition=detection or analysis.detection,
                )
            )

    @staticmethod
    def _trim_calibration_frames(
        frames: list[CalibrationCaptureFrame],
        trimmed_tail_ms: int,
    ) -> list[CalibrationCaptureFrame]:
        if not frames:
            return []
        if trimmed_tail_ms <= 0:
            return frames
        end_observed_at = frames[-1].observed_at
        trim_threshold = end_observed_at - (trimmed_tail_ms / 1000.0)
        trimmed = [frame for frame in frames if frame.observed_at <= trim_threshold]
        return trimmed or frames[:1]

    def _build_source_of_truth_take_sample(
        self,
        *,
        target_id: str,
        take_id: str,
        frames: list[CalibrationCaptureFrame],
    ) -> tuple[CalibrationCollectedSample, CalibrationAdvisoryRecognition | None]:
        with self._lock:
            active_config = self._active_config

        points = [frame.point for frame in frames if frame.point is not None]
        trajectory = [point for point in points if point is not None]
        hand_sizes = [
            frame.hand_size for frame in frames if frame.hand_size is not None
        ]
        hand_size = mean(hand_sizes) if hand_sizes else None
        hand_size_scale = compute_hand_size_scale(
            hand_size=hand_size,
            hand_size_reference=active_config.hand_size_reference,
            hand_size_scale_min=active_config.hand_size_scale_min,
            hand_size_scale_max=active_config.hand_size_scale_max,
        )
        duration_seconds = (
            max(0.0, frames[-1].observed_at - frames[0].observed_at)
            if len(frames) >= 2
            else 0.0
        )

        trajectory_summary = None
        if trajectory:
            features = extract_gesture_features(
                trajectory=trajectory,
                min_detection_points=max(
                    2, min(active_config.min_detection_points, len(trajectory))
                ),
                hand_size=hand_size,
                hand_size_reference=active_config.hand_size_reference,
                hand_size_scale_min=active_config.hand_size_scale_min,
                hand_size_scale_max=active_config.hand_size_scale_max,
            )
            if features is not None:
                trajectory_summary = GestureTrajectorySummary(
                    point_count=len(trajectory),
                    dx_total=features.dx_total,
                    dy_total=features.dy_total,
                    span_x=features.span_x,
                    span_y=features.span_y,
                    radius_mean=features.radius_mean,
                    radius_cv=features.radius_cv,
                    total_sweep=features.total_sweep,
                )

        push_depths = [
            frame.push_depth for frame in frames if frame.push_depth is not None
        ]
        center_distances = [
            frame.center_distance
            for frame in frames
            if frame.center_distance is not None
        ]
        index_extension_ratios = [
            frame.index_extension_ratio
            for frame in frames
            if frame.index_extension_ratio is not None
        ]
        distance_values = [
            frame.distance_value for frame in frames if frame.distance_value is not None
        ]

        push_metrics = None
        if target_id in {"push_click_short", "push_click_long"}:
            push_metrics = GesturePushSampleMetrics(
                pose_valid=bool(push_depths or index_extension_ratios),
                forward_depth=max(push_depths) if push_depths else 0.0,
                release_depth=push_depths[-1] if push_depths else 0.0,
                hold_duration_seconds=(
                    duration_seconds if target_id == "push_click_long" else None
                ),
                max_depth=max(push_depths) if push_depths else None,
            )

        zoom_metrics = None
        if target_id in {"zoom_out_hands", "zoom_in_hands"} and distance_values:
            zoom_metrics = GestureZoomSampleMetrics(
                start_distance=distance_values[0],
                end_distance=distance_values[-1],
                delta_distance=distance_values[-1] - distance_values[0],
                frame_count=len(distance_values),
            )

        advisory_recognition = self._select_advisory_recognition(frames)
        most_common_hand = self._most_common_non_null(frame.hand for frame in frames)
        tracking_source = self._most_common_non_null(
            frame.tracking_source for frame in frames
        )
        last_frame_with_pose = next(
            (
                frame
                for frame in reversed(frames)
                if frame.center_distance is not None or frame.push_depth is not None
            ),
            None,
        )

        payload = GestureCalibrationSamplePayload(
            gesture=cast(Any, target_id),
            confidence=(
                advisory_recognition.confidence
                if advisory_recognition is not None
                and advisory_recognition.confidence is not None
                else 0.0
            ),
            tracking_source=tracking_source,
            hand=most_common_hand,
            duration_seconds=duration_seconds,
            hand_size=hand_size,
            hand_size_scale=hand_size_scale,
            trajectory=trajectory_summary,
            push=push_metrics,
            zoom=zoom_metrics,
            pose=(
                GesturePoseSnapshot(
                    center_distance=last_frame_with_pose.center_distance or 0.0,
                    hand_openness=last_frame_with_pose.hand_openness or 0.0,
                    index_extension_ratio=last_frame_with_pose.index_extension_ratio
                    or 0.0,
                    push_depth=last_frame_with_pose.push_depth or 0.0,
                    dominant_hand_pose=last_frame_with_pose.dominant_hand_pose,
                    finger_states=last_frame_with_pose.finger_states,
                )
                if last_frame_with_pose is not None
                else None
            ),
            temporal=self._build_take_temporal_summary(frames, trajectory),
            sequence=self._build_sequence_artifact_from_capture_frames(
                frames=frames,
                hand_size=hand_size,
            ),
            feature_windows={
                "recognized_target": (
                    advisory_recognition.recognized_target_id
                    if advisory_recognition is not None
                    else None
                ),
                "recognized_confidence": (
                    advisory_recognition.confidence
                    if advisory_recognition is not None
                    else None
                ),
                "center_distance": mean(center_distances) if center_distances else 0.0,
                "index_extension_ratio": (
                    mean(index_extension_ratios) if index_extension_ratios else 0.0
                ),
            },
        )

        sample = CalibrationCollectedSample(
            sample_id=f"calibration-take-{take_id}",
            modality="gesture",
            target_id=target_id,
            collected_at=datetime.now(timezone.utc),
            gesture_payload=payload,
        )
        return sample, advisory_recognition

    @staticmethod
    def _select_sequence_anchor_index(
        *,
        active_phases: list[str | None],
        has_points: list[bool] | None = None,
    ) -> int:
        stable_phases = {"preparing", "holding", "committing"}
        for index, phase in enumerate(active_phases):
            if has_points is not None and (
                index >= len(has_points) or not has_points[index]
            ):
                continue
            if phase in stable_phases:
                return index
        if has_points is not None:
            for index, has_point in enumerate(has_points):
                if has_point:
                    return index
        else:
            for index in range(len(active_phases)):
                return index
        return 0

    @staticmethod
    def _build_sequence_frames(
        *,
        points: list[tuple[float, float]],
        timestamps: list[float],
        scale: float,
        hand_openness: list[float | None] | None = None,
        index_extension_ratios: list[float | None] | None = None,
        push_depths: list[float | None] | None = None,
        center_distances: list[float | None] | None = None,
        distance_values: list[float | None] | None = None,
        active_phases: list[str | None] | None = None,
    ) -> list[GestureSequenceFrame]:
        frames: list[GestureSequenceFrame] = []
        if not points or len(points) != len(timestamps):
            return frames

        origin_x, origin_y = points[0]
        anchor_time = timestamps[0]
        previous_x: float | None = None
        previous_y: float | None = None
        previous_t: float | None = None

        for index, (point, timestamp) in enumerate(zip(points, timestamps)):
            relative_t = max(0.0, timestamp - anchor_time)
            local_x = (point[0] - origin_x) / scale
            local_y = (point[1] - origin_y) / scale
            velocity_x = None
            velocity_y = None
            if previous_t is not None:
                dt = max(timestamp - previous_t, 1e-6)
                velocity_x = (local_x - (previous_x or 0.0)) / dt
                velocity_y = (local_y - (previous_y or 0.0)) / dt

            frames.append(
                GestureSequenceFrame(
                    t=relative_t,
                    x=local_x,
                    y=local_y,
                    velocity_x=velocity_x,
                    velocity_y=velocity_y,
                    hand_openness=(
                        hand_openness[index]
                        if hand_openness is not None and index < len(hand_openness)
                        else None
                    ),
                    index_extension_ratio=(
                        index_extension_ratios[index]
                        if index_extension_ratios is not None
                        and index < len(index_extension_ratios)
                        else None
                    ),
                    push_depth=(
                        push_depths[index]
                        if push_depths is not None and index < len(push_depths)
                        else None
                    ),
                    center_distance=(
                        center_distances[index]
                        if center_distances is not None
                        and index < len(center_distances)
                        else None
                    ),
                    distance_value=(
                        distance_values[index]
                        if distance_values is not None and index < len(distance_values)
                        else None
                    ),
                    active_phase=(
                        active_phases[index]
                        if active_phases is not None and index < len(active_phases)
                        else None
                    ),
                )
            )

            previous_x = local_x
            previous_y = local_y
            previous_t = timestamp

        return frames

    def _build_sequence_artifact_from_capture_frames(
        self,
        *,
        frames: list[CalibrationCaptureFrame],
        hand_size: float | None,
    ) -> GestureSequenceArtifact | None:
        indexed_frames = [
            (index, frame)
            for index, frame in enumerate(frames)
            if frame.point is not None
        ]
        if not indexed_frames:
            return None

        anchor_index = self._select_sequence_anchor_index(
            active_phases=[frame.active_phase for frame in frames],
            has_points=[frame.point is not None for frame in frames],
        )
        trimmed = [item for item in indexed_frames if item[0] >= anchor_index]
        if not trimmed:
            trimmed = indexed_frames
            anchor_index = indexed_frames[0][0]

        points = [frame.point for _, frame in trimmed if frame.point is not None]
        timestamps = [
            frame.observed_at for _, frame in trimmed if frame.point is not None
        ]
        sequence_frames = [frame for _, frame in trimmed if frame.point is not None]
        if not points or not timestamps:
            return None

        scale = hand_size if hand_size is not None and hand_size > 0 else 1.0
        frames_payload = self._build_sequence_frames(
            points=points,
            timestamps=timestamps,
            scale=scale,
            hand_openness=[frame.hand_openness for frame in sequence_frames],
            index_extension_ratios=[
                frame.index_extension_ratio for frame in sequence_frames
            ],
            push_depths=[frame.push_depth for frame in sequence_frames],
            center_distances=[frame.center_distance for frame in sequence_frames],
            distance_values=[frame.distance_value for frame in sequence_frames],
            active_phases=[frame.active_phase for frame in sequence_frames],
        )
        origin_x, origin_y = points[0]
        return GestureSequenceArtifact(
            point_count=len(points),
            frame_count=len(frames_payload),
            anchor_index=anchor_index,
            anchor_phase=sequence_frames[0].active_phase if sequence_frames else None,
            origin_x=origin_x,
            origin_y=origin_y,
            normalized_by_hand_size=hand_size is not None and hand_size > 0,
            frames=frames_payload,
        )

    def _build_sequence_artifact_from_runtime_window(
        self,
        *,
        trajectory: list[tuple[float, float]],
        trajectory_timestamps: list[float],
        hand_size: float | None,
        hand_openness: list[float | None] | None = None,
        index_extension_ratios: list[float | None] | None = None,
        push_depths: list[float | None] | None = None,
        center_distances: list[float | None] | None = None,
        active_phases: list[str | None] | None = None,
    ) -> GestureSequenceArtifact | None:
        if not trajectory or len(trajectory) != len(trajectory_timestamps):
            return None

        anchor_index = 0
        if active_phases:
            anchor_index = self._select_sequence_anchor_index(
                active_phases=active_phases[: len(trajectory)],
            )

        trimmed_trajectory = trajectory[anchor_index:]
        trimmed_timestamps = trajectory_timestamps[anchor_index:]
        trimmed_hand_openness = (
            hand_openness[anchor_index:] if hand_openness is not None else None
        )
        trimmed_index_extension_ratios = (
            index_extension_ratios[anchor_index:]
            if index_extension_ratios is not None
            else None
        )
        trimmed_push_depths = (
            push_depths[anchor_index:] if push_depths is not None else None
        )
        trimmed_center_distances = (
            center_distances[anchor_index:] if center_distances is not None else None
        )
        trimmed_active_phases = (
            active_phases[anchor_index:] if active_phases is not None else None
        )
        if not trimmed_trajectory or not trimmed_timestamps:
            return None

        scale = hand_size if hand_size is not None and hand_size > 0 else 1.0
        frames_payload = self._build_sequence_frames(
            points=trimmed_trajectory,
            timestamps=trimmed_timestamps,
            scale=scale,
            hand_openness=trimmed_hand_openness,
            index_extension_ratios=trimmed_index_extension_ratios,
            push_depths=trimmed_push_depths,
            center_distances=trimmed_center_distances,
            active_phases=trimmed_active_phases,
        )
        origin_x, origin_y = trimmed_trajectory[0]
        return GestureSequenceArtifact(
            point_count=len(trimmed_trajectory),
            frame_count=len(frames_payload),
            anchor_index=anchor_index,
            anchor_phase=trimmed_active_phases[0] if trimmed_active_phases else None,
            origin_x=origin_x,
            origin_y=origin_y,
            normalized_by_hand_size=hand_size is not None and hand_size > 0,
            frames=frames_payload,
        )

    def _slice_runtime_sequence_channels(
        self, point_count: int
    ) -> dict[str, list[float | None]]:
        with self._lock:
            channel_snapshot = self._lifecycle.copy_sequence_channel_snapshot()
        if point_count <= 0:
            return {name: [] for name in channel_snapshot}
        return {
            name: values[-point_count:] if len(values) >= point_count else list(values)
            for name, values in channel_snapshot.items()
        }

    def _slice_runtime_sequence_active_phases(
        self, point_count: int
    ) -> list[str | None]:
        with self._lock:
            active_phase_snapshot = self._lifecycle.copy_active_phase_snapshot()
        if point_count <= 0:
            return []
        return (
            active_phase_snapshot[-point_count:]
            if len(active_phase_snapshot) >= point_count
            else list(active_phase_snapshot)
        )

    def _match_runtime_sequence_window(
        self,
        *,
        candidate_gestures: set[GestureType],
        trajectory: list[tuple[float, float]],
        trajectory_timestamps: list[float],
        hand_size: float | None,
        sequence_channels: dict[str, list[float | None]],
        active_phases: list[str | None],
    ) -> tuple[
        dict[str, float],
        dict[str, float],
        dict[str, float],
        dict[str, str],
    ]:
        with self._lock:
            active_config = self._active_config
            sequence_profile_set = self._active_sequence_profile_set

        if (
            not candidate_gestures
            or sequence_profile_set is None
            or (
                not active_config.sequence_shadow_mode
                and not active_config.sequence_matching_enabled
            )
        ):
            return {}, {}, {}, {}

        artifact = self._build_sequence_artifact_from_runtime_window(
            trajectory=trajectory,
            trajectory_timestamps=trajectory_timestamps,
            hand_size=hand_size,
            hand_openness=sequence_channels.get("hand_openness"),
            index_extension_ratios=sequence_channels.get("index_extension_ratio"),
            push_depths=sequence_channels.get("push_depth"),
            center_distances=sequence_channels.get("center_distance"),
            active_phases=active_phases,
        )
        if artifact is None:
            return {}, {}, {}, {}

        matcher = GestureSequenceMatcher(sequence_profile_set)
        matches = matcher.match_artifact(artifact, gestures=candidate_gestures)
        return (
            {match.gesture: match.score for match in matches},
            {match.gesture: match.distance for match in matches},
            {
                match.gesture: match.margin
                for match in matches
                if match.margin is not None
            },
            {match.gesture: match.profile_id for match in matches},
        )

    @staticmethod
    def _most_common_non_null(
        values: list[str | None] | tuple[str | None, ...] | Any,
    ) -> str | None:
        counter = Counter(value for value in values if value is not None)
        if not counter:
            return None
        return counter.most_common(1)[0][0]

    @staticmethod
    def _select_advisory_recognition(
        frames: list[CalibrationCaptureFrame],
    ) -> CalibrationAdvisoryRecognition | None:
        recognitions = [
            frame.recognition for frame in frames if frame.recognition is not None
        ]
        if not recognitions:
            return None
        best = max(recognitions, key=lambda recognition: recognition.confidence)
        return CalibrationAdvisoryRecognition(
            recognized_target_id=best.gesture,
            confidence=best.confidence,
            tracking_source=best.tracking_source,
        )

    @staticmethod
    def _build_take_temporal_summary(
        frames: list[CalibrationCaptureFrame],
        trajectory: list[tuple[float, float]],
    ) -> GestureTemporalWindowSummary:
        duration_seconds = (
            max(0.0, frames[-1].observed_at - frames[0].observed_at)
            if len(frames) >= 2
            else 0.0
        )
        avg_velocity_x = 0.0
        avg_velocity_y = 0.0
        peak_speed = 0.0
        point_timestamps = [
            frame.observed_at for frame in frames if frame.point is not None
        ]
        if len(trajectory) >= 2 and len(point_timestamps) >= 2 and duration_seconds > 0:
            avg_velocity_x = (trajectory[-1][0] - trajectory[0][0]) / duration_seconds
            avg_velocity_y = (trajectory[-1][1] - trajectory[0][1]) / duration_seconds
            for index in range(1, len(trajectory)):
                dx = trajectory[index][0] - trajectory[index - 1][0]
                dy = trajectory[index][1] - trajectory[index - 1][1]
                dt = max(1e-6, point_timestamps[index] - point_timestamps[index - 1])
                peak_speed = max(peak_speed, math.hypot(dx, dy) / dt)
        active_phase = frames[-1].active_phase if frames else "recording"
        distance_values = [
            frame.distance_value for frame in frames if frame.distance_value is not None
        ]
        delta_distance = (
            distance_values[-1] - distance_values[0]
            if len(distance_values) >= 2
            else None
        )
        return GestureTemporalWindowSummary(
            duration_seconds=duration_seconds,
            frame_count=len(frames),
            avg_velocity_x=avg_velocity_x,
            avg_velocity_y=avg_velocity_y,
            peak_speed=peak_speed,
            direction_stability=1.0 if len(trajectory) >= 2 else 0.0,
            hold_stability=1.0 if duration_seconds > 0.25 else 0.0,
            jitter=0.0,
            active_phase=active_phase,
            delta_distance=delta_distance,
        )

    def process_video(
        self,
        video_path: str,
    ) -> dict[str, int | list[GestureName] | float | str | None]:
        if not self.is_available():
            with self._lock:
                self.last_error = (
                    "Gestenerkennung ist in dieser Umgebung nicht verfuegbar."
                )
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
        adapter_to_close: GestureAdapter | None = None
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
                observed_at = (
                    observation.captured_at
                    if observation.captured_at is not None
                    else time.monotonic()
                )

                if observation.point is None:
                    with self._lock:
                        pending_gesture = self._pending_gesture
                        push_state = self._push_state
                        (
                            trajectory_snapshot,
                            trajectory_timestamps_snapshot,
                            hand_size_snapshot,
                        ) = self._lifecycle.copy_motion_snapshot()
                        last_detectable_observation = self._last_detectable_observation
                    if observation.captured_at is None:
                        observed_at = (
                            pending_gesture.last_seen_at
                            if pending_gesture is not None
                            else (
                                push_state.last_seen_at
                                if push_state is not None
                                else (
                                    trajectory_timestamps_snapshot[-1]
                                    if trajectory_timestamps_snapshot
                                    else observed_at
                                )
                            )
                        )
                    detection = self._flush_pending_gesture(observed_at)
                    if detection is not None and self._cooldown_elapsed(
                        detection.gesture
                    ):
                        self._publish_runtime_detection(
                            detection=detection,
                            observation=last_detectable_observation,
                            trajectory=trajectory_snapshot,
                            trajectory_timestamps=trajectory_timestamps_snapshot,
                            hand_size=hand_size_snapshot,
                        )
                    self._reset_sequence_state(missing_observed_at=observed_at)
                    with self._lock:
                        self._lifecycle.reset_motion_window(clear_post_fire=True)
                        self._last_detectable_observation = None
                    time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
                    continue

                hand_count = len(observation.hands) if observation.hands else 1
                pose_features = extract_hand_pose_features(observation)

                _now = time.monotonic()
                if _now - self._last_landmark_broadcast >= 1.0 / 15:
                    self._last_landmark_broadcast = _now
                    _hands_data = []
                    for _h in observation.hands or [observation]:
                        if _h.landmarks:
                            _hands_data.append({
                                "hand": _h.hand,
                                "landmarks": {k: list(v) for k, v in _h.landmarks.items()},
                            })
                    self.realtime.publish_from_thread({
                        "eventType": "HandTrackingUpdated",
                        "payload": {"hands": _hands_data},
                    })
                with self._lock:
                    self.last_error = None
                    self.last_hand = observation.hand
                    self._last_detectable_observation = observation
                    recorded_point = self._lifecycle.append_point(
                        point=observation.point,
                        observed_at=observed_at,
                        hand_size=observation.hand_size,
                        hand_count=hand_count,
                        pose_features=pose_features,
                        smoothing_alpha=active_config.smoothing_alpha,
                        max_points=active_config.max_trajectory_points,
                    )
                    (
                        trajectory_snapshot,
                        trajectory_timestamps_snapshot,
                        hand_size_snapshot,
                    ) = self._lifecycle.copy_motion_snapshot()

                if recorded_point is None:
                    time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
                    continue

                analysis = self._analyze_runtime_gesture(
                    observation=observation,
                    observed_at=observed_at,
                    trajectory=trajectory_snapshot,
                    trajectory_timestamps=trajectory_timestamps_snapshot,
                    hand_size=hand_size_snapshot,
                    pose_features=pose_features,
                )
                with self._lock:
                    self._lifecycle.set_last_active_phase(analysis.active_phase)
                    self.last_tracking_quality = analysis.tracking_quality
                    self.last_active_phase = analysis.active_phase
                    self.last_candidate_scores = dict(analysis.candidate_scores)
                    self.last_sequence_scores = dict(analysis.sequence_scores)
                    self.last_sequence_distances = dict(analysis.sequence_distances)
                    self.last_sequence_margins = dict(analysis.sequence_margins)
                    self.last_sequence_profile_ids = dict(analysis.sequence_profile_ids)
                    self.last_reject_reason = analysis.reject_reason
                    self.last_spec_id = analysis.spec_id
                    self.last_dominant_hand_pose = analysis.dominant_hand_pose
                    self.last_primitive_hits = dict(analysis.primitive_hits)

                detection = self._advance_pending_gesture(
                    analysis=analysis, observed_at=observed_at
                )
                try:
                    self._append_active_calibration_capture_frame(
                        observation=observation,
                        analysis=analysis,
                        detection=detection,
                        observed_at=observed_at,
                    )
                except (AttributeError, KeyError, TypeError, ValueError) as exc:
                    logger.warning(
                        "Calibration capture frame append failed, skipping frame: %s",
                        exc,
                    )
                if detection is not None and self._cooldown_elapsed(detection.gesture):
                    self._publish_runtime_detection(
                        detection=detection,
                        observation=observation,
                        trajectory=trajectory_snapshot,
                        trajectory_timestamps=trajectory_timestamps_snapshot,
                        hand_size=hand_size_snapshot,
                    )
        finally:
            with self._lock:
                adapter_to_close = self._adapter
                self._adapter = None
                self._thread = None
                self.running = False
                self.camera_index = None
                self.camera_name = None
                self._active_calibration_capture = None
            if adapter_to_close is not None:
                try:
                    adapter_to_close.close()
                except (GestureAdapterError, OSError, RuntimeError, ValueError) as exc:
                    logger.warning(
                        "Gesture adapter close failed after runtime loop exit: %s", exc
                    )

    def _publish_runtime_detection(
        self,
        detection: GestureDetectionResult,
        observation: GestureObservation | None,
        trajectory: list[tuple[float, float]],
        trajectory_timestamps: list[float],
        hand_size: float | None,
    ) -> None:
        detected_at = datetime.now(timezone.utc)
        hand = observation.hand if observation is not None else None
        with self._lock:
            self.last_gesture = detection.gesture
            self.last_gesture_at = detected_at
            self.last_confidence = detection.confidence
            self.last_hand = hand if hand is not None else self.last_hand
            self.last_tracking_source = detection.tracking_source
            self.last_tracking_quality = detection.tracking_quality
            self.last_active_phase = detection.active_phase
            self.last_candidate_scores = dict(detection.candidate_scores)
            self.last_reject_reason = detection.reject_reason
            self.last_spec_id = detection.spec_id
            self.last_dominant_hand_pose = detection.dominant_hand_pose
            self.last_primitive_hits = dict(detection.primitive_hits)
        calibration_active = self.calibration_runtime.has_active_session("gesture")
        if calibration_active and observation is not None:
            calibration_sample = self._build_calibration_sample(
                detection=detection,
                observation=observation,
                detected_at=detected_at,
                trajectory=trajectory,
                trajectory_timestamps=trajectory_timestamps,
                hand_size=hand_size,
            )
            if calibration_sample is not None:
                self.calibration_runtime.capture_gesture_sample(calibration_sample)
        self._publish_gesture_event(
            detection=detection,
            hand=hand,
        )
        if not calibration_active:
            self._publish_ui_action_event(
                detection=detection,
                hand=hand,
            )
        self._reset_calibration_motion_window(
            observed_at=(
                trajectory_timestamps[-1] if trajectory_timestamps else time.monotonic()
            ),
        )

    def _advance_pending_gesture(
        self,
        *,
        analysis: GestureRuntimeAnalysis,
        observed_at: float,
    ) -> GestureDetectionResult | None:
        with self._lock:
            active_config = self._active_config

        detection = analysis.detection
        settled_phase = analysis.active_phase == "releasing"
        stable_hold = (
            analysis.active_phase == "holding"
            and detection is not None
            and detection.gesture == "push_click_long"
        )

        if detection is None:
            pending = self._pending_gesture
            if pending is None:
                return None
            keep_pending_during_commit = pending.detection.gesture in {
                "zoom_out_hands",
                "zoom_in_hands",
            }
            if (
                (
                    analysis.active_phase == "committing"
                    and not keep_pending_during_commit
                )
                or observed_at - pending.last_seen_at
                > active_config.pending_timeout_seconds
            ):
                self._pending_gesture = None
            return None

        pending = self._pending_gesture
        if pending is None or pending.detection.gesture != detection.gesture:
            self._pending_gesture = PendingGestureDetection(
                detection=detection,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                settled_at=observed_at if (settled_phase or stable_hold) else None,
            )
            return None

        pending.detection = detection
        pending.last_seen_at = observed_at
        if settled_phase or stable_hold:
            if pending.settled_at is None:
                pending.settled_at = observed_at
        else:
            pending.settled_at = None
            return None

        finalize_delay = (
            active_config.pending_long_finalize_seconds
            if detection.gesture == "push_click_long"
            else active_config.pending_finalize_seconds
        )
        if (
            pending.settled_at is not None
            and observed_at - pending.settled_at >= finalize_delay
        ):
            finalized = pending.detection
            self._pending_gesture = None
            return finalized

        return None

    def _flush_pending_gesture(
        self, observed_at: float
    ) -> GestureDetectionResult | None:
        with self._lock:
            pending_timeout_seconds = self._active_config.pending_timeout_seconds

        pending = self._pending_gesture
        if pending is None:
            return None
        if observed_at - pending.last_seen_at > pending_timeout_seconds:
            self._pending_gesture = None
            return None

        finalized = pending.detection
        self._pending_gesture = None
        return finalized

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
                    "tracking_quality": detection.tracking_quality,
                    "active_phase": detection.active_phase,
                    "candidate_scores": detection.candidate_scores,
                    "reject_reason": detection.reject_reason,
                    "spec_id": detection.spec_id,
                    "dominant_hand_pose": detection.dominant_hand_pose,
                    "primitive_hits": detection.primitive_hits,
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

        if last_gesture_at is None:
            return

        metadata = {
            "confidence": detection.confidence,
            "hand": hand,
            "tracking_source": detection.tracking_source,
            "tracking_quality": detection.tracking_quality,
            "active_phase": detection.active_phase,
            "candidate_scores": detection.candidate_scores,
            "sequence_scores": self.last_sequence_scores,
            "sequence_distances": self.last_sequence_distances,
            "sequence_margins": self.last_sequence_margins,
            "sequence_profile_ids": self.last_sequence_profile_ids,
            "reject_reason": detection.reject_reason,
            "spec_id": detection.spec_id,
            "dominant_hand_pose": detection.dominant_hand_pose,
            "primitive_hits": detection.primitive_hits,
        }
        self.input_orchestrator.publish_raw_input_detected(
            input_source="gesture",
            raw_input=detection.gesture,
            timestamp=last_gesture_at,
            metadata=metadata,
        )
        self.input_orchestrator.publish_ui_action_requested(
            input_source="gesture",
            raw_input=detection.gesture,
            timestamp=last_gesture_at,
            metadata=metadata,
        )

    def _cooldown_elapsed(self, gesture: GestureName) -> bool:
        now = time.time()
        with self._lock:
            cooldown_seconds = self._active_config.cooldown_seconds
            last_seen = max(self.last_gesture_time_by_name.values(), default=0.0)
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
            hand_size=hand_size,
            tracking_source=tracking_source,
            **active_config.trajectory_detection_kwargs(),
        )

    def _analyze_runtime_gesture(
        self,
        observation: GestureObservation,
        observed_at: float,
        trajectory: list[tuple[float, float]],
        trajectory_timestamps: list[float],
        hand_size: float | None,
        pose_features: HandPoseFeatures | None = None,
    ) -> GestureRuntimeAnalysis:
        candidates: list[GestureDetectionResult] = []

        zoom_detection = self._detect_zoom_gesture(observation, observed_at)
        if zoom_detection is not None:
            candidates.append(zoom_detection)

        push_detection = self._detect_push_gesture(observation, observed_at)
        if push_detection is not None:
            candidates.append(push_detection)

        trajectory_window = self._select_runtime_single_hand_trajectory(
            trajectory=trajectory,
            trajectory_timestamps=trajectory_timestamps,
            observed_at=observed_at,
        )
        trajectory_window_timestamps = (
            trajectory_timestamps[-len(trajectory_window) :]
            if trajectory_window
            else []
        )
        hand_count = (
            len(observation.hands)
            if observation.hands
            else (1 if observation.point is not None else 0)
        )
        analysis_trajectory = trajectory if hand_count >= 2 else trajectory_window
        analysis_timestamps = (
            trajectory_timestamps if hand_count >= 2 else trajectory_window_timestamps
        )
        candidates.extend(
            self._collect_runtime_single_hand_candidates(
                observation=observation,
                trajectory=trajectory_window,
                hand_size=hand_size,
                tracking_source=observation.tracking_source,
            )
        )

        with self._lock:
            active_config = self._active_config
            last_seen = max(self.last_gesture_time_by_name.values(), default=0.0)
            cooldown_active = (
                bool(self.last_gesture_time_by_name)
                and time.time() - last_seen <= active_config.cooldown_seconds
            )

        resolved_pose_features = pose_features or extract_hand_pose_features(
            observation
        )
        sequence_scores: dict[str, float] = {}
        sequence_distances: dict[str, float] = {}
        sequence_margins: dict[str, float] = {}
        sequence_profile_ids: dict[str, str] = {}
        if hand_count == 1 and trajectory_window and trajectory_window_timestamps:
            sequence_candidate_gestures: set[GestureType] = {
                cast(GestureType, candidate.gesture)
                for candidate in candidates
                if is_sequence_supported_gesture(candidate.gesture)
            }
            if sequence_candidate_gestures:
                (
                    sequence_scores,
                    sequence_distances,
                    sequence_margins,
                    sequence_profile_ids,
                ) = self._match_runtime_sequence_window(
                    candidate_gestures=sequence_candidate_gestures,
                    trajectory=trajectory_window,
                    trajectory_timestamps=trajectory_window_timestamps,
                    hand_size=hand_size,
                    sequence_channels=self._slice_runtime_sequence_channels(
                        len(trajectory_window)
                    ),
                    active_phases=self._slice_runtime_sequence_active_phases(
                        len(trajectory_window)
                    ),
                )
        return analyze_runtime_gesture(
            candidates=candidates,
            trajectory=analysis_trajectory,
            trajectory_timestamps=analysis_timestamps,
            hand_count=hand_count,
            pose_features=resolved_pose_features,
            hand_size=hand_size,
            cooldown_active=cooldown_active,
            distance_window=self._lifecycle.copy_two_hand_history(),
            sequence_scores=sequence_scores,
            sequence_profile_ids=sequence_profile_ids,
            sequence_distances=sequence_distances,
            sequence_margins=sequence_margins,
            **active_config.runtime_analysis_kwargs(),
        )

    def _detect_runtime_gesture(
        self,
        observation: GestureObservation,
        observed_at: float,
        trajectory: list[tuple[float, float]],
        trajectory_timestamps: list[float],
        hand_size: float | None,
    ) -> GestureDetectionResult | None:
        return self._analyze_runtime_gesture(
            observation=observation,
            observed_at=observed_at,
            trajectory=trajectory,
            trajectory_timestamps=trajectory_timestamps,
            hand_size=hand_size,
        ).detection

    def _detect_runtime_single_hand_gesture(
        self,
        observation: GestureObservation,
        trajectory: list[tuple[float, float]],
        hand_size: float | None,
        tracking_source: str | None,
    ) -> GestureDetectionResult | None:
        candidates = self._collect_runtime_single_hand_candidates(
            observation=observation,
            trajectory=trajectory,
            hand_size=hand_size,
            tracking_source=tracking_source,
        )
        return (
            max(candidates, key=lambda candidate: candidate.confidence)
            if candidates
            else None
        )

    def _select_runtime_single_hand_trajectory(
        self,
        trajectory: list[tuple[float, float]],
        trajectory_timestamps: list[float],
        observed_at: float,
    ) -> list[tuple[float, float]]:
        with self._lock:
            active_config = self._active_config

        if not trajectory or len(trajectory) != len(trajectory_timestamps):
            return list(trajectory)

        self._lifecycle.trajectory = list(trajectory)
        self._lifecycle.trajectory_timestamps = list(trajectory_timestamps)
        return self._lifecycle.select_single_hand_trajectory(
            observed_at=observed_at,
            cooldown_seconds=active_config.cooldown_seconds,
            min_detection_points=max(4, active_config.min_detection_points - 2),
        )

    def _collect_runtime_single_hand_candidates(
        self,
        observation: GestureObservation,
        trajectory: list[tuple[float, float]],
        hand_size: float | None,
        tracking_source: str | None,
    ) -> list[GestureDetectionResult]:
        with self._lock:
            active_config = self._active_config
            push_state = self._push_state

        runtime_min_detection_points = max(4, active_config.min_detection_points - 2)
        if len(trajectory) < runtime_min_detection_points:
            return []

        click_pose_candidate = is_click_pose_candidate(
            observation,
            center_tolerance=active_config.center_tolerance,
            extension_ratio=active_config.push_pose_extension_ratio,
            center_tolerance_multiplier=active_config.click_pose_center_tolerance_multiplier,
            extension_ratio_multiplier=active_config.click_pose_extension_ratio_multiplier,
            extension_ratio_floor=active_config.click_pose_extension_ratio_floor,
        )
        if (
            click_pose_candidate
            and push_state is not None
            and push_state.forward_started_at is not None
        ):
            return []

        pose_features = extract_hand_pose_features(observation)
        circle_pose_allowed = True
        swipe_pose_blocked = False
        if pose_features is not None:
            circle_pose_allowed = (
                pose_features.hand_openness
                < active_config.runtime_circle_pose_max_openness
            )
            index_primary_like = (
                pose_features.index_extension_ratio
                >= active_config.push_pose_extension_ratio
            )
            swipe_pose_blocked = (
                pose_features.hand_openness
                < active_config.runtime_swipe_block_max_openness
                and not index_primary_like
            )

        candidates: list[GestureDetectionResult] = []

        primary_detection = self._detect_gesture(
            trajectory,
            hand_size=hand_size,
            tracking_source=tracking_source,
        )
        if (
            primary_detection is not None
            and primary_detection.gesture == "circle"
            and circle_pose_allowed
        ):
            candidates.append(primary_detection)

        if (
            self._should_hold_swipe_for_circle(trajectory, hand_size)
            and circle_pose_allowed
        ):
            return candidates

        if swipe_pose_blocked:
            return candidates

        horizontal_segment = self._select_runtime_horizontal_segment(trajectory)
        horizontal_detection = self._detect_runtime_segment_gesture(
            trajectory=horizontal_segment,
            hand_size=hand_size,
            tracking_source=tracking_source,
            runtime_min_detection_points=runtime_min_detection_points,
        )
        if horizontal_detection is not None and horizontal_detection.gesture in {
            "swipe_left",
            "swipe_right",
        }:
            candidates.append(horizontal_detection)

        upward_segment = self._select_runtime_upstroke_segment(trajectory)
        if self._is_runtime_upstroke_candidate(upward_segment):
            upward_detection = self._detect_runtime_segment_gesture(
                trajectory=upward_segment,
                hand_size=hand_size,
                tracking_source=tracking_source,
                runtime_min_detection_points=runtime_min_detection_points,
            )
            if upward_detection is not None and upward_detection.gesture == "swipe_up":
                candidates.append(upward_detection)

        directional_segment = self._select_runtime_downstroke_segment(trajectory)
        if not self._is_runtime_downstroke_candidate(directional_segment):
            return self._dedupe_detection_candidates(candidates)

        detection = self._detect_runtime_segment_gesture(
            trajectory=directional_segment,
            hand_size=hand_size,
            tracking_source=tracking_source,
            runtime_min_detection_points=runtime_min_detection_points,
        )
        if detection is not None and detection.gesture == "swipe_down":
            candidates.append(detection)
        return self._dedupe_detection_candidates(candidates)

    @staticmethod
    def _dedupe_detection_candidates(
        candidates: list[GestureDetectionResult],
    ) -> list[GestureDetectionResult]:
        deduped: dict[str, GestureDetectionResult] = {}
        for candidate in candidates:
            previous = deduped.get(candidate.gesture)
            if previous is None or candidate.confidence > previous.confidence:
                deduped[candidate.gesture] = candidate
        return list(deduped.values())

    def _should_hold_swipe_for_circle(
        self,
        trajectory: list[tuple[float, float]],
        hand_size: float | None,
    ) -> bool:
        with self._lock:
            active_config = self._active_config

        features = extract_gesture_features(
            trajectory=trajectory,
            min_detection_points=active_config.min_detection_points,
            hand_size=hand_size,
            hand_size_reference=active_config.hand_size_reference,
            hand_size_scale_min=active_config.hand_size_scale_min,
            hand_size_scale_max=active_config.hand_size_scale_max,
        )
        if (
            features is None
            or features.radius_cv is None
            or features.total_sweep is None
        ):
            return False

        normalized_span_x = features.span_x / max(features.hand_size_scale, 1e-6)
        normalized_span_y = features.span_y / max(features.hand_size_scale, 1e-6)
        aspect_ratio = min(normalized_span_x, normalized_span_y) / max(
            normalized_span_x, normalized_span_y, 1e-6
        )
        return (
            features.radius_cv
            <= active_config.circle_radius_cv_max
            * active_config.runtime_circle_hold_radius_cv_ratio
            and abs(features.total_sweep)
            >= active_config.circle_sweep_min
            * active_config.runtime_circle_hold_sweep_ratio
            and min(normalized_span_x, normalized_span_y)
            >= active_config.swipe_min_span
            and aspect_ratio >= active_config.runtime_circle_hold_min_aspect_ratio
        )

    def _detect_runtime_segment_gesture(
        self,
        trajectory: list[tuple[float, float]] | None,
        hand_size: float | None,
        tracking_source: str | None,
        runtime_min_detection_points: int,
    ) -> GestureDetectionResult | None:
        if trajectory is None or len(trajectory) < runtime_min_detection_points:
            return None

        with self._lock:
            active_config = self._active_config

        trajectory_kwargs = active_config.trajectory_detection_kwargs()
        trajectory_kwargs["min_detection_points"] = runtime_min_detection_points
        return detect_gesture_with_confidence(
            trajectory=trajectory,
            hand_size=hand_size,
            tracking_source=tracking_source,
            **trajectory_kwargs,
        )

    @staticmethod
    def _select_runtime_horizontal_segment(
        trajectory: list[tuple[float, float]],
    ) -> list[tuple[float, float]] | None:
        if len(trajectory) < 4:
            return None

        deltas_x = [
            trajectory[index + 1][0] - trajectory[index][0]
            for index in range(len(trajectory) - 1)
        ]
        total_dx = trajectory[-1][0] - trajectory[0][0]
        if abs(total_dx) <= 1e-6:
            return None

        direction = 1 if total_dx > 0 else -1
        horizontal_run = 0
        start_index: int | None = None
        for index in range(len(deltas_x) - 1, -1, -1):
            if deltas_x[index] * direction > 0:
                horizontal_run += 1
                continue
            if horizontal_run >= 2:
                start_index = max(0, index)
                break
            horizontal_run = 0

        if horizontal_run >= 2 and start_index is None:
            start_index = 0

        if start_index is None:
            return None

        segment = trajectory[start_index:]
        return segment if len(segment) >= 4 else None

    @staticmethod
    def _select_runtime_upstroke_segment(
        trajectory: list[tuple[float, float]],
    ) -> list[tuple[float, float]] | None:
        if len(trajectory) < 4:
            return None

        deltas_y = [
            trajectory[index + 1][1] - trajectory[index][1]
            for index in range(len(trajectory) - 1)
        ]
        upward_run = 0
        start_index: int | None = None
        for index in range(len(deltas_y) - 1, -1, -1):
            if deltas_y[index] < 0:
                upward_run += 1
                continue
            if upward_run >= 2:
                start_index = max(0, index)
                break
            upward_run = 0

        if upward_run >= 2 and start_index is None:
            start_index = 0

        if start_index is None:
            return None

        segment = trajectory[start_index:]
        return segment if len(segment) >= 4 else None

    def _is_runtime_upstroke_candidate(
        self,
        trajectory: list[tuple[float, float]] | None,
    ) -> bool:
        if trajectory is None or len(trajectory) < 4:
            return False

        with self._lock:
            active_config = self._active_config

        start_y = trajectory[0][1]
        end_y = trajectory[-1][1]
        return (
            start_y >= active_config.runtime_upstroke_start_y_min
            and end_y <= active_config.runtime_upstroke_end_y_max
            and start_y - end_y >= active_config.runtime_vertical_displacement_min
        )

    @staticmethod
    def _select_runtime_downstroke_segment(
        trajectory: list[tuple[float, float]],
    ) -> list[tuple[float, float]] | None:
        if len(trajectory) < 4:
            return None

        deltas_y = [
            trajectory[index + 1][1] - trajectory[index][1]
            for index in range(len(trajectory) - 1)
        ]
        downward_run = 0
        start_index: int | None = None
        for index in range(len(deltas_y) - 1, -1, -1):
            if deltas_y[index] > 0:
                downward_run += 1
                continue
            if downward_run >= 2:
                start_index = max(0, index)
                break
            downward_run = 0

        if downward_run >= 2 and start_index is None:
            start_index = 0

        if start_index is None:
            return None

        segment = trajectory[start_index:]
        return segment if len(segment) >= 4 else None

    def _is_runtime_downstroke_candidate(
        self,
        trajectory: list[tuple[float, float]] | None,
    ) -> bool:
        if trajectory is None or len(trajectory) < 4:
            return False

        with self._lock:
            active_config = self._active_config

        start_y = trajectory[0][1]
        end_y = trajectory[-1][1]
        return (
            start_y <= active_config.runtime_downstroke_start_y_max
            and end_y >= active_config.runtime_downstroke_end_y_min
            and end_y - start_y >= active_config.runtime_vertical_displacement_min
        )

    def _detect_push_gesture(
        self,
        observation: GestureObservation,
        observed_at: float,
    ) -> GestureDetectionResult | None:
        with self._lock:
            active_config = self._active_config
        self._push_state, detection = detect_push_gesture(
            state=self._push_state,
            observation=observation,
            observed_at=observed_at,
            config=active_config,
        )
        return detection

    def _detect_zoom_gesture(
        self,
        observation: GestureObservation,
        observed_at: float,
    ) -> GestureDetectionResult | None:
        with self._lock:
            active_config = self._active_config

        if not observation.hands or len(observation.hands) < 2:
            self._lifecycle.clear_two_hand_history()
            return None

        tracked_hands: list[TrackedHandObservation] = sorted(
            [hand for hand in observation.hands if hand.point is not None],
            key=lambda hand: hand.point[0] if hand.point is not None else float("inf"),
        )
        if len(tracked_hands) < 2:
            self._lifecycle.clear_two_hand_history()
            return None

        left_hand, right_hand = tracked_hands[0], tracked_hands[-1]
        if left_hand.point is None or right_hand.point is None:
            self._lifecycle.clear_two_hand_history()
            return None
        distance = math.hypot(
            right_hand.point[0] - left_hand.point[0],
            right_hand.point[1] - left_hand.point[1],
        )
        distance_history = self._lifecycle.append_two_hand_distance(
            observed_at,
            distance,
            active_config.max_trajectory_points,
        )

        if len(distance_history) < active_config.two_hand_min_frames:
            return None

        start_distance = distance_history[0][1]
        end_distance = distance_history[-1][1]
        delta = end_distance - start_distance
        threshold = active_config.zoom_distance_delta_threshold
        frame_count = len(distance_history)
        zoom_duration = distance_history[-1][0] - distance_history[0][0]

        if (
            start_distance <= active_config.zoom_start_near_distance
            and delta >= threshold
        ):
            return GestureDetectionResult(
                gesture="zoom_in_hands",
                confidence=min(1.0, delta / max(threshold, 1e-6)),
                tracking_source="dual_hand_distance",
                metrics={
                    "start_distance": start_distance,
                    "end_distance": end_distance,
                    "delta_distance": delta,
                    "frame_count": frame_count,
                    "duration_seconds": zoom_duration,
                },
            )

        if (
            start_distance >= active_config.zoom_start_far_distance
            and -delta >= threshold
        ):
            return GestureDetectionResult(
                gesture="zoom_out_hands",
                confidence=min(1.0, (-delta) / max(threshold, 1e-6)),
                tracking_source="dual_hand_distance",
                metrics={
                    "start_distance": start_distance,
                    "end_distance": end_distance,
                    "delta_distance": delta,
                    "frame_count": frame_count,
                    "duration_seconds": zoom_duration,
                },
            )

        return None

    def _build_calibration_sample(
        self,
        detection: GestureDetectionResult,
        observation: GestureObservation,
        detected_at: datetime,
        trajectory: list[tuple[float, float]],
        trajectory_timestamps: list[float],
        hand_size: float | None,
    ) -> CalibrationCollectedSample | None:
        runtime_analysis = self._analyze_runtime_gesture(
            observation=observation,
            observed_at=(
                trajectory_timestamps[-1] if trajectory_timestamps else time.monotonic()
            ),
            trajectory=trajectory,
            trajectory_timestamps=trajectory_timestamps,
            hand_size=hand_size,
        )
        pose_features = extract_hand_pose_features(observation)
        hand_count = (
            len(observation.hands)
            if observation.hands
            else (1 if observation.point is not None else 0)
        )
        temporal_window = extract_temporal_gesture_window(
            trajectory=trajectory,
            trajectory_timestamps=trajectory_timestamps,
            hand_count=hand_count,
            pose_features=pose_features,
            hand_size=hand_size,
            cooldown_active=False,
            distance_window=self._lifecycle.copy_two_hand_history(),
        )
        with self._lock:
            active_config = self._active_config

        hand_size_scale = compute_hand_size_scale(
            hand_size=hand_size,
            hand_size_reference=active_config.hand_size_reference,
            hand_size_scale_min=active_config.hand_size_scale_min,
            hand_size_scale_max=active_config.hand_size_scale_max,
        )
        duration_seconds = None
        trajectory_summary = None
        if detection.gesture in {
            "swipe_left",
            "swipe_right",
            "swipe_up",
            "swipe_down",
            "circle",
        }:
            features = extract_gesture_features(
                trajectory=trajectory,
                min_detection_points=active_config.min_detection_points,
                hand_size=hand_size,
                hand_size_reference=active_config.hand_size_reference,
                hand_size_scale_min=active_config.hand_size_scale_min,
                hand_size_scale_max=active_config.hand_size_scale_max,
            )
            if features is not None:
                duration_seconds = (
                    trajectory_timestamps[-1] - trajectory_timestamps[0]
                    if len(trajectory_timestamps) >= 2
                    else None
                )
                trajectory_summary = GestureTrajectorySummary(
                    point_count=len(trajectory),
                    dx_total=features.dx_total,
                    dy_total=features.dy_total,
                    span_x=features.span_x,
                    span_y=features.span_y,
                    radius_mean=features.radius_mean,
                    radius_cv=features.radius_cv,
                    total_sweep=features.total_sweep,
                )

        push_metrics = None
        if detection.gesture in {"push_click_short", "push_click_long"}:
            push_metrics = GesturePushSampleMetrics(
                pose_valid=bool(detection.metrics.get("pose_valid", False)),
                forward_depth=self._metric_float(detection.metrics, "forward_depth"),
                release_depth=self._metric_float(detection.metrics, "release_depth"),
                hold_duration_seconds=self._metric_float(
                    detection.metrics, "hold_duration_seconds"
                ),
                max_depth=self._metric_float(detection.metrics, "forward_depth"),
            )
            duration_seconds = self._metric_float(
                detection.metrics, "hold_duration_seconds"
            )

        zoom_metrics = None
        if detection.gesture in {"zoom_out_hands", "zoom_in_hands"}:
            zoom_metrics = GestureZoomSampleMetrics(
                start_distance=self._metric_float(detection.metrics, "start_distance"),
                end_distance=self._metric_float(detection.metrics, "end_distance"),
                delta_distance=self._metric_float(detection.metrics, "delta_distance"),
                frame_count=self._metric_int(detection.metrics, "frame_count"),
            )
            duration_seconds = self._metric_float(detection.metrics, "duration_seconds")

        return CalibrationCollectedSample(
            sample_id=f"gesture-sample-{detected_at.timestamp():.6f}",
            modality="gesture",
            target_id=detection.gesture,
            collected_at=detected_at,
            gesture_payload=GestureCalibrationSamplePayload(
                gesture=cast(Any, detection.gesture),
                confidence=detection.confidence,
                tracking_source=detection.tracking_source,
                hand=observation.hand,
                duration_seconds=duration_seconds,
                hand_size=hand_size,
                hand_size_scale=hand_size_scale,
                trajectory=trajectory_summary,
                push=push_metrics,
                zoom=zoom_metrics,
                pose=(
                    GesturePoseSnapshot(
                        center_distance=pose_features.center_distance,
                        hand_openness=pose_features.hand_openness,
                        index_extension_ratio=pose_features.index_extension_ratio,
                        push_depth=pose_features.push_depth,
                        dominant_hand_pose=runtime_analysis.dominant_hand_pose,
                        finger_states={
                            name: GestureFingerStateSnapshot(
                                extended_score=state.extended_score,
                                curled_score=state.curled_score,
                                spread_score=state.spread_score,
                                tip_depth_relative=state.tip_depth_relative,
                                tip_to_palm_distance=state.tip_to_palm_distance,
                                label=state.label,
                            )
                            for name, state in pose_features.finger_states.items()
                        },
                    )
                    if pose_features is not None
                    else None
                ),
                temporal=GestureTemporalWindowSummary(
                    duration_seconds=temporal_window.duration_seconds,
                    frame_count=temporal_window.frame_count,
                    avg_velocity_x=temporal_window.avg_velocity_x,
                    avg_velocity_y=temporal_window.avg_velocity_y,
                    peak_speed=temporal_window.peak_speed,
                    direction_stability=temporal_window.direction_stability,
                    hold_stability=temporal_window.hold_stability,
                    jitter=temporal_window.jitter,
                    active_phase=runtime_analysis.active_phase,
                    delta_distance=temporal_window.delta_distance,
                ),
                sequence=self._build_sequence_artifact_from_runtime_window(
                    trajectory=trajectory,
                    trajectory_timestamps=trajectory_timestamps,
                    hand_size=hand_size,
                ),
                feature_windows={
                    "index_extension_ratio": self._metric_float(
                        detection.metrics, "index_extension_ratio"
                    ),
                    "center_distance": self._metric_float(
                        detection.metrics, "center_distance"
                    ),
                    "candidate_scores": runtime_analysis.candidate_scores,
                    "primitive_hits": runtime_analysis.primitive_hits,
                    "tracking_quality": runtime_analysis.tracking_quality,
                },
            ),
        )

    @staticmethod
    def _metric_float(
        metrics: dict[str, float | int | bool | str | None], key: str
    ) -> float:
        value = metrics.get(key)
        return float(value) if isinstance(value, (int, float)) else 0.0

    @staticmethod
    def _metric_int(
        metrics: dict[str, float | int | bool | str | None], key: str
    ) -> int:
        value = metrics.get(key)
        return int(value) if isinstance(value, (int, float)) else 0

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

    def _update_preview(self, preview_bytes: bytes | None) -> None:
        if preview_bytes is None:
            return

        encoded = base64.b64encode(preview_bytes).decode("ascii")
        captured_at = datetime.now(timezone.utc)
        with self._lock:
            self.latest_frame_data_url = f"data:image/jpeg;base64,{encoded}"
            self.latest_frame_captured_at = captured_at

    def _reset_runtime_state(self) -> None:
        self.latest_frame_data_url = None
        self.latest_frame_captured_at = None
        self._active_calibration_capture = None
        self._lifecycle.reset_all()
        self._pending_gesture = None
        self._last_detectable_observation = None
        self._push_state = None
        self.last_gesture = None
        self.last_gesture_at = None
        self.last_confidence = None
        self.last_hand = None
        self.last_tracking_source = None
        self.last_tracking_quality = None
        self.last_active_phase = None
        self.last_candidate_scores = {}
        self.last_sequence_scores = {}
        self.last_sequence_distances = {}
        self.last_sequence_margins = {}
        self.last_sequence_profile_ids = {}
        self.last_reject_reason = None
        self.last_spec_id = None
        self.last_dominant_hand_pose = None
        self.last_primitive_hits = {}
        self.last_error = None
        self.last_gesture_time_by_name = {}

    def _reset_calibration_motion_window(
        self, observed_at: float | None = None
    ) -> None:
        with self._lock:
            grace_seconds = self._active_config.post_fire_grace_seconds
            if observed_at is not None:
                self._lifecycle.begin_post_fire_grace(observed_at, grace_seconds)
            else:
                self._lifecycle.reset_motion_window(clear_post_fire=False)
            self._pending_gesture = None
            self._reset_sequence_state()

    def _resolve_camera_name(self, camera_index: int) -> str | None:
        devices = self.list_camera_devices()
        for device in devices:
            raw_index = device.get("index", -1)
            if isinstance(raw_index, int) and raw_index == camera_index:
                return str(device.get("name", f"Camera {camera_index}"))
        return f"Camera {camera_index}"

    def _reset_sequence_state(self, missing_observed_at: float | None = None) -> None:
        self._lifecycle.clear_two_hand_history()
        if (
            missing_observed_at is None
            or self._push_state is None
            or missing_observed_at - self._push_state.last_seen_at > 0.2
        ):
            self._push_state = None


gesture_service = GestureService(input_orchestrator_service=input_orchestrator)


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
    "analyze_runtime_gesture",
    "build_hand_landmark_map",
    "compute_hand_size_scale",
    "compute_hand_tracking_point",
    "detect_gesture_candidates",
    "detect_gesture_from_trajectory",
    "detect_gesture_with_confidence",
    "estimate_hand_size",
    "extract_gesture_features",
    "extract_hand_pose_features",
    "gesture_service",
    "select_best_gesture_candidate",
]
