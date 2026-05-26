from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Literal

from core.config import settings

PushGestureName = Literal["push_click_short", "push_click_long"]


@dataclass(slots=True)
class PushFrameSample:
    timestamp: float
    push_depth: float
    pose_valid: bool
    hand_size: float | None = None
    center_distance: float | None = None
    index_extension_ratio: float | None = None
    folded_fingers_count: int = 0
    hand: str | None = None
    tracking_quality: float | None = None


@dataclass(slots=True)
class PushCycle:
    gesture: PushGestureName
    observed_gesture: PushGestureName
    start_index: int
    end_index: int
    start_time: float
    end_time: float
    timestamps: list[float]
    push_depths: list[float]
    pose_valid_samples: list[bool]
    average_hand_size: float | None
    boundary_truncated: bool = False


@dataclass(slots=True)
class PushCycleProfile:
    gesture: PushGestureName
    observed_gesture: PushGestureName
    cycle_index: int
    start_time: float
    end_time: float
    duration_seconds: float
    trajectory_points: int
    average_hand_size: float | None
    forward_depth: float
    release_depth: float
    depth_delta: float
    depth_stability: float
    pose_valid_ratio: float
    index_extension_mean: float | None
    center_distance_mean: float | None
    folded_fingers_mean: float
    hold_duration_seconds: float
    lead_in_idle_seconds: float
    settle_idle_seconds: float
    boundary_truncated: bool


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


def segment_push_cycles(
    samples: list[PushFrameSample],
    *,
    expected_gesture: PushGestureName,
    min_cycle_points: int = settings.GESTURE_OFFLINE_PUSH_MIN_CYCLE_POINTS,
    activation_depth_threshold: float = 0.06,
    release_depth_threshold: float = 0.03,
    active_gap_seconds: float = settings.GESTURE_OFFLINE_PUSH_ACTIVE_GAP_SECONDS,
    min_pose_valid_ratio: float = settings.GESTURE_OFFLINE_PUSH_MIN_POSE_VALID_RATIO,
    min_index_extension_ratio: float = 1.1,
    min_folded_fingers: int = 2,
    center_distance_max: float = 0.35,
    long_click_seconds: float = 0.5,
    inactive_grace_seconds: float = settings.GESTURE_OFFLINE_PUSH_INACTIVE_GRACE_SECONDS,
) -> list[PushCycle]:
    if len(samples) < min_cycle_points:
        return []

    def is_active(sample: PushFrameSample) -> bool:
        if not sample.pose_valid:
            return False
        if sample.push_depth < activation_depth_threshold:
            return False
        if (
            sample.index_extension_ratio is not None
            and sample.index_extension_ratio < min_index_extension_ratio
        ):
            return False
        if (
            sample.center_distance is not None
            and sample.center_distance > center_distance_max
        ):
            return False
        return sample.folded_fingers_count >= min_folded_fingers

    cycles: list[PushCycle] = []
    active_start: int | None = None
    active_last_index: int | None = None

    def finalize(end_index: int) -> None:
        nonlocal active_start, active_last_index
        if active_start is None or active_last_index is None:
            return

        start_index = max(0, active_start - 1)
        if end_index - start_index + 1 < min_cycle_points:
            active_start = None
            active_last_index = None
            return

        segment = samples[start_index : end_index + 1]
        active_segment = samples[active_start : active_last_index + 1]
        pose_valid_ratio = mean(
            1.0 if sample.pose_valid else 0.0 for sample in active_segment
        )
        if pose_valid_ratio < min_pose_valid_ratio:
            active_start = None
            active_last_index = None
            return

        push_depths = [sample.push_depth for sample in segment]
        if max(push_depths, default=0.0) < activation_depth_threshold:
            active_start = None
            active_last_index = None
            return

        active_times = [
            sample.timestamp
            for sample in samples[active_start : active_last_index + 1]
            if is_active(sample)
        ]
        hold_duration_seconds = (
            max(0.0, active_times[-1] - active_times[0])
            if len(active_times) >= 2
            else 0.0
        )
        observed_gesture: PushGestureName = (
            "push_click_long"
            if hold_duration_seconds >= long_click_seconds
            else "push_click_short"
        )
        average_hand_sizes = [
            sample.hand_size for sample in segment if sample.hand_size is not None
        ]
        cycles.append(
            PushCycle(
                gesture=expected_gesture,
                observed_gesture=observed_gesture,
                start_index=start_index,
                end_index=end_index,
                start_time=segment[0].timestamp,
                end_time=segment[-1].timestamp,
                timestamps=[sample.timestamp for sample in segment],
                push_depths=push_depths,
                pose_valid_samples=[sample.pose_valid for sample in segment],
                average_hand_size=(
                    mean(average_hand_sizes) if average_hand_sizes else None
                ),
                boundary_truncated=start_index == 0 or end_index >= len(samples) - 1,
            )
        )
        active_start = None
        active_last_index = None

    for index, sample in enumerate(samples):
        if is_active(sample):
            if active_start is None:
                active_start = index
            active_last_index = index
            continue

        if active_start is None or active_last_index is None:
            continue

        gap_seconds = sample.timestamp - samples[active_last_index].timestamp
        if (
            sample.push_depth > release_depth_threshold
            and gap_seconds <= inactive_grace_seconds
        ):
            continue

        if (
            sample.push_depth <= release_depth_threshold
            or gap_seconds > active_gap_seconds
        ):
            finalize(index)

    if active_start is not None and active_last_index is not None:
        trailing_index = active_last_index
        if trailing_index + 1 < len(samples):
            trailing_index += 1
        finalize(trailing_index)

    return cycles


def profile_push_cycles(
    samples: list[PushFrameSample],
    cycles: list[PushCycle],
) -> list[PushCycleProfile]:
    profiles: list[PushCycleProfile] = []
    for cycle_index, cycle in enumerate(cycles):
        segment = samples[cycle.start_index : cycle.end_index + 1]
        if not segment:
            continue

        forward_depth = max(cycle.push_depths, default=0.0)
        release_depth = cycle.push_depths[-1] if cycle.push_depths else 0.0
        depth_delta = max(0.0, forward_depth - release_depth)
        depth_stability_values = [
            depth for depth in cycle.push_depths if depth >= forward_depth * 0.7
        ]
        depth_stability = max(depth_stability_values, default=0.0) - min(
            depth_stability_values, default=0.0
        )
        pose_valid_ratio = mean(
            1.0 if pose_valid else 0.0 for pose_valid in cycle.pose_valid_samples
        )
        extension_values = [
            sample.index_extension_ratio
            for sample in segment
            if sample.index_extension_ratio is not None
        ]
        center_values = [
            sample.center_distance
            for sample in segment
            if sample.center_distance is not None
        ]
        folded_values = [float(sample.folded_fingers_count) for sample in segment]
        active_times = [
            sample.timestamp
            for sample in segment
            if sample.pose_valid and sample.push_depth >= forward_depth * 0.7
        ]
        hold_duration_seconds = (
            max(0.0, active_times[-1] - active_times[0])
            if len(active_times) >= 2
            else 0.0
        )
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
            PushCycleProfile(
                gesture=cycle.gesture,
                observed_gesture=cycle.observed_gesture,
                cycle_index=cycle_index,
                start_time=cycle.start_time,
                end_time=cycle.end_time,
                duration_seconds=max(0.0, cycle.end_time - cycle.start_time),
                trajectory_points=len(cycle.timestamps),
                average_hand_size=cycle.average_hand_size,
                forward_depth=forward_depth,
                release_depth=release_depth,
                depth_delta=depth_delta,
                depth_stability=depth_stability,
                pose_valid_ratio=pose_valid_ratio,
                index_extension_mean=(
                    mean(extension_values) if extension_values else None
                ),
                center_distance_mean=mean(center_values) if center_values else None,
                folded_fingers_mean=mean(folded_values) if folded_values else 0.0,
                hold_duration_seconds=hold_duration_seconds,
                lead_in_idle_seconds=lead_in_idle_seconds,
                settle_idle_seconds=settle_idle_seconds,
                boundary_truncated=cycle.boundary_truncated,
            )
        )
    return profiles


def summarize_push_profiles(
    profiles: list[PushCycleProfile],
) -> dict[str, float | int | None]:
    if not profiles:
        return {
            "cycle_count": 0,
            "duration_mean": None,
            "duration_median": None,
            "duration_p90": None,
            "forward_depth_mean": None,
            "forward_depth_p10": None,
            "forward_depth_p90": None,
            "hold_duration_mean": None,
            "hold_duration_p90": None,
            "pose_valid_ratio_mean": None,
            "depth_stability_median": None,
        }

    durations = [profile.duration_seconds for profile in profiles]
    forward_depths = [profile.forward_depth for profile in profiles]
    hold_durations = [profile.hold_duration_seconds for profile in profiles]
    pose_valid_ratios = [profile.pose_valid_ratio for profile in profiles]
    depth_stability_values = [profile.depth_stability for profile in profiles]

    return {
        "cycle_count": len(profiles),
        "duration_mean": mean(durations),
        "duration_median": median(durations),
        "duration_p90": _percentile(durations, 0.90),
        "forward_depth_mean": mean(forward_depths),
        "forward_depth_p10": _percentile(forward_depths, 0.10),
        "forward_depth_p90": _percentile(forward_depths, 0.90),
        "hold_duration_mean": mean(hold_durations),
        "hold_duration_p90": _percentile(hold_durations, 0.90),
        "pose_valid_ratio_mean": mean(pose_valid_ratios),
        "depth_stability_median": median(depth_stability_values),
    }


__all__ = [
    "PushCycle",
    "PushCycleProfile",
    "PushFrameSample",
    "profile_push_cycles",
    "segment_push_cycles",
    "summarize_push_profiles",
]
