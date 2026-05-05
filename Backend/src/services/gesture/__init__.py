from services.gesture.contracts import GestureContract, default_gesture_contracts, get_gesture_contract
from services.gesture.push_runtime import PushGestureState, detect_push_gesture, is_click_pose_candidate

__all__ = [
    "GestureContract",
    "GestureService",
    "GestureServiceError",
    "PushGestureState",
    "default_gesture_contracts",
    "detect_push_gesture",
    "gesture_service",
    "get_gesture_contract",
    "is_click_pose_candidate",
]


def __getattr__(name: str):
    if name in {"GestureService", "GestureServiceError", "gesture_service"}:
        from services.gesture.runtime import (
            GestureService,
            GestureServiceError,
            gesture_service,
        )

        exports = {
            "GestureService": GestureService,
            "GestureServiceError": GestureServiceError,
            "gesture_service": gesture_service,
        }
        return exports[name]
    raise AttributeError(f"module 'services.gesture' has no attribute {name!r}")