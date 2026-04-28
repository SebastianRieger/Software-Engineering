from __future__ import annotations

import math
import os
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
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
GestureDepthMap = dict[str, float]


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
    landmark_depths: GestureDepthMap | None = None
    hand_size: float | None = None
    arm_landmarks: GestureLandmarks | None = None
    tracking_source: str | None = None
    hands: list["TrackedHandObservation"] | None = None
    captured_at: float | None = None


@dataclass(slots=True)
class TrackedHandObservation:
    point: GesturePoint | None
    hand: str | None = None
    landmarks: GestureLandmarks | None = None
    landmark_depths: GestureDepthMap | None = None
    hand_size: float | None = None
    tracking_source: str | None = None


class GestureAdapterError(Exception):
    pass


_HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
_HAND_LANDMARKER_MODEL_PATH = Path(
    os.environ.get(
        "NIMRAG_HAND_LANDMARKER_MODEL",
        str(Path(__file__).resolve().parents[2] / "models" / "hand_landmarker.task"),
    )
)


def _ensure_hand_landmarker_model() -> Path:
    if _HAND_LANDMARKER_MODEL_PATH.exists():
        return _HAND_LANDMARKER_MODEL_PATH

    _HAND_LANDMARKER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(_HAND_LANDMARKER_MODEL_URL, _HAND_LANDMARKER_MODEL_PATH)
    except Exception as exc:
        if _HAND_LANDMARKER_MODEL_PATH.exists():
            _HAND_LANDMARKER_MODEL_PATH.unlink(missing_ok=True)
        raise GestureAdapterError(
            "MediaPipe Hand-Landmarker-Modell konnte nicht geladen werden. "
            "Bitte Internetverbindung pruefen oder NIMRAG_HAND_LANDMARKER_MODEL setzen."
        ) from exc

    return _HAND_LANDMARKER_MODEL_PATH


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
            float(_hand_landmark_at(hand_landmarks, index).x),
            float(_hand_landmark_at(hand_landmarks, index).y),
        )
        for name, index in HAND_LANDMARK_NAMES.items()
    }


def build_hand_landmark_depth_map(hand_landmarks) -> GestureDepthMap:
    return {
        name: float(_hand_landmark_at(hand_landmarks, index).z)
        for name, index in HAND_LANDMARK_NAMES.items()
    }


def _hand_landmark_at(hand_landmarks, index: int):
    if hasattr(hand_landmarks, "landmark"):
        return hand_landmarks.landmark[index]
    return hand_landmarks[index]


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

    @staticmethod
    def list_available_cameras(max_devices: int = 8) -> list[dict[str, str | int | bool | None]]:
        if cv2 is None:
            return []

        linux_video_indices = MediaPipeHandsAdapter._linux_video_indices()
        candidate_indices = linux_video_indices or list(range(max_devices))

        devices: list[dict[str, str | int | bool | None]] = []
        for index in candidate_indices:
            capture = cv2.VideoCapture(index)
            if not capture or not capture.isOpened():
                if capture is not None:
                    capture.release()
                continue

            ok, _ = capture.read()
            backend_name = None
            try:
                backend_name = str(int(capture.get(cv2.CAP_PROP_BACKEND)))
            except (AttributeError, TypeError, ValueError):
                backend_name = None
            capture.release()

            if not ok:
                continue

            devices.append(
                {
                    "index": index,
                    "name": MediaPipeHandsAdapter._resolve_camera_name(index),
                    "available": True,
                    "backend": backend_name,
                }
            )

        return devices

    @staticmethod
    def _resolve_camera_name(index: int) -> str:
        sysfs_path = Path(f"/sys/class/video4linux/video{index}/name")
        if os.path.exists(sysfs_path):
            try:
                return sysfs_path.read_text(encoding="utf-8").strip() or f"Camera {index}"
            except OSError:
                return f"Camera {index}"
        return f"Camera {index}"

    @staticmethod
    def _linux_video_indices() -> list[int]:
        video_root = Path("/sys/class/video4linux")
        if not video_root.exists():
            return []

        indices: list[int] = []
        for child in sorted(video_root.iterdir()):
            if not child.name.startswith("video"):
                continue
            try:
                indices.append(int(child.name.replace("video", "")))
            except ValueError:
                continue
        return indices

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

        try:
            self.hands = self._create_hands_tracker()
        except GestureAdapterError:
            if self.cap is not None:
                self.cap.release()
            self.cap = None
            raise

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
        observation.captured_at = time.monotonic()
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

        hands = self._create_hands_tracker()
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

    @staticmethod
    def _create_hands_tracker():
        if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
            return mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

        try:
            from mediapipe.tasks import python as mp_tasks_python
            from mediapipe.tasks.python import vision as mp_tasks_vision

            base_options = mp_tasks_python.BaseOptions(
                model_asset_path=str(_ensure_hand_landmarker_model())
            )
            options = mp_tasks_vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_tasks_vision.RunningMode.IMAGE,
                num_hands=2,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            return mp_tasks_vision.HandLandmarker.create_from_options(options)
        except GestureAdapterError:
            raise
        except Exception as exc:
            raise GestureAdapterError(f"MediaPipe Hands konnte nicht initialisiert werden: {exc}") from exc

    def _extract_observation(
        self,
        frame,
        hands_instance=None,
    ) -> GestureObservation:
        hands_instance = hands_instance or self.hands
        if hands_instance is None:
            return GestureObservation(point=None)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if hasattr(hands_instance, "process"):
            results = hands_instance.process(rgb)
            hand_landmarks_list = results.multi_hand_landmarks or []
            handedness_list = results.multi_handedness or []
        else:
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            results = hands_instance.detect(image)
            hand_landmarks_list = results.hand_landmarks or []
            handedness_list = results.handedness or []

        if not hand_landmarks_list:
            return GestureObservation(point=None)

        tracked_hands: list[TrackedHandObservation] = []
        for index, hand_landmarks in enumerate(hand_landmarks_list):
            landmarks = build_hand_landmark_map(hand_landmarks)
            tracking_point = compute_hand_tracking_point(landmarks)
            landmark_depths = build_hand_landmark_depth_map(hand_landmarks)
            handedness = None
            if handedness_list and len(handedness_list) > index:
                handedness_entry = handedness_list[index]
                if hasattr(handedness_entry, "classification"):
                    handedness = handedness_entry.classification[0].label.lower()
                elif handedness_entry:
                    handedness = str(handedness_entry[0].category_name).lower()

            tracked_hands.append(
                TrackedHandObservation(
                    point=tracking_point,
                    hand=handedness,
                    landmarks=landmarks,
                    landmark_depths=landmark_depths,
                    hand_size=estimate_hand_size(landmarks),
                    tracking_source="palm_center",
                )
            )

        tracked_hands.sort(key=lambda candidate: candidate.hand_size or 0.0, reverse=True)
        primary_hand = tracked_hands[0]
        return GestureObservation(
            point=primary_hand.point,
            hand=primary_hand.hand,
            landmarks=primary_hand.landmarks,
            landmark_depths=primary_hand.landmark_depths,
            hand_size=primary_hand.hand_size,
            tracking_source="palm_center",
            hands=tracked_hands,
        )