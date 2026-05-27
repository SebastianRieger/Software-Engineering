from __future__ import annotations

import math
from dataclasses import dataclass

from core.config import settings
from schemas.gestures import GestureConfig
from services.gesture.detection import GestureDetectionResult
from services.gesture.tracking import GestureObservation, extract_hand_pose_features


@dataclass(slots=True)
class PushGestureState:
    pose_started_at: float
    forward_started_at: float | None
    last_seen_at: float
    stage: str = "arming"
    long_reported: bool = False
    max_depth: float = 0.0


@dataclass(frozen=True, slots=True)
class PushPoseSnapshot:
    push_depth: float
    pose_valid: bool
    center_distance: float
    index_extension_ratio: float


def _distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return math.hypot(left[0] - right[0], left[1] - right[1])


def compute_push_pose_snapshot(
    observation: GestureObservation,
    *,
    center_tolerance: float,
    extension_ratio: float,
    push_depth_threshold: float = 0.0,
    folded_distance_ratio: float = settings.GESTURE_PUSH_FOLDED_DISTANCE_RATIO,
    required_folded_fingers: int = settings.GESTURE_PUSH_REQUIRED_FOLDED_FINGERS,
    relaxed_center_tolerance_multiplier: float = settings.GESTURE_PUSH_RELAXED_CENTER_TOLERANCE_MULTIPLIER,
    relaxed_center_tolerance_max: float = settings.GESTURE_PUSH_RELAXED_CENTER_TOLERANCE_MAX,
    depth_assist_min_threshold: float = settings.GESTURE_PUSH_DEPTH_ASSIST_MIN_THRESHOLD,
    depth_assist_threshold_ratio: float = settings.GESTURE_PUSH_DEPTH_ASSIST_THRESHOLD_RATIO,
) -> PushPoseSnapshot:
    pose = extract_hand_pose_features(observation)
    if pose is None:
        return PushPoseSnapshot(
            push_depth=0.0,
            pose_valid=False,
            center_distance=float("inf"),
            index_extension_ratio=0.0,
        )

    if observation.landmarks is None:
        return PushPoseSnapshot(
            push_depth=pose.push_depth,
            pose_valid=False,
            center_distance=pose.center_distance,
            index_extension_ratio=pose.index_extension_ratio,
        )

    landmarks = observation.landmarks
    wrist = landmarks.get("wrist")
    index_tip = landmarks.get("index_tip")
    index_mcp = landmarks.get("index_mcp")
    if wrist is None or index_tip is None or index_mcp is None:
        return PushPoseSnapshot(
            push_depth=pose.push_depth,
            pose_valid=False,
            center_distance=pose.center_distance,
            index_extension_ratio=pose.index_extension_ratio,
        )

    folded_checks = 0
    for finger_tip, finger_mcp in (
        ("middle_tip", "middle_mcp"),
        ("ring_tip", "ring_mcp"),
        ("pinky_tip", "pinky_mcp"),
    ):
        tip = landmarks.get(finger_tip)
        mcp = landmarks.get(finger_mcp)
        if tip is None or mcp is None:
            continue
        if _distance(tip, wrist) <= _distance(mcp, wrist) * folded_distance_ratio:
            folded_checks += 1

    relaxed_center_tolerance = min(
        relaxed_center_tolerance_max,
        center_tolerance * relaxed_center_tolerance_multiplier,
    )
    depth_assisted_push = pose.push_depth >= max(
        depth_assist_min_threshold, push_depth_threshold * depth_assist_threshold_ratio
    )
    index_or_depth_valid = (
        pose.index_extension_ratio > extension_ratio or depth_assisted_push
    )

    return PushPoseSnapshot(
        push_depth=pose.push_depth,
        pose_valid=(
            folded_checks >= required_folded_fingers
            and pose.center_distance <= relaxed_center_tolerance
            and index_or_depth_valid
        ),
        center_distance=pose.center_distance,
        index_extension_ratio=pose.index_extension_ratio,
    )


def is_click_pose_candidate(
    observation: GestureObservation,
    *,
    center_tolerance: float,
    extension_ratio: float,
    center_tolerance_multiplier: float = settings.GESTURE_CLICK_POSE_CENTER_TOLERANCE_MULTIPLIER,
    extension_ratio_multiplier: float = settings.GESTURE_CLICK_POSE_EXTENSION_RATIO_MULTIPLIER,
    extension_ratio_floor: float = settings.GESTURE_CLICK_POSE_EXTENSION_RATIO_FLOOR,
) -> bool:
    snapshot = compute_push_pose_snapshot(
        observation,
        center_tolerance=center_tolerance * center_tolerance_multiplier,
        extension_ratio=max(
            extension_ratio_floor, extension_ratio * extension_ratio_multiplier
        ),
        push_depth_threshold=0.0,
    )
    return snapshot.pose_valid


def _build_push_detection(
    *,
    gesture: str,
    confidence: float,
    snapshot: PushPoseSnapshot,
    forward_depth: float,
    release_depth: float,
    hold_duration_seconds: float,
    stage: str,
) -> GestureDetectionResult:
    return GestureDetectionResult(
        gesture=gesture,
        confidence=confidence,
        tracking_source="index_push",
        metrics={
            "forward_depth": forward_depth,
            "release_depth": release_depth,
            "hold_duration_seconds": hold_duration_seconds,
            "pose_valid": snapshot.pose_valid,
            "index_extension_ratio": snapshot.index_extension_ratio,
            "center_distance": snapshot.center_distance,
            "push_stage": stage,
        },
    )


def detect_push_gesture(
    *,
    state: PushGestureState | None,
    observation: GestureObservation,
    observed_at: float,
    config: GestureConfig,
) -> tuple[PushGestureState | None, GestureDetectionResult | None]:
    snapshot = compute_push_pose_snapshot(
        observation,
        center_tolerance=config.center_tolerance,
        extension_ratio=config.push_pose_extension_ratio,
        push_depth_threshold=config.push_depth_threshold,
        folded_distance_ratio=config.push_folded_distance_ratio,
        required_folded_fingers=config.push_required_folded_fingers,
        relaxed_center_tolerance_multiplier=config.push_relaxed_center_tolerance_multiplier,
        relaxed_center_tolerance_max=config.push_relaxed_center_tolerance_max,
        depth_assist_min_threshold=config.push_depth_assist_min_threshold,
        depth_assist_threshold_ratio=config.push_depth_assist_threshold_ratio,
    )
    is_forward = (
        snapshot.pose_valid and snapshot.push_depth >= config.push_depth_threshold
    )
    is_released = snapshot.push_depth <= config.push_release_threshold
    transient_pose_gap_seconds = min(
        config.push_transient_pose_gap_max_seconds,
        config.long_click_seconds * config.push_transient_pose_gap_long_ratio,
    )

    if (
        state is not None
        and state.forward_started_at is not None
        and is_released
        and observed_at >= state.forward_started_at
    ):
        gesture_started_at = state.forward_started_at
        if gesture_started_at is None:
            return None, None
        duration = state.last_seen_at - gesture_started_at
        total_duration = observed_at - gesture_started_at
        confidence = min(1.0, state.max_depth / max(config.push_depth_threshold, 1e-6))
        if total_duration >= config.long_click_seconds and not state.long_reported:
            return None, _build_push_detection(
                gesture="push_click_long",
                confidence=confidence,
                snapshot=snapshot,
                forward_depth=state.max_depth,
                release_depth=snapshot.push_depth,
                hold_duration_seconds=total_duration,
                stage="releasing",
            )
        if config.push_short_click_min_duration <= duration < config.long_click_seconds:
            return None, _build_push_detection(
                gesture="push_click_short",
                confidence=confidence,
                snapshot=snapshot,
                forward_depth=state.max_depth,
                release_depth=snapshot.push_depth,
                hold_duration_seconds=duration,
                stage="releasing",
            )
        return None, None

    if snapshot.pose_valid:
        if state is None:
            return (
                PushGestureState(
                    pose_started_at=observed_at,
                    forward_started_at=observed_at if is_forward else None,
                    last_seen_at=observed_at,
                    stage="forward" if is_forward else "arming",
                    max_depth=snapshot.push_depth,
                ),
                None,
            )

        state.last_seen_at = observed_at
        state.max_depth = max(state.max_depth, snapshot.push_depth)
        if is_forward and state.forward_started_at is None:
            state.forward_started_at = observed_at
        if state.forward_started_at is not None:
            forward_duration = observed_at - state.forward_started_at
            state.stage = (
                "holding"
                if forward_duration >= config.long_click_seconds
                else "forward"
            )
            if (
                forward_duration >= config.long_click_seconds
                and not state.long_reported
            ):
                state.long_reported = True
                confidence = min(
                    1.0, state.max_depth / max(config.push_depth_threshold, 1e-6)
                )
                return state, _build_push_detection(
                    gesture="push_click_long",
                    confidence=confidence,
                    snapshot=snapshot,
                    forward_depth=state.max_depth,
                    release_depth=snapshot.push_depth,
                    hold_duration_seconds=forward_duration,
                    stage=state.stage,
                )
        else:
            state.stage = "arming"
        return state, None

    if state is None:
        return None, None

    if (
        not is_released
        and observed_at - state.last_seen_at <= transient_pose_gap_seconds
    ):
        return state, None

    gesture_started_at = (
        state.forward_started_at
        if state.forward_started_at is not None
        else state.pose_started_at
    )
    if state.max_depth < config.push_depth_threshold:
        return None, None

    duration = state.last_seen_at - gesture_started_at
    total_duration = observed_at - gesture_started_at
    release_gap = observed_at - state.last_seen_at
    confidence = min(1.0, state.max_depth / max(config.push_depth_threshold, 1e-6))

    if (
        total_duration >= config.long_click_seconds
        and release_gap <= config.push_long_release_max_gap_seconds
        and not state.long_reported
    ):
        return None, _build_push_detection(
            gesture="push_click_long",
            confidence=confidence,
            snapshot=snapshot,
            forward_depth=state.max_depth,
            release_depth=snapshot.push_depth,
            hold_duration_seconds=total_duration,
            stage=state.stage,
        )

    if config.push_short_click_min_duration <= duration < config.long_click_seconds:
        return None, _build_push_detection(
            gesture="push_click_short",
            confidence=confidence,
            snapshot=snapshot,
            forward_depth=state.max_depth,
            release_depth=snapshot.push_depth,
            hold_duration_seconds=duration,
            stage=state.stage,
        )

    return None, None
