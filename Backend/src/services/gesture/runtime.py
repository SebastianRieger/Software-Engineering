import base64
import logging
import math
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, cast

from core.config import settings
from core.realtime import RealtimeHub, realtime_hub
from repositories.config import ConfigRepository
from schemas.calibration import (
	CalibrationCollectedSample,
	GestureCalibrationSamplePayload,
	GestureFingerStateSnapshot,
	GesturePoseSnapshot,
	GesturePushSampleMetrics,
	GestureTemporalWindowSummary,
	GestureTrajectorySummary,
	GestureZoomSampleMetrics,
)
from schemas.gestures import GestureConfig
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
from services.gesture.push_runtime import PushGestureState, detect_push_gesture, is_click_pose_candidate
from services.gesture.tracking import (
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
	extract_hand_pose_features,
	smooth_point,
)
from services.input.orchestrator import InputOrchestrator


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
		self._lock = threading.RLock()
		self._stop_event = threading.Event()
		self._thread: threading.Thread | None = None
		self._adapter: GestureAdapter | None = None
		self._active_config = GestureConfig()
		self.running = False
		self.camera_index: int | None = None
		self.camera_name: str | None = None
		self._preferred_camera_index: int | None = None
		self.latest_frame_data_url: str | None = None
		self.smoothed_point: tuple[float, float] | None = None
		self.trajectory: list[tuple[float, float]] = []
		self.trajectory_timestamps: list[float] = []
		self.hand_size_samples: list[float | None] = []
		self.two_hand_distance_history: list[tuple[float, float]] = []
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
		self.last_reject_reason: str | None = None
		self.last_spec_id: str | None = None
		self.last_dominant_hand_pose: str | None = None
		self.last_primitive_hits: dict[str, float] = {}
		self.last_error: str | None = None

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
		except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
			logger.warning("Could not reload gesture config, using defaults: %s", exc)
			config = GestureConfig()
		self.input_orchestrator.reload_config()

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
			resolved_camera_index = cast(int | None, getattr(adapter, "camera_index", camera_index))
			if resolved_camera_index is None:
				resolved_camera_index = camera_index
			self._adapter = adapter
			self.camera_index = resolved_camera_index
			self.camera_name = cast(str | None, getattr(adapter, "camera_name", None)) or self._resolve_camera_name(resolved_camera_index)
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
			self.camera_name = None

		return self.get_status()

	def shutdown(self) -> None:
		self.stop()

	def get_status(self) -> dict[str, object]:
		with self._lock:
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
			active_profile_getter = getattr(repository, "get_active_command_profile", None)
			if callable(active_profile_getter):
				active_profile = active_profile_getter()
				device_preferences = getattr(active_profile, "device_preferences", None)
				gesture_camera_index = getattr(device_preferences, "gesture_camera_index", None)
				if isinstance(gesture_camera_index, int):
					return gesture_camera_index
		except (AttributeError, OSError, sqlite3.Error, TypeError, ValueError):
			return None

		return None

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
					with self._lock:
						pending_gesture = self._pending_gesture
						push_state = self._push_state
						trajectory_snapshot = list(self.trajectory)
						trajectory_timestamps_snapshot = list(self.trajectory_timestamps)
						hand_size_snapshot = self._average_hand_size(self.hand_size_samples)
						last_detectable_observation = self._last_detectable_observation
					if observation.captured_at is None:
						observed_at = (
							pending_gesture.last_seen_at
							if pending_gesture is not None
							else push_state.last_seen_at
							if push_state is not None
							else trajectory_timestamps_snapshot[-1]
							if trajectory_timestamps_snapshot
							else observed_at
						)
					detection = self._flush_pending_gesture(observed_at)
					if detection is not None and self._cooldown_elapsed(detection.gesture):
						self._publish_runtime_detection(
							detection=detection,
							observation=last_detectable_observation,
							trajectory=trajectory_snapshot,
							trajectory_timestamps=trajectory_timestamps_snapshot,
							hand_size=hand_size_snapshot,
						)
					self._reset_sequence_state(missing_observed_at=observed_at)
					with self._lock:
						self.smoothed_point = None
						self.trajectory.clear()
						self.trajectory_timestamps.clear()
						self.hand_size_samples.clear()
						self._last_detectable_observation = None
					time.sleep(settings.GESTURE_IDLE_SLEEP_SECONDS)
					continue

				with self._lock:
					self.last_error = None
					self.last_hand = observation.hand
					self._last_detectable_observation = observation
					self.smoothed_point = smooth_point(
						previous_point=self.smoothed_point,
						point=observation.point,
						alpha=active_config.smoothing_alpha,
					)
					self.trajectory.append(self.smoothed_point)
					self.trajectory_timestamps.append(observed_at)
					self.hand_size_samples.append(observation.hand_size)
					if len(self.trajectory) > active_config.max_trajectory_points:
						self.trajectory.pop(0)
						self.trajectory_timestamps.pop(0)
						self.hand_size_samples.pop(0)
					trajectory_snapshot = list(self.trajectory)
					trajectory_timestamps_snapshot = list(self.trajectory_timestamps)
					hand_size_snapshot = self._average_hand_size(self.hand_size_samples)

				analysis = self._analyze_runtime_gesture(
					observation=observation,
					observed_at=observed_at,
					trajectory=trajectory_snapshot,
					trajectory_timestamps=trajectory_timestamps_snapshot,
					hand_size=hand_size_snapshot,
				)
				with self._lock:
					self.last_tracking_quality = analysis.tracking_quality
					self.last_active_phase = analysis.active_phase
					self.last_candidate_scores = dict(analysis.candidate_scores)
					self.last_reject_reason = analysis.reject_reason
					self.last_spec_id = analysis.spec_id
					self.last_dominant_hand_pose = analysis.dominant_hand_pose
					self.last_primitive_hits = dict(analysis.primitive_hits)

				detection = self._advance_pending_gesture(analysis=analysis, observed_at=observed_at)
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
				self.running = False

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
		self._reset_calibration_motion_window()

	def _advance_pending_gesture(
		self,
		*,
		analysis: GestureRuntimeAnalysis,
		observed_at: float,
	) -> GestureDetectionResult | None:
		detection = analysis.detection
		settled_phase = analysis.active_phase == "releasing"
		stable_hold = analysis.active_phase == "holding" and detection is not None and detection.gesture == "push_click_long"

		if detection is None:
			pending = self._pending_gesture
			if pending is None:
				return None
			keep_pending_during_commit = pending.detection.gesture in {"zoom_out_hands", "zoom_in_hands"}
			if (analysis.active_phase == "committing" and not keep_pending_during_commit) or observed_at - pending.last_seen_at > 0.3:
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

		finalize_delay = 0.16 if detection.gesture == "push_click_long" else 0.12
		if pending.settled_at is not None and observed_at - pending.settled_at >= finalize_delay:
			finalized = pending.detection
			self._pending_gesture = None
			return finalized

		return None

	def _flush_pending_gesture(self, observed_at: float) -> GestureDetectionResult | None:
		pending = self._pending_gesture
		if pending is None:
			return None
		if observed_at - pending.last_seen_at > 0.3:
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

	def _analyze_runtime_gesture(
		self,
		observation: GestureObservation,
		observed_at: float,
		trajectory: list[tuple[float, float]],
		trajectory_timestamps: list[float],
		hand_size: float | None,
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
		trajectory_window_timestamps = trajectory_timestamps[-len(trajectory_window):] if trajectory_window else []
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
			cooldown_active = bool(self.last_gesture_time_by_name) and time.time() - last_seen <= active_config.cooldown_seconds

		pose_features = extract_hand_pose_features(observation)
		hand_count = len(observation.hands) if observation.hands else (1 if observation.point is not None else 0)
		return analyze_runtime_gesture(
			candidates=candidates,
			trajectory=trajectory_window,
			trajectory_timestamps=trajectory_window_timestamps,
			hand_count=hand_count,
			pose_features=pose_features,
			hand_size=hand_size,
			swipe_threshold=active_config.swipe_threshold,
			circle_sweep_min=active_config.circle_sweep_min,
			circle_cv_max=active_config.circle_radius_cv_max,
			center_tolerance=active_config.center_tolerance,
			push_depth_threshold=active_config.push_depth_threshold,
			zoom_delta_threshold=active_config.zoom_distance_delta_threshold,
			cooldown_active=cooldown_active,
			distance_window=list(self.two_hand_distance_history),
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
		return max(candidates, key=lambda candidate: candidate.confidence) if candidates else None

	def _select_runtime_single_hand_trajectory(
		self,
		trajectory: list[tuple[float, float]],
		trajectory_timestamps: list[float],
		observed_at: float,
	) -> list[tuple[float, float]]:
		with self._lock:
			active_config = self._active_config

		if not trajectory or len(trajectory) != len(trajectory_timestamps):
			return trajectory

		window_seconds = min(1.5, max(0.9, active_config.cooldown_seconds * 1.25))
		window_start = observed_at - window_seconds
		start_index = 0
		for index, timestamp in enumerate(trajectory_timestamps):
			if timestamp >= window_start:
				start_index = index
				break
		else:
			start_index = max(0, len(trajectory) - active_config.min_detection_points)

		max_start = max(0, len(trajectory) - active_config.min_detection_points)
		start_index = min(start_index, max_start)
		return trajectory[start_index:]

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
		)
		if click_pose_candidate and push_state is not None and push_state.forward_started_at is not None:
			return []

		pose_features = extract_hand_pose_features(observation)
		circle_pose_allowed = True
		swipe_pose_blocked = False
		if pose_features is not None:
			circle_pose_allowed = pose_features.hand_openness < 0.52
			index_primary_like = pose_features.index_extension_ratio >= active_config.push_pose_extension_ratio
			swipe_pose_blocked = pose_features.hand_openness < 0.30 and not index_primary_like

		candidates: list[GestureDetectionResult] = []

		primary_detection = self._detect_gesture(
			trajectory,
			hand_size=hand_size,
			tracking_source=tracking_source,
		)
		if primary_detection is not None and primary_detection.gesture == "circle" and circle_pose_allowed:
			candidates.append(primary_detection)

		if self._should_hold_swipe_for_circle(trajectory, hand_size) and circle_pose_allowed:
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
		if horizontal_detection is not None and horizontal_detection.gesture in {"swipe_left", "swipe_right"}:
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
		if features is None or features.radius_cv is None or features.total_sweep is None:
			return False

		normalized_span_x = features.span_x / max(features.hand_size_scale, 1e-6)
		normalized_span_y = features.span_y / max(features.hand_size_scale, 1e-6)
		aspect_ratio = min(normalized_span_x, normalized_span_y) / max(normalized_span_x, normalized_span_y, 1e-6)
		return (
			features.radius_cv <= active_config.circle_radius_cv_max * 0.95
			and abs(features.total_sweep) >= active_config.circle_sweep_min * 0.7
			and min(normalized_span_x, normalized_span_y) >= active_config.swipe_min_span
			and aspect_ratio >= 0.28
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

		return detect_gesture_with_confidence(
			trajectory=trajectory,
			swipe_threshold=active_config.swipe_threshold,
			down_threshold=active_config.down_threshold,
			circle_sweep_min=active_config.circle_sweep_min,
			circle_cv_max=active_config.circle_radius_cv_max,
			min_detection_points=runtime_min_detection_points,
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

	@staticmethod
	def _select_runtime_horizontal_segment(
		trajectory: list[tuple[float, float]],
	) -> list[tuple[float, float]] | None:
		if len(trajectory) < 4:
			return None

		deltas_x = [trajectory[index + 1][0] - trajectory[index][0] for index in range(len(trajectory) - 1)]
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

		deltas_y = [trajectory[index + 1][1] - trajectory[index][1] for index in range(len(trajectory) - 1)]
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

	@staticmethod
	def _is_runtime_upstroke_candidate(
		trajectory: list[tuple[float, float]] | None,
	) -> bool:
		if trajectory is None or len(trajectory) < 4:
			return False

		start_y = trajectory[0][1]
		end_y = trajectory[-1][1]
		return start_y >= 0.46 and end_y <= 0.42 and start_y - end_y >= 0.08

	@staticmethod
	def _select_runtime_downstroke_segment(
		trajectory: list[tuple[float, float]],
	) -> list[tuple[float, float]] | None:
		if len(trajectory) < 4:
			return None

		deltas_y = [trajectory[index + 1][1] - trajectory[index][1] for index in range(len(trajectory) - 1)]
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

	@staticmethod
	def _is_runtime_downstroke_candidate(
		trajectory: list[tuple[float, float]] | None,
	) -> bool:
		if trajectory is None or len(trajectory) < 4:
			return False

		start_y = trajectory[0][1]
		end_y = trajectory[-1][1]
		return start_y <= 0.56 and end_y >= 0.58 and end_y - start_y >= 0.08

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
		frame_count = len(self.two_hand_distance_history)
		zoom_duration = self.two_hand_distance_history[-1][0] - self.two_hand_distance_history[0][0]

		if start_distance <= active_config.zoom_start_near_distance and delta >= threshold:
			self.two_hand_distance_history.clear()
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

		if start_distance >= active_config.zoom_start_far_distance and -delta >= threshold:
			self.two_hand_distance_history.clear()
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
			observed_at=trajectory_timestamps[-1] if trajectory_timestamps else time.monotonic(),
			trajectory=trajectory,
			trajectory_timestamps=trajectory_timestamps,
			hand_size=hand_size,
		)
		pose_features = extract_hand_pose_features(observation)
		hand_count = len(observation.hands) if observation.hands else (1 if observation.point is not None else 0)
		temporal_window = extract_temporal_gesture_window(
			trajectory=trajectory,
			trajectory_timestamps=trajectory_timestamps,
			hand_count=hand_count,
			pose_features=pose_features,
			hand_size=hand_size,
			cooldown_active=False,
			distance_window=list(self.two_hand_distance_history),
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
		if detection.gesture in {"swipe_left", "swipe_right", "swipe_up", "swipe_down", "circle"}:
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
				hold_duration_seconds=self._metric_float(detection.metrics, "hold_duration_seconds"),
				max_depth=self._metric_float(detection.metrics, "forward_depth"),
			)
			duration_seconds = self._metric_float(detection.metrics, "hold_duration_seconds")

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
				feature_windows={
					"index_extension_ratio": self._metric_float(detection.metrics, "index_extension_ratio"),
					"center_distance": self._metric_float(detection.metrics, "center_distance"),
					"candidate_scores": runtime_analysis.candidate_scores,
					"primitive_hits": runtime_analysis.primitive_hits,
					"tracking_quality": runtime_analysis.tracking_quality,
				},
			),
		)

	@staticmethod
	def _metric_float(metrics: dict[str, float | int | bool | str | None], key: str) -> float:
		value = metrics.get(key)
		return float(value) if isinstance(value, (int, float)) else 0.0

	@staticmethod
	def _metric_int(metrics: dict[str, float | int | bool | str | None], key: str) -> int:
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
		self.trajectory_timestamps = []
		self.hand_size_samples = []
		self._pending_gesture = None
		self._last_detectable_observation = None
		self._reset_sequence_state()
		self.last_gesture = None
		self.last_gesture_at = None
		self.last_confidence = None
		self.last_hand = None
		self.last_tracking_source = None
		self.last_tracking_quality = None
		self.last_active_phase = None
		self.last_candidate_scores = {}
		self.last_reject_reason = None
		self.last_spec_id = None
		self.last_dominant_hand_pose = None
		self.last_primitive_hits = {}
		self.last_error = None
		self.last_gesture_time_by_name = {}

	def _reset_calibration_motion_window(self) -> None:
		with self._lock:
			self.smoothed_point = None
			self.trajectory = []
			self.trajectory_timestamps = []
			self.hand_size_samples = []
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
		self.two_hand_distance_history = []
		if (
			missing_observed_at is None
			or self._push_state is None
			or missing_observed_at - self._push_state.last_seen_at > 0.2
		):
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