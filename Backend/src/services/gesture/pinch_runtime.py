from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean

from services.gesture.detection import GestureDetectionResult
from services.gesture.tracking import HandPoseFeatures

# Distance between thumb_tip and index_tip (as a fraction of palm_span).
# FingerState.spread_score for "thumb" is exactly this distance.
_CLOSE_THRESHOLD = 0.30  # below → pinched
_OPEN_THRESHOLD  = 0.52  # above → open (hysteresis gap prevents flicker)
_WINDOW          = 4     # frames to smooth spread over
_COOLDOWN        = 0.55  # minimum seconds between consecutive fires


@dataclass(slots=True)
class PinchGestureState:
    pinch_closed: bool
    spread_window: list[float] = field(default_factory=list)
    last_fire_at: float = 0.0


def detect_pinch_gesture(
    state: PinchGestureState | None,
    pose_features: HandPoseFeatures | None,
    observed_at: float,
) -> tuple[PinchGestureState, GestureDetectionResult | None]:
    if pose_features is None:
        return state or PinchGestureState(pinch_closed=False), None

    thumb = pose_features.finger_states.get("thumb")
    if thumb is None:
        return state or PinchGestureState(pinch_closed=False), None

    raw_spread = thumb.spread_score
    window = ((state.spread_window if state else [])[-_WINDOW + 1:]) + [raw_spread]
    smoothed = mean(window)

    if state is None:
        initial_closed = smoothed < _CLOSE_THRESHOLD
        return PinchGestureState(
            pinch_closed=initial_closed,
            spread_window=window,
            last_fire_at=0.0,
        ), None

    cooldown_ok = observed_at - state.last_fire_at >= _COOLDOWN
    detection: GestureDetectionResult | None = None
    new_closed = state.pinch_closed

    if cooldown_ok:
        if not state.pinch_closed and smoothed < _CLOSE_THRESHOLD:
            detection = GestureDetectionResult(
                gesture="pinch_close",
                confidence=0.92,
                tracking_source="pinch_state",
            )
            new_closed = True
        elif state.pinch_closed and smoothed > _OPEN_THRESHOLD:
            detection = GestureDetectionResult(
                gesture="pinch_open",
                confidence=0.92,
                tracking_source="pinch_state",
            )
            new_closed = False

    return PinchGestureState(
        pinch_closed=new_closed,
        spread_window=window,
        last_fire_at=observed_at if detection is not None else state.last_fire_at,
    ), detection
