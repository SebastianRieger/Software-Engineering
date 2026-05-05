from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Literal

from core.config import settings
from services.gesture.contracts import default_gesture_contracts
from services.gesture.tracking import (
    GestureName,
    HandPoseFeatures,
    compute_hand_size_scale,
)


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


GesturePhase = Literal[
    "idle", "preparing", "holding", "committing", "releasing", "cooldown"
]
RuntimeGestureGroup = Literal["single_hand_motion", "push", "two_hand_zoom"]


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
    threshold: float = 0.0
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
    sequence_scores: dict[str, float]
    sequence_distances: dict[str, float]
    sequence_margins: dict[str, float]
    sequence_profile_ids: dict[str, str]
    reject_reason: str | None
    spec_id: str | None
    dominant_hand_pose: str | None
    primitive_hits: dict[str, float]


@dataclass(slots=True)
class RuntimeGestureSpec:
    specification: GestureSpecification
    group: RuntimeGestureGroup


@dataclass(slots=True)
class DetectionContext:
    trajectory: list[tuple[float, float]]
    trajectory_timestamps: list[float]
    hand_count: int
    pose_features: HandPoseFeatures | None
    hand_size: float | None
    cooldown_active: bool
    distance_window: list[tuple[float, float]]
    temporal_window: TemporalGestureWindow
    primitives: dict[str, PrimitiveDetection]
    tracking_quality: float
    dominant_hand_pose: str | None


@dataclass(slots=True)
class ResolvedRuntimeCandidate:
    candidate: GestureDetectionResult
    runtime_spec: RuntimeGestureSpec
    total_score: float
    reject_reason: str | None
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
    hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
    cooldown_active: bool = False,
    distance_window: list[tuple[float, float]] | None = None,
    phase_hold_max_peak_speed: float = settings.GESTURE_PHASE_HOLD_MAX_PEAK_SPEED,
    phase_hold_min_stability: float = settings.GESTURE_PHASE_HOLD_MIN_STABILITY,
    phase_preparing_max_seconds: float = settings.GESTURE_PHASE_PREPARING_MAX_SECONDS,
    phase_release_max_recent_speed: float = settings.GESTURE_PHASE_RELEASE_MAX_RECENT_SPEED,
    phase_release_speed_ratio: float = settings.GESTURE_PHASE_RELEASE_SPEED_RATIO,
    phase_commit_distance_threshold: float = settings.GESTURE_PHASE_COMMIT_DISTANCE_THRESHOLD,
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

    duration_seconds = max(
        trajectory_timestamps[frame_count - 1] - trajectory_timestamps[0], 1e-6
    )
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
    horizontal_stability = abs(sum(dx_components)) / max(
        sum(abs(value) for value in dx_components), 1e-6
    )
    vertical_stability = abs(sum(dy_components)) / max(
        sum(abs(value) for value in dy_components), 1e-6
    )
    direction_stability = max(horizontal_stability, vertical_stability)

    span_x = max(point[0] for point in trajectory[:frame_count]) - min(
        point[0] for point in trajectory[:frame_count]
    )
    span_y = max(point[1] for point in trajectory[:frame_count]) - min(
        point[1] for point in trajectory[:frame_count]
    )
    normalized_span_reference = max(hand_size or hand_size_reference, 1e-6)
    span_score = max(span_x, span_y) / normalized_span_reference
    hold_stability = max(0.0, min(1.0, 1.0 - (span_score / 1.4)))

    recent_speed = speeds[-1] if speeds else 0.0
    if cooldown_active:
        phase: GesturePhase = "cooldown"
    elif (
        peak_speed <= phase_hold_max_peak_speed
        and hold_stability >= phase_hold_min_stability
    ):
        phase = "holding" if pose_features is not None else "idle"
    elif duration_seconds <= phase_preparing_max_seconds:
        phase = "preparing"
    elif recent_speed <= max(
        phase_release_max_recent_speed, peak_speed * phase_release_speed_ratio
    ):
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
        if (
            phase in {"idle", "holding", "preparing"}
            and abs(delta_distance) >= phase_commit_distance_threshold
        ):
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
    primitive_hand_centered_threshold: float = settings.GESTURE_PRIMITIVE_HAND_CENTERED_THRESHOLD,
    primitive_stable_hold_threshold: float = settings.GESTURE_PRIMITIVE_STABLE_HOLD_THRESHOLD,
    primitive_index_primary_threshold: float = settings.GESTURE_PRIMITIVE_INDEX_PRIMARY_THRESHOLD,
    primitive_all_fingers_open_threshold: float = settings.GESTURE_PRIMITIVE_ALL_FINGERS_OPEN_THRESHOLD,
    primitive_fist_like_threshold: float = settings.GESTURE_PRIMITIVE_FIST_LIKE_THRESHOLD,
    primitive_push_forward_threshold: float = settings.GESTURE_PRIMITIVE_PUSH_FORWARD_THRESHOLD,
    primitive_palm_visible_score: float = settings.GESTURE_PRIMITIVE_PALM_VISIBLE_SCORE,
    primitive_palm_visible_threshold: float = settings.GESTURE_PRIMITIVE_PALM_VISIBLE_THRESHOLD,
    primitive_swipe_jitter_damping: float = settings.GESTURE_PRIMITIVE_SWIPE_JITTER_DAMPING,
    primitive_circle_motion_threshold: float = settings.GESTURE_PRIMITIVE_CIRCLE_MOTION_THRESHOLD,
    primitive_two_hand_threshold: float = settings.GESTURE_PRIMITIVE_TWO_HAND_THRESHOLD,
) -> dict[str, PrimitiveDetection]:
    features = extract_gesture_features(
        trajectory=trajectory, min_detection_points=2, hand_size=hand_size
    )
    primitives: dict[str, PrimitiveDetection] = {}

    def add(
        name: str,
        score: float,
        threshold: float = 0.55,
        reject_reason: str | None = None,
    ) -> None:
        clamped = max(0.0, min(1.0, score))
        primitives[name] = PrimitiveDetection(
            name=name,
            score=clamped,
            passed=clamped >= threshold,
            threshold=threshold,
            reject_reason=None if clamped >= threshold else reject_reason,
        )

    if pose_features is not None:
        index_state = pose_features.finger_states.get("index")
        other_curled = [
            pose_features.finger_states[name].curled_score
            for name in ("middle", "ring", "pinky")
            if name in pose_features.finger_states
        ]
        all_extended = [
            state.extended_score for state in pose_features.finger_states.values()
        ]
        all_curled = [
            state.curled_score
            for state in pose_features.finger_states.values()
            if state.name != "thumb"
        ]
        add(
            "hand_centered",
            1.0 - (pose_features.center_distance / max(center_tolerance, 1e-6)),
            primitive_hand_centered_threshold,
            "hand_not_centered",
        )
        add(
            "stable_hold",
            temporal_window.hold_stability,
            primitive_stable_hold_threshold,
            "hand_not_stable",
        )
        add(
            "index_primary",
            (
                mean(
                    [
                        index_state.extended_score if index_state is not None else 0.0,
                        *other_curled,
                    ]
                )
                if other_curled
                else 0.0
            ),
            primitive_index_primary_threshold,
            "index_not_primary",
        )
        add(
            "all_fingers_open",
            mean(all_extended) if all_extended else 0.0,
            primitive_all_fingers_open_threshold,
            "hand_not_open",
        )
        add(
            "fist_like",
            mean(all_curled) if all_curled else 0.0,
            primitive_fist_like_threshold,
            "hand_not_closed",
        )
        add(
            "push_forward",
            pose_features.push_depth / max(push_depth_threshold, 1e-6),
            primitive_push_forward_threshold,
            "push_depth_too_small",
        )
        add(
            "palm_visible",
            (
                primitive_palm_visible_score
                if pose_features.palm_center is not None
                else 0.0
            ),
            primitive_palm_visible_threshold,
            "palm_not_visible",
        )
    else:
        add("hand_centered", 0.0, primitive_hand_centered_threshold, "pose_unavailable")
        add(
            "stable_hold",
            temporal_window.hold_stability,
            primitive_stable_hold_threshold,
            "hand_not_stable",
        )

    if features is not None:
        normalized_dx = features.dx_total / max(features.hand_size_scale, 1e-6)
        normalized_dy = features.dy_total / max(features.hand_size_scale, 1e-6)
        directional_base = temporal_window.direction_stability * max(
            0.0, 1.0 - temporal_window.jitter * primitive_swipe_jitter_damping
        )
        add(
            "swipe_vector_left",
            (
                (normalized_dx / max(swipe_threshold, 1e-6)) * directional_base
                if normalized_dx > 0
                else 0.0
            ),
            reject_reason="left_commit_missing",
        )
        add(
            "swipe_vector_right",
            (
                ((-normalized_dx) / max(swipe_threshold, 1e-6)) * directional_base
                if normalized_dx < 0
                else 0.0
            ),
            reject_reason="right_commit_missing",
        )
        add(
            "swipe_vector_up",
            (
                ((-normalized_dy) / max(swipe_threshold, 1e-6)) * directional_base
                if normalized_dy < 0
                else 0.0
            ),
            reject_reason="up_commit_missing",
        )
        add(
            "swipe_vector_down",
            (
                (normalized_dy / max(swipe_threshold, 1e-6)) * directional_base
                if normalized_dy > 0
                else 0.0
            ),
            reject_reason="down_commit_missing",
        )
        circle_score = 0.0
        if features.total_sweep is not None and features.radius_cv is not None:
            sweep_score = abs(features.total_sweep) / max(circle_sweep_min, 1e-6)
            cv_score = circle_cv_max / max(features.radius_cv, 1e-6)
            circle_score = min(1.0, (sweep_score + cv_score) / 2)
        add(
            "circular_motion",
            circle_score,
            primitive_circle_motion_threshold,
            "circle_commit_missing",
        )
    else:
        add("swipe_vector_left", 0.0, reject_reason="trajectory_missing")
        add("swipe_vector_right", 0.0, reject_reason="trajectory_missing")
        add("swipe_vector_up", 0.0, reject_reason="trajectory_missing")
        add("swipe_vector_down", 0.0, reject_reason="trajectory_missing")
        add(
            "circular_motion",
            0.0,
            primitive_circle_motion_threshold,
            "trajectory_missing",
        )

    delta_distance = temporal_window.delta_distance or 0.0
    two_hand_score = (
        abs(delta_distance) / max(zoom_delta_threshold, 1e-6)
        if temporal_window.hand_count >= 2
        else 0.0
    )
    add(
        "two_hand_expand",
        two_hand_score if delta_distance > 0 else 0.0,
        primitive_two_hand_threshold,
        "two_hand_expand_missing",
    )
    add(
        "two_hand_contract",
        two_hand_score if delta_distance < 0 else 0.0,
        primitive_two_hand_threshold,
        "two_hand_contract_missing",
    )
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


def _runtime_gesture_group_for_spec(specification: GestureSpecification) -> RuntimeGestureGroup:
    if specification.min_hand_count >= 2:
        return "two_hand_zoom"
    if specification.gesture in {"push_click_short", "push_click_long"}:
        return "push"
    return "single_hand_motion"


def _runtime_gesture_group_rank(group: RuntimeGestureGroup) -> int:
    return {
        "single_hand_motion": 0,
        "two_hand_zoom": 1,
        "push": 2,
    }[group]


def build_runtime_gesture_specs() -> dict[GestureName, RuntimeGestureSpec]:
    return {
        gesture: RuntimeGestureSpec(
            specification=specification,
            group=_runtime_gesture_group_for_spec(specification),
        )
        for gesture, specification in default_gesture_specs().items()
    }


def _resolve_tracking_quality(
    *,
    trajectory: list[tuple[float, float]],
    pose_features: HandPoseFeatures | None,
    hand_count: int,
    resolver_tracking_quality_trajectory_weight: float,
    resolver_tracking_quality_pose_weight: float,
    resolver_tracking_quality_hand_weight: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            (resolver_tracking_quality_trajectory_weight if trajectory else 0.0)
            + (
                resolver_tracking_quality_pose_weight
                if pose_features is not None
                else 0.0
            )
            + (resolver_tracking_quality_hand_weight if hand_count >= 1 else 0.0),
        ),
    )


def _resolve_dominant_hand_pose(
    primitives: dict[str, PrimitiveDetection],
    pose_features: HandPoseFeatures | None,
) -> str | None:
    if primitives.get(
        "index_primary", PrimitiveDetection("index_primary", 0.0, False)
    ).passed:
        return "index_primary"
    if primitives.get(
        "all_fingers_open", PrimitiveDetection("all_fingers_open", 0.0, False)
    ).passed:
        return "open_hand"
    if primitives.get(
        "fist_like", PrimitiveDetection("fist_like", 0.0, False)
    ).passed:
        return "fist_like"
    if pose_features is not None:
        return "neutral"
    return None


def build_detection_context(
    *,
    trajectory: list[tuple[float, float]],
    trajectory_timestamps: list[float],
    hand_count: int,
    pose_features: HandPoseFeatures | None,
    hand_size: float | None,
    cooldown_active: bool,
    distance_window: list[tuple[float, float]] | None,
    swipe_threshold: float,
    circle_sweep_min: float,
    circle_cv_max: float,
    center_tolerance: float,
    push_depth_threshold: float,
    zoom_delta_threshold: float,
    hand_size_reference: float,
    phase_hold_max_peak_speed: float,
    phase_hold_min_stability: float,
    phase_preparing_max_seconds: float,
    phase_release_max_recent_speed: float,
    phase_release_speed_ratio: float,
    phase_commit_distance_threshold: float,
    primitive_hand_centered_threshold: float,
    primitive_stable_hold_threshold: float,
    primitive_index_primary_threshold: float,
    primitive_all_fingers_open_threshold: float,
    primitive_fist_like_threshold: float,
    primitive_push_forward_threshold: float,
    primitive_palm_visible_score: float,
    primitive_palm_visible_threshold: float,
    primitive_swipe_jitter_damping: float,
    primitive_circle_motion_threshold: float,
    primitive_two_hand_threshold: float,
    resolver_tracking_quality_trajectory_weight: float,
    resolver_tracking_quality_pose_weight: float,
    resolver_tracking_quality_hand_weight: float,
) -> DetectionContext:
    normalized_distance_window = list(distance_window or [])
    temporal_window = extract_temporal_gesture_window(
        trajectory=trajectory,
        trajectory_timestamps=trajectory_timestamps,
        hand_count=hand_count,
        pose_features=pose_features,
        hand_size=hand_size,
        hand_size_reference=hand_size_reference,
        cooldown_active=cooldown_active,
        distance_window=normalized_distance_window,
        phase_hold_max_peak_speed=phase_hold_max_peak_speed,
        phase_hold_min_stability=phase_hold_min_stability,
        phase_preparing_max_seconds=phase_preparing_max_seconds,
        phase_release_max_recent_speed=phase_release_max_recent_speed,
        phase_release_speed_ratio=phase_release_speed_ratio,
        phase_commit_distance_threshold=phase_commit_distance_threshold,
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
        primitive_hand_centered_threshold=primitive_hand_centered_threshold,
        primitive_stable_hold_threshold=primitive_stable_hold_threshold,
        primitive_index_primary_threshold=primitive_index_primary_threshold,
        primitive_all_fingers_open_threshold=primitive_all_fingers_open_threshold,
        primitive_fist_like_threshold=primitive_fist_like_threshold,
        primitive_push_forward_threshold=primitive_push_forward_threshold,
        primitive_palm_visible_score=primitive_palm_visible_score,
        primitive_palm_visible_threshold=primitive_palm_visible_threshold,
        primitive_swipe_jitter_damping=primitive_swipe_jitter_damping,
        primitive_circle_motion_threshold=primitive_circle_motion_threshold,
        primitive_two_hand_threshold=primitive_two_hand_threshold,
    )
    tracking_quality = _resolve_tracking_quality(
        trajectory=trajectory,
        pose_features=pose_features,
        hand_count=hand_count,
        resolver_tracking_quality_trajectory_weight=resolver_tracking_quality_trajectory_weight,
        resolver_tracking_quality_pose_weight=resolver_tracking_quality_pose_weight,
        resolver_tracking_quality_hand_weight=resolver_tracking_quality_hand_weight,
    )
    return DetectionContext(
        trajectory=trajectory,
        trajectory_timestamps=trajectory_timestamps,
        hand_count=hand_count,
        pose_features=pose_features,
        hand_size=hand_size,
        cooldown_active=cooldown_active,
        distance_window=normalized_distance_window,
        temporal_window=temporal_window,
        primitives=primitives,
        tracking_quality=tracking_quality,
        dominant_hand_pose=_resolve_dominant_hand_pose(primitives, pose_features),
    )


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
    hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
    phase_hold_max_peak_speed: float = settings.GESTURE_PHASE_HOLD_MAX_PEAK_SPEED,
    phase_hold_min_stability: float = settings.GESTURE_PHASE_HOLD_MIN_STABILITY,
    phase_preparing_max_seconds: float = settings.GESTURE_PHASE_PREPARING_MAX_SECONDS,
    phase_release_max_recent_speed: float = settings.GESTURE_PHASE_RELEASE_MAX_RECENT_SPEED,
    phase_release_speed_ratio: float = settings.GESTURE_PHASE_RELEASE_SPEED_RATIO,
    phase_commit_distance_threshold: float = settings.GESTURE_PHASE_COMMIT_DISTANCE_THRESHOLD,
    primitive_hand_centered_threshold: float = settings.GESTURE_PRIMITIVE_HAND_CENTERED_THRESHOLD,
    primitive_stable_hold_threshold: float = settings.GESTURE_PRIMITIVE_STABLE_HOLD_THRESHOLD,
    primitive_index_primary_threshold: float = settings.GESTURE_PRIMITIVE_INDEX_PRIMARY_THRESHOLD,
    primitive_all_fingers_open_threshold: float = settings.GESTURE_PRIMITIVE_ALL_FINGERS_OPEN_THRESHOLD,
    primitive_fist_like_threshold: float = settings.GESTURE_PRIMITIVE_FIST_LIKE_THRESHOLD,
    primitive_push_forward_threshold: float = settings.GESTURE_PRIMITIVE_PUSH_FORWARD_THRESHOLD,
    primitive_palm_visible_score: float = settings.GESTURE_PRIMITIVE_PALM_VISIBLE_SCORE,
    primitive_palm_visible_threshold: float = settings.GESTURE_PRIMITIVE_PALM_VISIBLE_THRESHOLD,
    primitive_swipe_jitter_damping: float = settings.GESTURE_PRIMITIVE_SWIPE_JITTER_DAMPING,
    primitive_circle_motion_threshold: float = settings.GESTURE_PRIMITIVE_CIRCLE_MOTION_THRESHOLD,
    primitive_two_hand_threshold: float = settings.GESTURE_PRIMITIVE_TWO_HAND_THRESHOLD,
    resolver_push_centered_score_floor: float = settings.GESTURE_RESOLVER_PUSH_CENTERED_SCORE_FLOOR,
    resolver_tracking_quality_trajectory_weight: float = settings.GESTURE_RESOLVER_TRACKING_QUALITY_TRAJECTORY_WEIGHT,
    resolver_tracking_quality_pose_weight: float = settings.GESTURE_RESOLVER_TRACKING_QUALITY_POSE_WEIGHT,
    resolver_tracking_quality_hand_weight: float = settings.GESTURE_RESOLVER_TRACKING_QUALITY_HAND_WEIGHT,
    resolver_candidate_confidence_weight: float = settings.GESTURE_RESOLVER_CANDIDATE_CONFIDENCE_WEIGHT,
    resolver_candidate_primitive_weight: float = settings.GESTURE_RESOLVER_CANDIDATE_PRIMITIVE_WEIGHT,
    resolver_candidate_phase_weight: float = settings.GESTURE_RESOLVER_CANDIDATE_PHASE_WEIGHT,
    resolver_required_primitive_min_score: float = settings.GESTURE_RESOLVER_REQUIRED_PRIMITIVE_MIN_SCORE,
    sequence_matching_enabled: bool = settings.GESTURE_SEQUENCE_MATCHING_ENABLED,
    sequence_scores: dict[str, float] | None = None,
    sequence_profile_ids: dict[str, str] | None = None,
    sequence_distances: dict[str, float] | None = None,
    sequence_margins: dict[str, float] | None = None,
    sequence_min_margin: float = settings.GESTURE_SEQUENCE_MIN_MARGIN,
    sequence_score_weight: float = settings.GESTURE_SEQUENCE_SCORE_WEIGHT,
) -> GestureRuntimeAnalysis:
    resolved_sequence_scores = dict(sequence_scores or {})
    resolved_sequence_profile_ids = dict(sequence_profile_ids or {})
    resolved_sequence_distances = dict(sequence_distances or {})
    resolved_sequence_margins = dict(sequence_margins or {})
    context = build_detection_context(
        trajectory=trajectory,
        trajectory_timestamps=trajectory_timestamps,
        hand_count=hand_count,
        pose_features=pose_features,
        hand_size=hand_size,
        cooldown_active=cooldown_active,
        distance_window=distance_window,
        swipe_threshold=swipe_threshold,
        circle_sweep_min=circle_sweep_min,
        circle_cv_max=circle_cv_max,
        center_tolerance=center_tolerance,
        push_depth_threshold=push_depth_threshold,
        zoom_delta_threshold=zoom_delta_threshold,
        hand_size_reference=hand_size_reference,
        phase_hold_max_peak_speed=phase_hold_max_peak_speed,
        phase_hold_min_stability=phase_hold_min_stability,
        phase_preparing_max_seconds=phase_preparing_max_seconds,
        phase_release_max_recent_speed=phase_release_max_recent_speed,
        phase_release_speed_ratio=phase_release_speed_ratio,
        phase_commit_distance_threshold=phase_commit_distance_threshold,
        primitive_hand_centered_threshold=primitive_hand_centered_threshold,
        primitive_stable_hold_threshold=primitive_stable_hold_threshold,
        primitive_index_primary_threshold=primitive_index_primary_threshold,
        primitive_all_fingers_open_threshold=primitive_all_fingers_open_threshold,
        primitive_fist_like_threshold=primitive_fist_like_threshold,
        primitive_push_forward_threshold=primitive_push_forward_threshold,
        primitive_palm_visible_score=primitive_palm_visible_score,
        primitive_palm_visible_threshold=primitive_palm_visible_threshold,
        primitive_swipe_jitter_damping=primitive_swipe_jitter_damping,
        primitive_circle_motion_threshold=primitive_circle_motion_threshold,
        primitive_two_hand_threshold=primitive_two_hand_threshold,
        resolver_tracking_quality_trajectory_weight=resolver_tracking_quality_trajectory_weight,
        resolver_tracking_quality_pose_weight=resolver_tracking_quality_pose_weight,
        resolver_tracking_quality_hand_weight=resolver_tracking_quality_hand_weight,
    )
    specs = build_runtime_gesture_specs()
    best_detection: GestureDetectionResult | None = None
    best_priority = -1
    best_score = -1.0
    best_group_rank = -1
    best_reject_reason: str | None = None
    best_reject_score = -1.0
    best_reject_spec_id: str | None = None
    best_primitive_hits: dict[str, float] = {}
    candidate_scores: dict[str, float] = {}

    for candidate in candidates:
        runtime_spec = specs.get(candidate.gesture)
        if runtime_spec is None:
            candidate_scores[candidate.gesture] = round(candidate.confidence, 4)
            continue

        spec = runtime_spec.specification
        phase = context.temporal_window.phase

        candidate_primitive_hits: dict[str, float] = {}
        candidate_primitive_passes: dict[str, bool] = {}
        for name in spec.required_primitives:
            primitive = context.primitives.get(name, PrimitiveDetection(name, 0.0, False))
            primitive_score = primitive.score
            primitive_threshold = max(
                primitive.threshold, resolver_required_primitive_min_score
            )
            if name == "push_forward":
                forward_depth = candidate.metrics.get("forward_depth")
                if isinstance(forward_depth, (int, float)):
                    primitive_score = max(
                        primitive_score,
                        float(forward_depth) / max(push_depth_threshold, 1e-6),
                    )
            elif name == "hand_centered" and candidate.gesture in {
                "push_click_short",
                "push_click_long",
            }:
                candidate_center_distance = candidate.metrics.get("center_distance")
                if (
                    not isinstance(candidate_center_distance, (int, float))
                    and context.pose_features is not None
                ):
                    candidate_center_distance = context.pose_features.center_distance
                if (
                    isinstance(candidate_center_distance, (int, float))
                    and float(candidate_center_distance) <= center_tolerance
                ):
                    primitive_score = max(
                        primitive_score, resolver_push_centered_score_floor
                    )
            elif name == "stable_hold" and candidate.gesture == "push_click_long":
                primitive_score = 1.0
            elif (
                name.startswith("swipe_vector_")
                and candidate.gesture
                == name.removeprefix("swipe_vector_").join(("swipe_", ""))
                and phase in spec.allowed_phases
            ):
                primitive_score = max(primitive_score, candidate.confidence)
            elif name in {"two_hand_expand", "two_hand_contract"}:
                delta_distance = candidate.metrics.get("delta_distance")
                if isinstance(delta_distance, (int, float)):
                    primitive_score = max(
                        primitive_score,
                        abs(float(delta_distance)) / max(zoom_delta_threshold, 1e-6),
                    )
            clamped_primitive_score = max(0.0, min(1.0, primitive_score))
            candidate_primitive_hits[name] = round(clamped_primitive_score, 4)
            candidate_primitive_passes[name] = (
                clamped_primitive_score >= primitive_threshold
            )

        primitive_scores = list(candidate_primitive_hits.values())
        combined_primitive_score = (
            mean(primitive_scores) if primitive_scores else candidate.confidence
        )
        phase_score = (
            1.0 if not spec.allowed_phases or phase in spec.allowed_phases else 0.0
        )
        hand_score = (
            1.0 if spec.min_hand_count <= hand_count <= spec.max_hand_count else 0.0
        )
        total_score = min(
            1.0,
            candidate.confidence * resolver_candidate_confidence_weight
            + combined_primitive_score * resolver_candidate_primitive_weight
            + phase_score * hand_score * resolver_candidate_phase_weight,
        )
        sequence_score = resolved_sequence_scores.get(candidate.gesture)
        sequence_margin = resolved_sequence_margins.get(candidate.gesture)
        if (
            sequence_matching_enabled
            and sequence_score is not None
            and (sequence_margin is None or sequence_margin >= sequence_min_margin)
        ):
            total_score = min(
                1.0,
                total_score * max(0.0, 1.0 - sequence_score_weight)
                + sequence_score * sequence_score_weight,
            )
        candidate_scores[candidate.gesture] = round(total_score, 4)
        if sequence_score is not None:
            candidate.metrics["sequence_score"] = round(sequence_score, 4)
        if candidate.gesture in resolved_sequence_profile_ids:
            candidate.metrics["sequence_profile_id"] = resolved_sequence_profile_ids[candidate.gesture]
        if candidate.gesture in resolved_sequence_distances:
            candidate.metrics["sequence_distance"] = round(
                resolved_sequence_distances[candidate.gesture],
                4,
            )
        if sequence_margin is not None:
            candidate.metrics["sequence_margin"] = round(sequence_margin, 4)
            if sequence_matching_enabled and sequence_margin < sequence_min_margin:
                candidate.metrics["sequence_margin_blocked"] = True

        reject_reason = None
        if not (spec.min_hand_count <= hand_count <= spec.max_hand_count):
            reject_reason = "hand_count_mismatch"
        elif spec.allowed_phases and phase not in spec.allowed_phases:
            reject_reason = "phase_mismatch"
        else:
            for primitive_name in spec.required_primitives:
                if not candidate_primitive_passes.get(primitive_name, False):
                    primitive = context.primitives.get(primitive_name)
                    reject_reason = (
                        primitive.reject_reason
                        if primitive is not None
                        else f"{primitive_name}_missing"
                    )
                    break
            if reject_reason is None:
                for primitive_name in spec.forbidden_primitives:
                    primitive = context.primitives.get(primitive_name)
                    if primitive is not None and primitive.passed:
                        reject_reason = f"{primitive_name}_forbidden"
                        break
            if reject_reason is None and total_score < spec.score_threshold:
                reject_reason = "score_below_threshold"

        primitive_hits = dict(candidate_primitive_hits)
        group_rank = _runtime_gesture_group_rank(runtime_spec.group)
        if reject_reason is None:
            if spec.priority > best_priority or (
                spec.priority == best_priority
                and (
                    total_score > best_score
                    or (total_score == best_score and group_rank > best_group_rank)
                )
            ):
                candidate.active_phase = phase
                candidate.spec_id = spec.spec_id
                candidate.tracking_quality = context.tracking_quality
                candidate.dominant_hand_pose = context.dominant_hand_pose
                candidate.primitive_hits = primitive_hits
                candidate.metrics["runtime_group"] = runtime_spec.group
                best_detection = candidate
                best_priority = spec.priority
                best_score = total_score
                best_group_rank = group_rank
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
                "tracking_quality": round(context.tracking_quality, 4),
                "candidate_score": round(best_score, 4),
                "active_phase": context.temporal_window.phase,
                "spec_id": best_detection.spec_id,
                "dominant_hand_pose": context.dominant_hand_pose,
            }
        )
        return GestureRuntimeAnalysis(
            detection=best_detection,
            active_phase=context.temporal_window.phase,
            tracking_quality=context.tracking_quality,
            candidate_scores=candidate_scores,
            sequence_scores=resolved_sequence_scores,
            sequence_distances=resolved_sequence_distances,
            sequence_margins=resolved_sequence_margins,
            sequence_profile_ids=resolved_sequence_profile_ids,
            reject_reason=None,
            spec_id=best_detection.spec_id,
            dominant_hand_pose=context.dominant_hand_pose,
            primitive_hits=best_primitive_hits,
        )

    return GestureRuntimeAnalysis(
        detection=None,
        active_phase=context.temporal_window.phase,
        tracking_quality=context.tracking_quality,
        candidate_scores=candidate_scores,
        sequence_scores=resolved_sequence_scores,
        sequence_distances=resolved_sequence_distances,
        sequence_margins=resolved_sequence_margins,
        sequence_profile_ids=resolved_sequence_profile_ids,
        reject_reason=best_reject_reason,
        spec_id=best_reject_spec_id,
        dominant_hand_pose=context.dominant_hand_pose,
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
    horizontal_dominance_ratio: float = settings.GESTURE_CANDIDATE_HORIZONTAL_DOMINANCE_RATIO,
    horizontal_max_off_axis_span_ratio: float = settings.GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_SPAN_RATIO,
    horizontal_max_off_axis_motion_ratio: float = settings.GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_MOTION_RATIO,
    vertical_dominance_ratio: float = settings.GESTURE_CANDIDATE_VERTICAL_DOMINANCE_RATIO,
    vertical_max_off_axis_span_ratio: float = settings.GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_SPAN_RATIO,
    vertical_max_off_axis_motion_ratio: float = settings.GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_MOTION_RATIO,
    circle_min_aspect_ratio: float = settings.GESTURE_CANDIDATE_CIRCLE_MIN_ASPECT_RATIO,
) -> list[GestureDetectionCandidate]:
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

    candidates: list[GestureDetectionCandidate] = []
    horizontal_candidate = _detect_horizontal_gesture_candidate(
        normalized_dx_total=normalized_dx_total,
        normalized_dy_total=normalized_dy_total,
        normalized_span_x=normalized_span_x,
        normalized_span_y=normalized_span_y,
        swipe_threshold=swipe_threshold,
        swipe_min_span=swipe_min_span,
        horizontal_dominance_ratio=horizontal_dominance_ratio,
        horizontal_max_off_axis_span_ratio=horizontal_max_off_axis_span_ratio,
        horizontal_max_off_axis_motion_ratio=horizontal_max_off_axis_motion_ratio,
    )
    if horizontal_candidate is not None:
        candidates.append(horizontal_candidate)

    candidates.extend(
        _detect_vertical_gesture_candidates(
            normalized_dx_total=normalized_dx_total,
            normalized_dy_total=normalized_dy_total,
            normalized_span_x=normalized_span_x,
            normalized_span_y=normalized_span_y,
            down_threshold=down_threshold,
            effective_up_threshold=effective_up_threshold,
            swipe_min_span=swipe_min_span,
            vertical_dominance_ratio=vertical_dominance_ratio,
            vertical_max_off_axis_span_ratio=vertical_max_off_axis_span_ratio,
            vertical_max_off_axis_motion_ratio=vertical_max_off_axis_motion_ratio,
        )
    )

    circle_candidate = _detect_circle_gesture_candidate(
        normalized_span_x=normalized_span_x,
        normalized_span_y=normalized_span_y,
        normalized_radius_mean=normalized_radius_mean,
        radius_cv=features.radius_cv,
        total_sweep=features.total_sweep,
        swipe_min_span=swipe_min_span,
        circle_sweep_min=circle_sweep_min,
        circle_cv_max=circle_cv_max,
        circle_min_radius=circle_min_radius,
        circle_min_aspect_ratio=circle_min_aspect_ratio,
    )
    if circle_candidate is not None:
        candidates.append(circle_candidate)

    return candidates


def _detect_horizontal_gesture_candidate(
    *,
    normalized_dx_total: float,
    normalized_dy_total: float,
    normalized_span_x: float,
    normalized_span_y: float,
    swipe_threshold: float,
    swipe_min_span: float,
    horizontal_dominance_ratio: float,
    horizontal_max_off_axis_span_ratio: float,
    horizontal_max_off_axis_motion_ratio: float,
) -> GestureDetectionCandidate | None:
    horizontal_margin = abs(normalized_dx_total) - swipe_threshold
    if (
        horizontal_margin > 0
        and abs(normalized_dx_total) > abs(normalized_dy_total) * horizontal_dominance_ratio
        and normalized_span_x > swipe_min_span
        and normalized_span_y
        <= max(
            swipe_min_span * horizontal_max_off_axis_span_ratio,
            abs(normalized_dx_total) * horizontal_max_off_axis_motion_ratio,
        )
    ):
        gesture = "swipe_left" if normalized_dx_total > 0 else "swipe_right"
        confidence = min(1.0, horizontal_margin / max(swipe_threshold, 1e-6))
        return GestureDetectionCandidate(gesture=gesture, confidence=confidence)
    return None


def _detect_vertical_gesture_candidates(
    *,
    normalized_dx_total: float,
    normalized_dy_total: float,
    normalized_span_x: float,
    normalized_span_y: float,
    down_threshold: float,
    effective_up_threshold: float,
    swipe_min_span: float,
    vertical_dominance_ratio: float,
    vertical_max_off_axis_span_ratio: float,
    vertical_max_off_axis_motion_ratio: float,
) -> list[GestureDetectionCandidate]:
    candidates: list[GestureDetectionCandidate] = []

    vertical_margin = normalized_dy_total - down_threshold
    if (
        vertical_margin > 0
        and normalized_dy_total > abs(normalized_dx_total) * vertical_dominance_ratio
        and normalized_span_y > swipe_min_span
        and normalized_span_x
        <= max(
            swipe_min_span * vertical_max_off_axis_span_ratio,
            abs(normalized_dy_total) * vertical_max_off_axis_motion_ratio,
        )
    ):
        confidence = min(1.0, vertical_margin / max(down_threshold, 1e-6))
        candidates.append(
            GestureDetectionCandidate(gesture="swipe_down", confidence=confidence)
        )

    upward_margin = abs(normalized_dy_total) - effective_up_threshold
    if (
        normalized_dy_total < 0
        and upward_margin > 0
        and abs(normalized_dy_total) > abs(normalized_dx_total) * vertical_dominance_ratio
        and normalized_span_y > swipe_min_span
        and normalized_span_x
        <= max(
            swipe_min_span * vertical_max_off_axis_span_ratio,
            abs(normalized_dy_total) * vertical_max_off_axis_motion_ratio,
        )
    ):
        confidence = min(1.0, upward_margin / max(effective_up_threshold, 1e-6))
        candidates.append(
            GestureDetectionCandidate(gesture="swipe_up", confidence=confidence)
        )

    return candidates


def _detect_circle_gesture_candidate(
    *,
    normalized_span_x: float,
    normalized_span_y: float,
    normalized_radius_mean: float | None,
    radius_cv: float | None,
    total_sweep: float | None,
    swipe_min_span: float,
    circle_sweep_min: float,
    circle_cv_max: float,
    circle_min_radius: float,
    circle_min_aspect_ratio: float,
) -> GestureDetectionCandidate | None:
    if (
        normalized_radius_mean is not None
        and radius_cv is not None
        and total_sweep is not None
        and normalized_radius_mean > circle_min_radius
        and abs(total_sweep) > circle_sweep_min
        and radius_cv < circle_cv_max
        and min(normalized_span_x, normalized_span_y) > swipe_min_span
        and min(normalized_span_x, normalized_span_y)
        / max(normalized_span_x, normalized_span_y, 1e-6)
        >= circle_min_aspect_ratio
    ):
        sweep_score = min(1.0, abs(total_sweep) / max(circle_sweep_min, 1e-6))
        radius_score = min(1.0, circle_cv_max / max(radius_cv, 1e-6))
        confidence = min(1.0, (sweep_score + radius_score) / 2)
        return GestureDetectionCandidate(gesture="circle", confidence=confidence)
    return None


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
    horizontal_dominance_ratio: float = settings.GESTURE_CANDIDATE_HORIZONTAL_DOMINANCE_RATIO,
    horizontal_max_off_axis_span_ratio: float = settings.GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_SPAN_RATIO,
    horizontal_max_off_axis_motion_ratio: float = settings.GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_MOTION_RATIO,
    vertical_dominance_ratio: float = settings.GESTURE_CANDIDATE_VERTICAL_DOMINANCE_RATIO,
    vertical_max_off_axis_span_ratio: float = settings.GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_SPAN_RATIO,
    vertical_max_off_axis_motion_ratio: float = settings.GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_MOTION_RATIO,
    circle_min_aspect_ratio: float = settings.GESTURE_CANDIDATE_CIRCLE_MIN_ASPECT_RATIO,
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
        horizontal_dominance_ratio=horizontal_dominance_ratio,
        horizontal_max_off_axis_span_ratio=horizontal_max_off_axis_span_ratio,
        horizontal_max_off_axis_motion_ratio=horizontal_max_off_axis_motion_ratio,
        vertical_dominance_ratio=vertical_dominance_ratio,
        vertical_max_off_axis_span_ratio=vertical_max_off_axis_span_ratio,
        vertical_max_off_axis_motion_ratio=vertical_max_off_axis_motion_ratio,
        circle_min_aspect_ratio=circle_min_aspect_ratio,
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
    "DetectionContext",
    "GestureDetectionCandidate",
    "GestureDetectionResult",
    "GestureFeatures",
    "GesturePhase",
    "GestureRuntimeAnalysis",
    "GestureSpecification",
    "PrimitiveDetection",
    "RuntimeGestureSpec",
    "TemporalGestureWindow",
    "analyze_runtime_gesture",
    "build_detection_context",
    "build_runtime_gesture_specs",
    "default_gesture_specs",
    "detect_gesture_candidates",
    "detect_gesture_from_trajectory",
    "detect_gesture_primitives",
    "detect_gesture_with_confidence",
    "extract_gesture_features",
    "extract_temporal_gesture_window",
    "select_best_gesture_candidate",
]
