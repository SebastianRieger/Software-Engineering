from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Literal

from core.config import settings
from services.gesture.detection import (
    extract_gesture_features,
    extract_temporal_gesture_window,
)
from services.gesture.tracking import GestureName

AxisName = Literal["x", "y"]


@dataclass(slots=True)
class SwipeFrameSample:
    timestamp: float
    point: tuple[float, float]
    hand_size: float | None = None
    phase: str | None = None
    candidate_score: float = 0.0
    tracking_quality: float | None = None
    hand_count: int = 1
    push_depth: float = 0.0
    center_distance: float | None = None
    index_extension_ratio: float | None = None


@dataclass(slots=True)
class SwipeCycle:
    gesture: GestureName
    observed_gesture: GestureName
    start_index: int
    end_index: int
    start_time: float
    end_time: float
    axis: AxisName
    sign: float
    trajectory: list[tuple[float, float]]
    timestamps: list[float]
    average_hand_size: float | None


@dataclass(slots=True)
class SwipeCycleProfile:
    gesture: GestureName
    observed_gesture: GestureName
    cycle_index: int
    start_time: float
    end_time: float
    duration_seconds: float
    trajectory_points: int
    average_hand_size: float | None
    axis: AxisName
    signed_displacement: float
    normalized_signed_displacement: float
    off_axis_displacement: float
    axis_span: float
    normalized_axis_span: float
    off_axis_span: float
    axis_dominance: float
    avg_velocity_x: float
    avg_velocity_y: float
    peak_speed: float
    direction_stability: float
    hold_stability: float
    jitter: float
    active_phase: str
    lead_in_idle_seconds: float
    settle_idle_seconds: float


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    position = max(
        0.0, min(float(len(ordered) - 1), probability * float(len(ordered) - 1))
    )
    lower_index = int(position)
    upper_index = min(len(ordered) - 1, lower_index + 1)
    weight = position - float(lower_index)
    lower = ordered[lower_index]
    upper = ordered[upper_index]
    return lower + (upper - lower) * weight


def swipe_axis_sign(gesture: GestureName) -> tuple[AxisName, float]:
    if gesture == "swipe_left":
        return "x", 1.0
    if gesture == "swipe_right":
        return "x", -1.0
    if gesture == "swipe_down":
        return "y", 1.0
    if gesture == "swipe_up":
        return "y", -1.0
    raise ValueError(f"Unsupported swipe gesture: {gesture}")


def gesture_for_axis_sign(axis: AxisName, sign: float) -> GestureName:
    if axis == "x":
        return "swipe_left" if sign >= 0 else "swipe_right"
    return "swipe_down" if sign >= 0 else "swipe_up"


def segment_swipe_cycles(
    samples: list[SwipeFrameSample],
    *,
    expected_gesture: GestureName,
    min_cycle_points: int = settings.GESTURE_OFFLINE_SWIPE_MIN_CYCLE_POINTS,
    motion_step_threshold: float = settings.GESTURE_OFFLINE_SWIPE_MOTION_STEP_THRESHOLD,
    edge_speed_threshold: float = settings.GESTURE_OFFLINE_SWIPE_EDGE_SPEED_THRESHOLD,
    active_gap_seconds: float = settings.GESTURE_OFFLINE_SWIPE_ACTIVE_GAP_SECONDS,
    axis_ratio_threshold: float = settings.GESTURE_OFFLINE_SWIPE_AXIS_RATIO_THRESHOLD,
    min_cycle_displacement: float = 0.08,
    edge_gap_ratio: float = settings.GESTURE_OFFLINE_SWIPE_EDGE_GAP_RATIO,
    edge_gap_max_seconds: float = settings.GESTURE_OFFLINE_SWIPE_EDGE_GAP_MAX_SECONDS,
) -> list[SwipeCycle]:
    if len(samples) < min_cycle_points:
        return []

    axis, sign = swipe_axis_sign(expected_gesture)
    step_end_indices: list[tuple[int, float]] = []
    step_speeds: list[float] = []
    step_axis_signs: list[float] = []

    for index in range(len(samples) - 1):
        current = samples[index]
        next_sample = samples[index + 1]
        dt = max(next_sample.timestamp - current.timestamp, 1e-6)
        dx = next_sample.point[0] - current.point[0]
        dy = next_sample.point[1] - current.point[1]
        axis_delta = dx if axis == "x" else dy
        off_axis_delta = dy if axis == "x" else dx
        axis_sign = 1.0 if axis_delta >= 0 else -1.0
        speed = ((dx * dx) + (dy * dy)) ** 0.5 / dt
        step_speeds.append(speed)
        step_axis_signs.append(axis_sign)
        if (
            abs(axis_delta) >= motion_step_threshold
            and abs(axis_delta) >= abs(off_axis_delta) * axis_ratio_threshold
        ):
            step_end_indices.append((index + 1, axis_sign))

    if not step_end_indices:
        return []

    grouped_end_indices: list[tuple[float, list[int]]] = [
        (step_end_indices[0][1], [step_end_indices[0][0]])
    ]
    edge_gap_seconds = min(edge_gap_max_seconds, active_gap_seconds * edge_gap_ratio)
    for point_index, step_sign in step_end_indices[1:]:
        grouped_sign, grouped_points = grouped_end_indices[-1]
        previous_index = grouped_points[-1]
        time_gap = samples[point_index].timestamp - samples[previous_index].timestamp
        if (
            step_sign == grouped_sign
            and point_index - previous_index <= 2
            and time_gap <= active_gap_seconds
        ):
            grouped_points.append(point_index)
            continue
        grouped_end_indices.append((step_sign, [point_index]))

    cycles: list[SwipeCycle] = []
    last_end_index = -1
    for grouped_sign, grouped_indices in grouped_end_indices:
        start_index = max(0, grouped_indices[0] - 1)
        end_index = grouped_indices[-1]

        while start_index > last_end_index + 1:
            previous_index = start_index - 1
            previous_speed = step_speeds[previous_index]
            if previous_speed < edge_speed_threshold:
                break
            if (
                samples[start_index].timestamp - samples[previous_index].timestamp
                > edge_gap_seconds
            ):
                break
            if step_axis_signs[previous_index] != grouped_sign:
                break
            start_index = previous_index

        while end_index < len(samples) - 1:
            current_speed = step_speeds[end_index]
            if current_speed < edge_speed_threshold:
                break
            if (
                samples[end_index + 1].timestamp - samples[end_index].timestamp
                > edge_gap_seconds
            ):
                break
            if step_axis_signs[end_index] != grouped_sign:
                break
            end_index += 1

        if end_index - start_index + 1 < min_cycle_points:
            continue

        trajectory = [sample.point for sample in samples[start_index : end_index + 1]]
        timestamps = [
            sample.timestamp for sample in samples[start_index : end_index + 1]
        ]
        average_hand_size_values = [
            sample.hand_size
            for sample in samples[start_index : end_index + 1]
            if sample.hand_size is not None
        ]
        average_hand_size = (
            mean(average_hand_size_values) if average_hand_size_values else None
        )
        features = extract_gesture_features(
            trajectory=trajectory,
            min_detection_points=min_cycle_points,
            hand_size=average_hand_size,
        )
        if features is None:
            continue

        axis_displacement = features.dx_total if axis == "x" else features.dy_total
        observed_sign = 1.0 if axis_displacement >= 0 else -1.0
        signed_displacement = abs(axis_displacement)
        off_axis_displacement = (
            abs(features.dy_total) if axis == "x" else abs(features.dx_total)
        )
        if signed_displacement < min_cycle_displacement:
            continue
        if signed_displacement < off_axis_displacement * axis_ratio_threshold:
            continue

        cycles.append(
            SwipeCycle(
                gesture=expected_gesture,
                observed_gesture=gesture_for_axis_sign(axis, observed_sign),
                start_index=start_index,
                end_index=end_index,
                start_time=timestamps[0],
                end_time=timestamps[-1],
                axis=axis,
                sign=observed_sign,
                trajectory=trajectory,
                timestamps=timestamps,
                average_hand_size=average_hand_size,
            )
        )
        last_end_index = end_index

    return cycles


def profile_swipe_cycles(
    samples: list[SwipeFrameSample],
    cycles: list[SwipeCycle],
) -> list[SwipeCycleProfile]:
    profiles: list[SwipeCycleProfile] = []
    for cycle_index, cycle in enumerate(cycles):
        temporal = extract_temporal_gesture_window(
            trajectory=cycle.trajectory,
            trajectory_timestamps=cycle.timestamps,
            hand_count=1,
            pose_features=None,
            hand_size=cycle.average_hand_size,
            cooldown_active=False,
        )
        features = extract_gesture_features(
            trajectory=cycle.trajectory,
            min_detection_points=min(4, len(cycle.trajectory)),
            hand_size=cycle.average_hand_size,
        )
        if features is None:
            continue

        signed_displacement = (
            features.dx_total * cycle.sign
            if cycle.axis == "x"
            else features.dy_total * cycle.sign
        )
        off_axis_displacement = (
            abs(features.dy_total) if cycle.axis == "x" else abs(features.dx_total)
        )
        axis_span = features.span_x if cycle.axis == "x" else features.span_y
        off_axis_span = features.span_y if cycle.axis == "x" else features.span_x
        normalized_signed_displacement = signed_displacement / max(
            features.hand_size_scale, 1e-6
        )
        normalized_axis_span = axis_span / max(features.hand_size_scale, 1e-6)
        lead_in_idle_seconds = (
            max(0.0, cycle.start_time - samples[cycle.start_index - 1].timestamp)
            if cycle.start_index > 0
            else 0.0
        )
        settle_idle_seconds = (
            max(0.0, samples[cycle.end_index + 1].timestamp - cycle.end_time)
            if cycle.end_index < len(samples) - 1
            else 0.0
        )
        profiles.append(
            SwipeCycleProfile(
                gesture=cycle.gesture,
                observed_gesture=cycle.observed_gesture,
                cycle_index=cycle_index,
                start_time=cycle.start_time,
                end_time=cycle.end_time,
                duration_seconds=temporal.duration_seconds,
                trajectory_points=len(cycle.trajectory),
                average_hand_size=cycle.average_hand_size,
                axis=cycle.axis,
                signed_displacement=signed_displacement,
                normalized_signed_displacement=normalized_signed_displacement,
                off_axis_displacement=off_axis_displacement,
                axis_span=axis_span,
                normalized_axis_span=normalized_axis_span,
                off_axis_span=off_axis_span,
                axis_dominance=signed_displacement / max(off_axis_displacement, 1e-6),
                avg_velocity_x=temporal.avg_velocity_x,
                avg_velocity_y=temporal.avg_velocity_y,
                peak_speed=temporal.peak_speed,
                direction_stability=temporal.direction_stability,
                hold_stability=temporal.hold_stability,
                jitter=temporal.jitter,
                active_phase=temporal.phase,
                lead_in_idle_seconds=lead_in_idle_seconds,
                settle_idle_seconds=settle_idle_seconds,
            )
        )
    return profiles


def summarize_swipe_profiles(
    profiles: list[SwipeCycleProfile],
) -> dict[str, float | int | None]:
    if not profiles:
        return {
            "cycle_count": 0,
            "duration_mean": None,
            "duration_median": None,
            "duration_p90": None,
            "signed_displacement_mean": None,
            "normalized_signed_displacement_mean": None,
            "signed_displacement_p10": None,
            "normalized_signed_displacement_p10": None,
            "peak_speed_mean": None,
            "peak_speed_p90": None,
            "direction_stability_mean": None,
            "axis_dominance_mean": None,
            "normalized_axis_span_mean": None,
            "lead_in_idle_mean": None,
            "settle_idle_mean": None,
        }

    durations = [profile.duration_seconds for profile in profiles]
    displacements = [profile.signed_displacement for profile in profiles]
    normalized_displacements = [
        profile.normalized_signed_displacement for profile in profiles
    ]
    peak_speeds = [profile.peak_speed for profile in profiles]
    direction_stabilities = [profile.direction_stability for profile in profiles]
    axis_dominance = [profile.axis_dominance for profile in profiles]
    normalized_axis_spans = [profile.normalized_axis_span for profile in profiles]
    lead_in_idles = [profile.lead_in_idle_seconds for profile in profiles]
    settle_idles = [profile.settle_idle_seconds for profile in profiles]

    return {
        "cycle_count": len(profiles),
        "duration_mean": mean(durations),
        "duration_median": median(durations),
        "duration_p90": _percentile(durations, 0.90),
        "signed_displacement_mean": mean(displacements),
        "normalized_signed_displacement_mean": mean(normalized_displacements),
        "signed_displacement_p10": _percentile(displacements, 0.10),
        "normalized_signed_displacement_p10": _percentile(
            normalized_displacements, 0.10
        ),
        "peak_speed_mean": mean(peak_speeds),
        "peak_speed_p90": _percentile(peak_speeds, 0.90),
        "direction_stability_mean": mean(direction_stabilities),
        "axis_dominance_mean": mean(axis_dominance),
        "normalized_axis_span_mean": mean(normalized_axis_spans),
        "lead_in_idle_mean": mean(lead_in_idles),
        "settle_idle_mean": mean(settle_idles),
    }


__all__ = [
    "SwipeCycle",
    "SwipeCycleProfile",
    "SwipeFrameSample",
    "gesture_for_axis_sign",
    "profile_swipe_cycles",
    "segment_swipe_cycles",
    "summarize_swipe_profiles",
    "swipe_axis_sign",
]
