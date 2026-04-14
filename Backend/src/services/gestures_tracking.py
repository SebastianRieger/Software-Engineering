from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from statistics import mean
from typing import TYPE_CHECKING, Protocol


try:
    import cv2
except ImportError:
    cv2 = None

try:
    import mediapipe as mp
except ImportError:
    mp = None


if TYPE_CHECKING:
    from services.gestures_detection import GestureDetectionResult


GestureName = str
GesturePoint = tuple[float, float]
GestureLandmarks = dict[str, GesturePoint]


HAND_LANDMARK_NAMES = {
    "wrist": 0,
    "thumb_tip": 4,
    "index_mcp": 5,
    "index_tip": 8,
    "middle_mcp": 9,
    "middle_tip": 12,
    "ring_mcp": 13,
    "ring_tip": 16,
    "pinky_mcp": 17,
    "pinky_tip": 20,
}

PALM_CENTER_LANDMARKS = (
    "wrist",
    "index_mcp",
    "middle_mcp",
    "ring_mcp",
    "pinky_mcp",
)


@dataclass(slots=True)
class GestureObservation:
    point: GesturePoint | None
    hand: str | None = None
    preview_bytes: bytes | None = None
    landmarks: GestureLandmarks | None = None
    hand_size: float | None = None
    arm_landmarks: GestureLandmarks | None = None
    tracking_source: str | None = None


class GestureAdapterError(Exception):
    pass


class GestureAdapter(Protocol):
    def is_available(self) -> bool:
        ...

    def open(self, camera_index: int) -> None:
        ...

    def read(self) -> GestureObservation | None:
        ...

    def close(self) -> None:
        ...

    def process_video(
        self,
        video_path: str,
        classifier: Callable[[list[GesturePoint], float | None], GestureDetectionResult | None],
        smoothing_alpha: float,
        tracking_source: str,
    ) -> dict[str, int | list[GestureName] | float | str | None]:
        ...


def compute_hand_size_scale(
    hand_size: float | None,
    hand_size_reference: float,
    hand_size_scale_min: float,
    hand_size_scale_max: float,
) -> float:
    if hand_size is None or hand_size <= 0:
        return 1.0

    scale = hand_size / max(hand_size_reference, 1e-6)
    return max(hand_size_scale_min, min(hand_size_scale_max, scale))


def build_hand_landmark_map(hand_landmarks) -> GestureLandmarks:
    return {
        name: (
            float(hand_landmarks.landmark[index].x),
            float(hand_landmarks.landmark[index].y),
        )
        for name, index in HAND_LANDMARK_NAMES.items()
    }


def compute_hand_tracking_point(landmarks: GestureLandmarks) -> GesturePoint | None:
    points = [landmarks[name] for name in PALM_CENTER_LANDMARKS if name in landmarks]
    if not points:
        return None

    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def estimate_hand_size(landmarks: GestureLandmarks) -> float | None:
    if "index_mcp" in landmarks and "pinky_mcp" in landmarks:
        index_mcp = landmarks["index_mcp"]
        pinky_mcp = landmarks["pinky_mcp"]
        return math.hypot(index_mcp[0] - pinky_mcp[0], index_mcp[1] - pinky_mcp[1])

    tracking_point = compute_hand_tracking_point(landmarks)
    wrist = landmarks.get("wrist")
    if wrist is None or tracking_point is None:
        return None

    return math.hypot(wrist[0] - tracking_point[0], wrist[1] - tracking_point[1])


def smooth_point(
    previous_point: GesturePoint | None,
    point: GesturePoint,
    alpha: float,
) -> GesturePoint:
    if previous_point is None:
        return point

    return (
        alpha * point[0] + (1 - alpha) * previous_point[0],
        alpha * point[1] + (1 - alpha) * previous_point[1],
    )


class MediaPipeHandsAdapter:
    def __init__(self) -> None:
        self.cap = None
        self.hands = None

    def is_available(self) -> bool:
        return cv2 is not None and mp is not None

    def open(self, camera_index: int) -> None:
        if not self.is_available():
            raise GestureAdapterError(
                "MediaPipe Hands oder OpenCV ist in dieser Umgebung nicht verfuegbar."
            )

        self.cap = cv2.VideoCapture(camera_index)
        if not (self.cap and self.cap.isOpened()):
            if self.cap is not None:
                self.cap.release()
            self.cap = None
            raise GestureAdapterError("Kamera konnte nicht geoeffnet werden.")

        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def read(self) -> GestureObservation | None:
        if self.cap is None or self.hands is None:
            return None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return GestureObservation(point=None)

        observation = self._extract_observation(frame)
        preview_bytes = None
        try:
            ok, jpeg = cv2.imencode(".jpg", frame)
            if ok:
                preview_bytes = jpeg.tobytes()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            preview_bytes = None

        observation.preview_bytes = preview_bytes
        return observation

    def close(self) -> None:
        if self.hands is not None:
            self.hands.close()
            self.hands = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def process_video(
        self,
        video_path: str,
        classifier: Callable[[list[GesturePoint], float | None], GestureDetectionResult | None],
        smoothing_alpha: float,
        tracking_source: str,
    ) -> dict[str, int | list[GestureName] | float | str | None]:
        if not self.is_available():
            raise GestureAdapterError(
                "MediaPipe Hands oder OpenCV ist in dieser Umgebung nicht verfuegbar."
            )

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise GestureAdapterError(f"Video konnte nicht geoeffnet werden: {video_path}")

        hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        trajectory: list[GesturePoint] = []
        hand_sizes: list[float] = []
        smoothed_point: GesturePoint | None = None
        frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                frame_count += 1
                observation = self._extract_observation(frame, hands_instance=hands)
                if observation.point is None:
                    continue

                smoothed_point = smooth_point(
                    previous_point=smoothed_point,
                    point=observation.point,
                    alpha=smoothing_alpha,
                )
                trajectory.append(smoothed_point)
                if observation.hand_size is not None:
                    hand_sizes.append(observation.hand_size)

            average_hand_size = mean(hand_sizes) if hand_sizes else None
            detection = classifier(trajectory, average_hand_size)
            gestures = [detection.gesture] if detection is not None else []
            return {
                "gestures": gestures,
                "frames_processed": frame_count,
                "trajectory_points": len(trajectory),
                "confidence": detection.confidence if detection is not None else None,
                "tracking_source": detection.tracking_source if detection is not None else tracking_source,
            }
        finally:
            hands.close()
            cap.release()

    def _extract_observation(
        self,
        frame,
        hands_instance=None,
    ) -> GestureObservation:
        hands_instance = hands_instance or self.hands
        if hands_instance is None:
            return GestureObservation(point=None)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands_instance.process(rgb)
        if not results.multi_hand_landmarks:
            return GestureObservation(point=None)

        hand_landmarks = results.multi_hand_landmarks[0]
        landmarks = build_hand_landmark_map(hand_landmarks)
        tracking_point = compute_hand_tracking_point(landmarks)
        handedness = None
        if results.multi_handedness:
            handedness = results.multi_handedness[0].classification[0].label.lower()

        return GestureObservation(
            point=tracking_point,
            hand=handedness,
            landmarks=landmarks,
            hand_size=estimate_hand_size(landmarks),
            tracking_source="palm_center",
        )