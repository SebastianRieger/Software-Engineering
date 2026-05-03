from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Literal

from core.config import settings
from services.gesture.contracts import default_gesture_contracts
from services.gesture.tracking import GestureName, HandPoseFeatures, compute_hand_size_scale


@dataclass(slots=True)
class GestureFeatures:
	dx_total: float
	dy_total: float
	span_x: float
	span_y: float
	radius_mean: float | None
	radius_cv: float | None
	total_sweep: float | None
	hand_size: float | None
	hand_size_scale: float


@dataclass(slots=True)
class GestureDetectionCandidate:
	gesture: GestureName
	confidence: float


@dataclass(slots=True)
class GestureDetectionResult:
	gesture: GestureName
	confidence: float
	tracking_source: str | None = None
	active_phase: "GesturePhase" | None = None
	spec_id: str | None = None
	reject_reason: str | None = None
	tracking_quality: float | None = None
	dominant_hand_pose: str | None = None
	primitive_hits: dict[str, float] = field(default_factory=dict)
	candidate_scores: dict[str, float] = field(default_factory=dict)
	metrics: dict[str, float | int | bool | str | None] = field(default_factory=dict)


GesturePhase = Literal["idle", "preparing", "holding", "committing", "releasing", "cooldown"]


@dataclass(slots=True)
class TemporalGestureWindow:
	frame_count: int
	duration_seconds: float
	avg_velocity_x: float
	avg_velocity_y: float
	peak_speed: float
	direction_stability: float
	hold_stability: float
	jitter: float
	phase: GesturePhase
	hand_count: int = 1
	start_distance: float | None = None
	end_distance: float | None = None
	delta_distance: float | None = None


@dataclass(slots=True)
class PrimitiveDetection:
	name: str
	score: float
	passed: bool
	reject_reason: str | None = None


@dataclass(slots=True)
class GestureSpecification:
	spec_id: str
	gesture: GestureName
	required_primitives: tuple[str, ...]
	optional_primitives: tuple[str, ...] = ()
	forbidden_primitives: tuple[str, ...] = ()
	allowed_phases: tuple[GesturePhase, ...] = ()
	min_hand_count: int = 1
	max_hand_count: int = 1
	score_threshold: float = 0.45
	priority: int = 0


@dataclass(slots=True)
class GestureRuntimeAnalysis:
	detection: GestureDetectionResult | None
	active_phase: GesturePhase
	tracking_quality: float
	candidate_scores: dict[str, float]
	reject_reason: str | None
	spec_id: str | None
	dominant_hand_pose: str | None
	primitive_hits: dict[str, float]


def detect_gesture_from_trajectory(
	trajectory: list[tuple[float, float]],
	swipe_threshold: float,
	down_threshold: float,
	circle_sweep_min: float,
	circle_cv_max: float,
	min_detection_points: int = settings.GESTURE_MIN_DETECTION_POINTS,
	swipe_min_span: float = settings.GESTURE_SWIPE_MIN_SPAN,
	circle_min_radius: float = settings.GESTURE_CIRCLE_MIN_RADIUS,
	hand_size: float | None = None,
	hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
	hand_size_scale_min: float = settings.GESTURE_HAND_SIZE_SCALE_MIN,
	hand_size_scale_max: float = settings.GESTURE_HAND_SIZE_SCALE_MAX,
	up_threshold: float | None = None,
) -> GestureName | None:
	result = detect_gesture_with_confidence(
		trajectory=trajectory,
		swipe_threshold=swipe_threshold,
		down_threshold=down_threshold,
		circle_sweep_min=circle_sweep_min,
		circle_cv_max=circle_cv_max,
		min_detection_points=min_detection_points,
		swipe_min_span=swipe_min_span,
		circle_min_radius=circle_min_radius,
		min_confidence=0.0,
		hand_size=hand_size,
		hand_size_reference=hand_size_reference,
		hand_size_scale_min=hand_size_scale_min,
		hand_size_scale_max=hand_size_scale_max,
		up_threshold=up_threshold,
	)
	return result.gesture if result is not None else None


def extract_gesture_features(
	trajectory: list[tuple[float, float]],
	min_detection_points: int,
	hand_size: float | None = None,
	hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
	hand_size_scale_min: float = settings.GESTURE_HAND_SIZE_SCALE_MIN,
	hand_size_scale_max: float = settings.GESTURE_HAND_SIZE_SCALE_MAX,
) -> GestureFeatures | None:
	if len(trajectory) < min_detection_points:
		return None

	xs = [point[0] for point in trajectory]
	ys = [point[1] for point in trajectory]

	dx_total = xs[-1] - xs[0]
	dy_total = ys[-1] - ys[0]
	span_x = max(xs) - min(xs)
	span_y = max(ys) - min(ys)

	center_x = mean(xs)
	center_y = mean(ys)
	vectors = [(x - center_x, y - center_y) for x, y in trajectory]
	radii = [math.hypot(x, y) for x, y in vectors]

	if not radii:
		radius_mean = None
		radius_cv = None
		total_sweep = None
	else:
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

	hand_size_scale = compute_hand_size_scale(
		hand_size=hand_size,
		hand_size_reference=hand_size_reference,
		hand_size_scale_min=hand_size_scale_min,
		hand_size_scale_max=hand_size_scale_max,
	)

	return GestureFeatures(
		dx_total=dx_total,
		dy_total=dy_total,
		span_x=span_x,
		span_y=span_y,
		radius_mean=radius_mean,
		radius_cv=radius_cv,
		total_sweep=total_sweep,
		hand_size=hand_size,
		hand_size_scale=hand_size_scale,
	)


def extract_temporal_gesture_window(
	trajectory: list[tuple[float, float]],
	trajectory_timestamps: list[float],
	*,
	hand_count: int = 1,
	pose_features: HandPoseFeatures | None = None,
	hand_size: float | None = None,
	cooldown_active: bool = False,
	distance_window: list[tuple[float, float]] | None = None,
) -> TemporalGestureWindow:
	frame_count = min(len(trajectory), len(trajectory_timestamps))
	if frame_count < 2:
		return TemporalGestureWindow(
			frame_count=frame_count,
			duration_seconds=0.0,
			avg_velocity_x=0.0,
			avg_velocity_y=0.0,
			peak_speed=0.0,
			direction_stability=0.0,
			hold_stability=1.0,
			jitter=0.0,
			phase="cooldown" if cooldown_active else "idle",
			hand_count=hand_count,
		)

	duration_seconds = max(trajectory_timestamps[frame_count - 1] - trajectory_timestamps[0], 1e-6)
	dx_total = trajectory[frame_count - 1][0] - trajectory[0][0]
	dy_total = trajectory[frame_count - 1][1] - trajectory[0][1]
	avg_velocity_x = dx_total / duration_seconds
	avg_velocity_y = dy_total / duration_seconds

	speeds: list[float] = []
	dx_components: list[float] = []
	dy_components: list[float] = []
	total_distance = 0.0
	for index in range(frame_count - 1):
		dt = max(trajectory_timestamps[index + 1] - trajectory_timestamps[index], 1e-6)
		dx = trajectory[index + 1][0] - trajectory[index][0]
		dy = trajectory[index + 1][1] - trajectory[index][1]
		distance = math.hypot(dx, dy)
		total_distance += distance
		speeds.append(distance / dt)
		dx_components.append(dx)
		dy_components.append(dy)

	peak_speed = max(speeds, default=0.0)
	net_displacement = math.hypot(dx_total, dy_total)
	jitter = max(0.0, 1.0 - (net_displacement / max(total_distance, 1e-6)))
	horizontal_stability = abs(sum(dx_components)) / max(sum(abs(value) for value in dx_components), 1e-6)
	vertical_stability = abs(sum(dy_components)) / max(sum(abs(value) for value in dy_components), 1e-6)
	direction_stability = max(horizontal_stability, vertical_stability)

	span_x = max(point[0] for point in trajectory[:frame_count]) - min(point[0] for point in trajectory[:frame_count])
	span_y = max(point[1] for point in trajectory[:frame_count]) - min(point[1] for point in trajectory[:frame_count])
	normalized_span_reference = max(hand_size or 0.16, 1e-6)
	span_score = max(span_x, span_y) / normalized_span_reference
	hold_stability = max(0.0, min(1.0, 1.0 - (span_score / 1.4)))

	recent_speed = speeds[-1] if speeds else 0.0
	if cooldown_active:
		phase: GesturePhase = "cooldown"
	elif peak_speed <= 0.08 and hold_stability >= 0.68:
		phase = "holding" if pose_features is not None else "idle"
	elif duration_seconds <= 0.14:
		phase = "preparing"
	elif recent_speed <= max(0.025, peak_speed * 0.35):
		phase = "releasing"
	else:
		phase = "committing"

	start_distance = None
	end_distance = None
	delta_distance = None
	if distance_window and len(distance_window) >= 2:
		start_distance = distance_window[0][1]
		end_distance = distance_window[-1][1]
		delta_distance = end_distance - start_distance
		if phase in {"idle", "holding", "preparing"} and abs(delta_distance) >= 0.02:
			phase = "committing"

	return TemporalGestureWindow(
		frame_count=frame_count,
		duration_seconds=duration_seconds,
		avg_velocity_x=avg_velocity_x,
		avg_velocity_y=avg_velocity_y,
		peak_speed=peak_speed,
		direction_stability=direction_stability,
		hold_stability=hold_stability,
		jitter=jitter,
		phase=phase,
		hand_count=hand_count,
		start_distance=start_distance,
		end_distance=end_distance,
		delta_distance=delta_distance,
	)


def detect_gesture_primitives(
	*,
	trajectory: list[tuple[float, float]],
	pose_features: HandPoseFeatures | None,
	temporal_window: TemporalGestureWindow,
	swipe_threshold: float,
	circle_sweep_min: float,
	circle_cv_max: float,
	center_tolerance: float,
	push_depth_threshold: float,
	zoom_delta_threshold: float,
	hand_size: float | None = None,
) -> dict[str, PrimitiveDetection]:
	features = extract_gesture_features(trajectory=trajectory, min_detection_points=2, hand_size=hand_size)
	primitives: dict[str, PrimitiveDetection] = {}

	def add(name: str, score: float, threshold: float = 0.55, reject_reason: str | None = None) -> None:
		clamped = max(0.0, min(1.0, score))
		primitives[name] = PrimitiveDetection(
			name=name,
			score=clamped,
			passed=clamped >= threshold,
			reject_reason=None if clamped >= threshold else reject_reason,
		)

	if pose_features is not None:
		index_state = pose_features.finger_states.get("index")
		other_curled = [
			pose_features.finger_states[name].curled_score
			for name in ("middle", "ring", "pinky")
			if name in pose_features.finger_states
		]
		all_extended = [state.extended_score for state in pose_features.finger_states.values()]
		all_curled = [state.curled_score for state in pose_features.finger_states.values() if state.name != "thumb"]
		add("hand_centered", 1.0 - (pose_features.center_distance / max(center_tolerance, 1e-6)), 0.5, "hand_not_centered")
		add("stable_hold", temporal_window.hold_stability, 0.62, "hand_not_stable")
		add(
			"index_primary",
			mean([index_state.extended_score if index_state is not None else 0.0, *other_curled]) if other_curled else 0.0,
			0.62,
			"index_not_primary",
		)
		add("all_fingers_open", mean(all_extended) if all_extended else 0.0, 0.6, "hand_not_open")
		add("fist_like", mean(all_curled) if all_curled else 0.0, 0.6, "hand_not_closed")
		add("push_forward", pose_features.push_depth / max(push_depth_threshold, 1e-6), 0.55, "push_depth_too_small")
		add("palm_visible", 0.78 if pose_features.palm_center is not None else 0.0, 0.5, "palm_not_visible")
	else:
		add("hand_centered", 0.0, 0.5, "pose_unavailable")
		add("stable_hold", temporal_window.hold_stability, 0.62, "hand_not_stable")

	if features is not None:
		normalized_dx = features.dx_total / max(features.hand_size_scale, 1e-6)
		normalized_dy = features.dy_total / max(features.hand_size_scale, 1e-6)
		directional_base = temporal_window.direction_stability * max(0.0, 1.0 - temporal_window.jitter * 0.5)
		add("swipe_vector_left", ((-normalized_dx) / max(swipe_threshold, 1e-6)) * directional_base if normalized_dx < 0 else 0.0, reject_reason="left_commit_missing")
		add("swipe_vector_right", (normalized_dx / max(swipe_threshold, 1e-6)) * directional_base if normalized_dx > 0 else 0.0, reject_reason="right_commit_missing")
		add("swipe_vector_up", ((-normalized_dy) / max(swipe_threshold, 1e-6)) * directional_base if normalized_dy < 0 else 0.0, reject_reason="up_commit_missing")
		add("swipe_vector_down", (normalized_dy / max(swipe_threshold, 1e-6)) * directional_base if normalized_dy > 0 else 0.0, reject_reason="down_commit_missing")
		circle_score = 0.0
		if features.total_sweep is not None and features.radius_cv is not None:
			sweep_score = abs(features.total_sweep) / max(circle_sweep_min, 1e-6)
			cv_score = circle_cv_max / max(features.radius_cv, 1e-6)
			circle_score = min(1.0, (sweep_score + cv_score) / 2)
		add("circular_motion", circle_score, 0.58, "circle_commit_missing")
	else:
		add("swipe_vector_left", 0.0, reject_reason="trajectory_missing")
		add("swipe_vector_right", 0.0, reject_reason="trajectory_missing")
		add("swipe_vector_up", 0.0, reject_reason="trajectory_missing")
		add("swipe_vector_down", 0.0, reject_reason="trajectory_missing")
		add("circular_motion", 0.0, 0.58, "trajectory_missing")

	delta_distance = temporal_window.delta_distance or 0.0
	two_hand_score = abs(delta_distance) / max(zoom_delta_threshold, 1e-6) if temporal_window.hand_count >= 2 else 0.0
	add("two_hand_expand", two_hand_score if delta_distance > 0 else 0.0, 0.55, "two_hand_expand_missing")
	add("two_hand_contract", two_hand_score if delta_distance < 0 else 0.0, 0.55, "two_hand_contract_missing")
	return primitives


def default_gesture_specs() -> dict[GestureName, GestureSpecification]:
	return {
		gesture: GestureSpecification(
			spec_id=contract.spec_id,
			gesture=gesture,
			required_primitives=contract.required_primitives,
			forbidden_primitives=contract.forbidden_primitives,
			allowed_phases=contract.allowed_phases,
			min_hand_count=contract.min_hand_count,
			max_hand_count=contract.max_hand_count,
			score_threshold=contract.score_threshold,
			priority=contract.priority,
		)
		for gesture, contract in default_gesture_contracts().items()
	}


def analyze_runtime_gesture(
	*,
	candidates: list[GestureDetectionResult],
	trajectory: list[tuple[float, float]],
	trajectory_timestamps: list[float],
	hand_count: int,
	pose_features: HandPoseFeatures | None,
	hand_size: float | None,
	swipe_threshold: float,
	circle_sweep_min: float,
	circle_cv_max: float,
	center_tolerance: float,
	push_depth_threshold: float,
	zoom_delta_threshold: float,
	cooldown_active: bool = False,
	distance_window: list[tuple[float, float]] | None = None,
) -> GestureRuntimeAnalysis:
	temporal_window = extract_temporal_gesture_window(
		trajectory=trajectory,
		trajectory_timestamps=trajectory_timestamps,
		hand_count=hand_count,
		pose_features=pose_features,
		hand_size=hand_size,
		cooldown_active=cooldown_active,
		distance_window=distance_window,
	)
	primitives = detect_gesture_primitives(
		trajectory=trajectory,
		pose_features=pose_features,
		temporal_window=temporal_window,
		swipe_threshold=swipe_threshold,
		circle_sweep_min=circle_sweep_min,
		circle_cv_max=circle_cv_max,
		center_tolerance=center_tolerance,
		push_depth_threshold=push_depth_threshold,
		zoom_delta_threshold=zoom_delta_threshold,
		hand_size=hand_size,
	)
	tracking_quality = max(0.0, min(1.0, (0.45 if trajectory else 0.0) + (0.35 if pose_features is not None else 0.0) + (0.20 if hand_count >= 1 else 0.0)))
	dominant_hand_pose = None
	if primitives.get("index_primary", PrimitiveDetection("index_primary", 0.0, False)).passed:
		dominant_hand_pose = "index_primary"
	elif primitives.get("all_fingers_open", PrimitiveDetection("all_fingers_open", 0.0, False)).passed:
		dominant_hand_pose = "open_hand"
	elif primitives.get("fist_like", PrimitiveDetection("fist_like", 0.0, False)).passed:
		dominant_hand_pose = "fist_like"
	elif pose_features is not None:
		dominant_hand_pose = "neutral"

	specs = default_gesture_specs()
	best_detection: GestureDetectionResult | None = None
	best_priority = -1
	best_score = -1.0
	best_reject_reason: str | None = None
	best_reject_score = -1.0
	best_reject_spec_id: str | None = None
	best_primitive_hits: dict[str, float] = {}
	candidate_scores: dict[str, float] = {}

	for candidate in candidates:
		spec = specs.get(candidate.gesture)
		if spec is None:
			candidate_scores[candidate.gesture] = round(candidate.confidence, 4)
			continue

		phase = temporal_window.phase
		candidate_primitive_hits: dict[str, float] = {}
		for name in spec.required_primitives:
			primitive_score = primitives.get(name, PrimitiveDetection(name, 0.0, False)).score
			if name == "push_forward":
				forward_depth = candidate.metrics.get("forward_depth")
				if isinstance(forward_depth, (int, float)):
					primitive_score = max(primitive_score, float(forward_depth) / max(push_depth_threshold, 1e-6))
			elif name == "hand_centered" and candidate.gesture in {"push_click_short", "push_click_long"}:
				candidate_center_distance = candidate.metrics.get("center_distance")
				if not isinstance(candidate_center_distance, (int, float)) and pose_features is not None:
					candidate_center_distance = pose_features.center_distance
				if isinstance(candidate_center_distance, (int, float)) and float(candidate_center_distance) <= center_tolerance:
					primitive_score = max(primitive_score, 0.6)
			elif name == "stable_hold" and candidate.gesture == "push_click_long":
				primitive_score = 1.0
			elif (
				name.startswith("swipe_vector_")
				and candidate.gesture == name.removeprefix("swipe_vector_").join(("swipe_", ""))
				and phase in spec.allowed_phases
			):
				primitive_score = max(primitive_score, candidate.confidence)
			elif name in {"two_hand_expand", "two_hand_contract"}:
				delta_distance = candidate.metrics.get("delta_distance")
				if isinstance(delta_distance, (int, float)):
					primitive_score = max(primitive_score, abs(float(delta_distance)) / max(zoom_delta_threshold, 1e-6))
			candidate_primitive_hits[name] = round(max(0.0, min(1.0, primitive_score)), 4)

		primitive_scores = list(candidate_primitive_hits.values())
		combined_primitive_score = mean(primitive_scores) if primitive_scores else candidate.confidence
		phase_score = 1.0 if not spec.allowed_phases or phase in spec.allowed_phases else 0.0
		hand_score = 1.0 if spec.min_hand_count <= hand_count <= spec.max_hand_count else 0.0
		total_score = min(1.0, candidate.confidence * 0.55 + combined_primitive_score * 0.35 + phase_score * hand_score * 0.10)
		candidate_scores[candidate.gesture] = round(total_score, 4)

		reject_reason = None
		if not (spec.min_hand_count <= hand_count <= spec.max_hand_count):
			reject_reason = "hand_count_mismatch"
		elif spec.allowed_phases and phase not in spec.allowed_phases:
			reject_reason = "phase_mismatch"
		else:
			for primitive_name in spec.required_primitives:
				if candidate_primitive_hits.get(primitive_name, 0.0) < 0.45:
					primitive = primitives.get(primitive_name)
					reject_reason = primitive.reject_reason if primitive is not None else f"{primitive_name}_missing"
					break
			if reject_reason is None:
				for primitive_name in spec.forbidden_primitives:
					primitive = primitives.get(primitive_name)
					if primitive is not None and primitive.passed:
						reject_reason = f"{primitive_name}_forbidden"
						break
			if reject_reason is None and total_score < spec.score_threshold:
				reject_reason = "score_below_threshold"

		primitive_hits = dict(candidate_primitive_hits)
		if reject_reason is None:
			if spec.priority > best_priority or (spec.priority == best_priority and total_score > best_score):
				candidate.active_phase = phase
				candidate.spec_id = spec.spec_id
				candidate.tracking_quality = tracking_quality
				candidate.dominant_hand_pose = dominant_hand_pose
				candidate.primitive_hits = primitive_hits
				best_detection = candidate
				best_priority = spec.priority
				best_score = total_score
				best_primitive_hits = primitive_hits
		elif total_score > best_reject_score:
			best_reject_score = total_score
			best_reject_reason = reject_reason
			best_reject_spec_id = spec.spec_id
			best_primitive_hits = primitive_hits

	if best_detection is not None:
		best_detection.candidate_scores = dict(candidate_scores)
		best_detection.metrics.update(
			{
				"tracking_quality": round(tracking_quality, 4),
				"candidate_score": round(best_score, 4),
				"active_phase": temporal_window.phase,
				"spec_id": best_detection.spec_id,
				"dominant_hand_pose": dominant_hand_pose,
			}
		)
		return GestureRuntimeAnalysis(
			detection=best_detection,
			active_phase=temporal_window.phase,
			tracking_quality=tracking_quality,
			candidate_scores=candidate_scores,
			reject_reason=None,
			spec_id=best_detection.spec_id,
			dominant_hand_pose=dominant_hand_pose,
			primitive_hits=best_primitive_hits,
		)

	return GestureRuntimeAnalysis(
		detection=None,
		active_phase=temporal_window.phase,
		tracking_quality=tracking_quality,
		candidate_scores=candidate_scores,
		reject_reason=best_reject_reason,
		spec_id=best_reject_spec_id,
		dominant_hand_pose=dominant_hand_pose,
		primitive_hits=best_primitive_hits,
	)


def detect_gesture_candidates(
	features: GestureFeatures,
	swipe_threshold: float,
	down_threshold: float,
	circle_sweep_min: float,
	circle_cv_max: float,
	swipe_min_span: float,
	circle_min_radius: float,
	up_threshold: float | None = None,
) -> list[GestureDetectionCandidate]:
	candidates: list[GestureDetectionCandidate] = []
	effective_up_threshold = up_threshold if up_threshold is not None else down_threshold

	normalized_dx_total = features.dx_total / max(features.hand_size_scale, 1e-6)
	normalized_dy_total = features.dy_total / max(features.hand_size_scale, 1e-6)
	normalized_span_x = features.span_x / max(features.hand_size_scale, 1e-6)
	normalized_span_y = features.span_y / max(features.hand_size_scale, 1e-6)
	normalized_radius_mean = (
		features.radius_mean / max(features.hand_size_scale, 1e-6)
		if features.radius_mean is not None
		else None
	)

	horizontal_margin = abs(normalized_dx_total) - swipe_threshold
	if (
		horizontal_margin > 0
		and abs(normalized_dx_total) > abs(normalized_dy_total) * 1.5
		and normalized_span_x > swipe_min_span
		and normalized_span_y <= max(swipe_min_span * 2.0, abs(normalized_dx_total) * 0.75)
	):
		gesture = "swipe_left" if normalized_dx_total < 0 else "swipe_right"
		confidence = min(1.0, horizontal_margin / max(swipe_threshold, 1e-6))
		candidates.append(GestureDetectionCandidate(gesture=gesture, confidence=confidence))

	vertical_margin = normalized_dy_total - down_threshold
	if (
		vertical_margin > 0
		and normalized_dy_total > abs(normalized_dx_total) * 1.2
		and normalized_span_y > swipe_min_span
		and normalized_span_x <= max(swipe_min_span * 1.2, abs(normalized_dy_total) * 0.3)
	):
		confidence = min(1.0, vertical_margin / max(down_threshold, 1e-6))
		candidates.append(GestureDetectionCandidate(gesture="swipe_down", confidence=confidence))

	upward_margin = abs(normalized_dy_total) - effective_up_threshold
	if (
		normalized_dy_total < 0
		and upward_margin > 0
		and abs(normalized_dy_total) > abs(normalized_dx_total) * 1.2
		and normalized_span_y > swipe_min_span
		and normalized_span_x <= max(swipe_min_span * 1.2, abs(normalized_dy_total) * 0.3)
	):
		confidence = min(1.0, upward_margin / max(effective_up_threshold, 1e-6))
		candidates.append(GestureDetectionCandidate(gesture="swipe_up", confidence=confidence))

	if (
		normalized_radius_mean is not None
		and features.radius_cv is not None
		and features.total_sweep is not None
		and normalized_radius_mean > circle_min_radius
		and abs(features.total_sweep) > circle_sweep_min
		and features.radius_cv < circle_cv_max
		and min(normalized_span_x, normalized_span_y) > swipe_min_span
		and min(normalized_span_x, normalized_span_y) / max(normalized_span_x, normalized_span_y, 1e-6) >= 0.2
	):
		sweep_score = min(1.0, abs(features.total_sweep) / max(circle_sweep_min, 1e-6))
		radius_score = min(1.0, circle_cv_max / max(features.radius_cv, 1e-6))
		confidence = min(1.0, (sweep_score + radius_score) / 2)
		candidates.append(GestureDetectionCandidate(gesture="circle", confidence=confidence))

	return candidates


def select_best_gesture_candidate(
	candidates: list[GestureDetectionCandidate],
	min_confidence: float,
) -> GestureDetectionCandidate | None:
	if not candidates:
		return None

	best_candidate = max(candidates, key=lambda candidate: candidate.confidence)
	if best_candidate.confidence < min_confidence:
		return None

	return best_candidate


def detect_gesture_with_confidence(
	trajectory: list[tuple[float, float]],
	swipe_threshold: float,
	down_threshold: float,
	circle_sweep_min: float,
	circle_cv_max: float,
	min_detection_points: int = settings.GESTURE_MIN_DETECTION_POINTS,
	swipe_min_span: float = settings.GESTURE_SWIPE_MIN_SPAN,
	circle_min_radius: float = settings.GESTURE_CIRCLE_MIN_RADIUS,
	min_confidence: float = settings.GESTURE_MIN_CONFIDENCE,
	hand_size: float | None = None,
	hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
	hand_size_scale_min: float = settings.GESTURE_HAND_SIZE_SCALE_MIN,
	hand_size_scale_max: float = settings.GESTURE_HAND_SIZE_SCALE_MAX,
	tracking_source: str | None = None,
	up_threshold: float | None = None,
) -> GestureDetectionResult | None:
	features = extract_gesture_features(
		trajectory=trajectory,
		min_detection_points=min_detection_points,
		hand_size=hand_size,
		hand_size_reference=hand_size_reference,
		hand_size_scale_min=hand_size_scale_min,
		hand_size_scale_max=hand_size_scale_max,
	)
	if features is None:
		return None

	candidates = detect_gesture_candidates(
		features=features,
		swipe_threshold=swipe_threshold,
		down_threshold=down_threshold,
		circle_sweep_min=circle_sweep_min,
		circle_cv_max=circle_cv_max,
		swipe_min_span=swipe_min_span,
		circle_min_radius=circle_min_radius,
		up_threshold=up_threshold,
	)
	best_candidate = select_best_gesture_candidate(candidates, min_confidence)
	if best_candidate is None:
		return None

	return GestureDetectionResult(
		gesture=best_candidate.gesture,
		confidence=best_candidate.confidence,
		tracking_source=tracking_source,
	)


__all__ = [
	"GestureDetectionCandidate",
	"GestureDetectionResult",
	"GestureFeatures",
	"GesturePhase",
	"GestureRuntimeAnalysis",
	"GestureSpecification",
	"PrimitiveDetection",
	"TemporalGestureWindow",
	"analyze_runtime_gesture",
	"default_gesture_specs",
	"detect_gesture_candidates",
	"detect_gesture_from_trajectory",
	"detect_gesture_primitives",
	"detect_gesture_with_confidence",
	"extract_gesture_features",
	"extract_temporal_gesture_window",
	"select_best_gesture_candidate",
]