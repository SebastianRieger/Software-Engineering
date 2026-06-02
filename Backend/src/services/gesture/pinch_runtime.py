from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from services.gesture.detection import GestureDetectionResult
from services.gesture.tracking import HandPoseFeatures, PinchContactMetrics

_DEFAULT_CLOSE_THRESHOLD = 0.30
_DEFAULT_OPEN_THRESHOLD = 0.52
_DEFAULT_WINDOW = 4
_DEFAULT_COOLDOWN = 0.55
_DEFAULT_CONFIDENCE = 0.92


@dataclass(slots=True)
class PinchGestureState:
    pinch_closed: bool
    spread_window: list[float] = field(default_factory=list)
    last_fire_at: float = 0.0
    anchor: tuple[float, float] | None = None
    raw_distance: float | None = None
    smoothed_distance: float | None = None
    contact_pair: tuple[str, str] | None = None


def _config_value(config: Any, name: str, default: float | int) -> float | int:
    if config is None:
        return default
    value = getattr(config, name, default)
    return value if isinstance(value, (int, float)) else default


def _fallback_thumb_index_distance(
    pose_features: HandPoseFeatures | None,
) -> float | None:
    if pose_features is None:
        return None
    thumb = pose_features.finger_states.get("thumb")
    if thumb is None:
        return None
    return thumb.spread_score


def is_pinch_pose_candidate(
    pose_features: HandPoseFeatures | None,
    *,
    config: Any = None,
) -> bool:
    if pose_features is None:
        return False

    min_hand_openness = float(
        _config_value(
            config,
            "pinch_pose_min_hand_openness",
            0.38,
        )
    )
    min_thumb_extended = float(
        _config_value(
            config,
            "pinch_pose_min_thumb_extended",
            0.4,
        )
    )
    min_index_extended = float(
        _config_value(
            config,
            "pinch_pose_min_index_extended",
            0.55,
        )
    )
    max_curled_support_fingers = int(
        _config_value(
            config,
            "pinch_pose_max_curled_support_fingers",
            1,
        )
    )
    reject_fist_like_threshold = float(
        _config_value(
            config,
            "pinch_pose_reject_fist_like_threshold",
            0.6,
        )
    )

    if pose_features.hand_openness < min_hand_openness:
        return False

    thumb = pose_features.finger_states.get("thumb")
    index = pose_features.finger_states.get("index")
    if thumb is None or index is None:
        return False

    if thumb.extended_score < min_thumb_extended:
        return False
    if index.extended_score < min_index_extended:
        return False

    support_fingers = (
        pose_features.finger_states.get("middle"),
        pose_features.finger_states.get("ring"),
        pose_features.finger_states.get("pinky"),
    )
    curled_support_fingers = sum(
        1
        for finger in support_fingers
        if finger is not None and finger.curled_score >= reject_fist_like_threshold
    )
    if curled_support_fingers > max_curled_support_fingers:
        return False

    return True


def detect_pinch_gesture(
    state: PinchGestureState | None,
    pose_features: HandPoseFeatures | None,
    observed_at: float,
    *,
    config: Any = None,
    contact_metrics: PinchContactMetrics | None = None,
) -> tuple[PinchGestureState, GestureDetectionResult | None]:
    close_threshold = float(
        _config_value(config, "pinch_close_threshold", _DEFAULT_CLOSE_THRESHOLD)
    )
    open_threshold = float(
        _config_value(config, "pinch_open_threshold", _DEFAULT_OPEN_THRESHOLD)
    )
    window_size = max(
        1, int(_config_value(config, "pinch_smoothing_window", _DEFAULT_WINDOW))
    )
    cooldown_seconds = float(
        _config_value(config, "pinch_cooldown_seconds", _DEFAULT_COOLDOWN)
    )
    confidence = float(_config_value(config, "pinch_confidence", _DEFAULT_CONFIDENCE))

    raw_distance = (
        contact_metrics.distance
        if contact_metrics is not None
        else _fallback_thumb_index_distance(pose_features)
    )
    if raw_distance is None:
        return state or PinchGestureState(pinch_closed=False), None

    window = ((state.spread_window if state else [])[-window_size + 1 :]) + [
        raw_distance
    ]
    smoothed = mean(window)
    anchor = contact_metrics.anchor if contact_metrics is not None else None
    contact_pair = contact_metrics.contact_pair if contact_metrics is not None else None
    pose_valid = is_pinch_pose_candidate(pose_features, config=config)

    if state is None:
        initial_closed = pose_valid and smoothed < close_threshold
        return (
            PinchGestureState(
                pinch_closed=initial_closed,
                spread_window=window,
                last_fire_at=0.0,
                anchor=anchor,
                raw_distance=raw_distance,
                smoothed_distance=smoothed,
                contact_pair=contact_pair,
            ),
            None,
        )

    cooldown_ok = observed_at - state.last_fire_at >= cooldown_seconds
    detection: GestureDetectionResult | None = None
    new_closed = state.pinch_closed

    if cooldown_ok:
        if not state.pinch_closed and pose_valid and smoothed < close_threshold:
            detection = GestureDetectionResult(
                gesture="pinch_close",
                confidence=confidence,
                tracking_source="pinch_state",
            )
            new_closed = True
        elif state.pinch_closed and smoothed > open_threshold:
            detection = GestureDetectionResult(
                gesture="pinch_open",
                confidence=confidence,
                tracking_source="pinch_state",
            )
            new_closed = False

    return (
        PinchGestureState(
            pinch_closed=new_closed,
            spread_window=window,
            last_fire_at=observed_at if detection is not None else state.last_fire_at,
            anchor=anchor or state.anchor,
            raw_distance=raw_distance,
            smoothed_distance=smoothed,
            contact_pair=contact_pair or state.contact_pair,
        ),
        detection,
    )
