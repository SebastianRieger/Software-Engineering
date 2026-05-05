from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from schemas.calibration import GestureSequenceArtifact, GestureSequenceFrame
from schemas.gestures import GestureType


ACTIVE_SEQUENCE_GESTURES: frozenset[GestureType] = frozenset(
    {
        "swipe_left",
        "swipe_right",
        "swipe_up",
        "swipe_down",
        "circle",
    }
)

DEFAULT_SEQUENCE_CHANNELS: tuple[str, ...] = (
    "x",
    "y",
    "velocity_x",
    "velocity_y",
    "hand_openness",
    "index_extension_ratio",
    "push_depth",
    "center_distance",
)


@dataclass(slots=True)
class PreparedGestureSequence:
    values: np.ndarray
    channel_names: tuple[str, ...]
    source_points: int


def is_sequence_supported_gesture(gesture: GestureType | str) -> bool:
    return gesture in ACTIVE_SEQUENCE_GESTURES


def resample_sequence_artifact(
    artifact: GestureSequenceArtifact,
    *,
    target_points: int,
    channel_names: tuple[str, ...] = DEFAULT_SEQUENCE_CHANNELS,
) -> PreparedGestureSequence:
    if target_points < 2:
        raise ValueError("target_points must be at least 2")
    if not artifact.frames:
        raise ValueError("gesture sequence artifact must contain at least one frame")

    source_times = _normalize_source_times(artifact.frames)
    target_times = np.linspace(float(source_times[0]), float(source_times[-1]), target_points)
    resampled_columns = [
        _resample_channel(
            values=np.array(
                [
                    float(getattr(frame, channel_name) or 0.0)
                    for frame in artifact.frames
                ],
                dtype=np.float64,
            ),
            source_times=source_times,
            target_times=target_times,
        )
        for channel_name in channel_names
    ]

    return PreparedGestureSequence(
        values=np.column_stack(resampled_columns),
        channel_names=channel_names,
        source_points=len(artifact.frames),
    )


def _normalize_source_times(frames: list[GestureSequenceFrame]) -> np.ndarray:
    raw_times = np.array([float(frame.t) for frame in frames], dtype=np.float64)
    if len(raw_times) == 1:
        return np.array([0.0], dtype=np.float64)

    normalized = raw_times - raw_times[0]
    if float(normalized[-1]) <= 0.0:
        normalized = np.linspace(0.0, 1.0, len(frames), dtype=np.float64)

    previous = float(normalized[0])
    for index in range(1, len(normalized)):
        current = float(normalized[index])
        if current <= previous:
            current = previous + 1e-6
            normalized[index] = current
        previous = current
    return normalized


def _resample_channel(
    *,
    values: np.ndarray,
    source_times: np.ndarray,
    target_times: np.ndarray,
) -> np.ndarray:
    if len(values) == 1:
        return np.full(len(target_times), float(values[0]), dtype=np.float64)
    return np.interp(target_times, source_times, values)