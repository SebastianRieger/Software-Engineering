from __future__ import annotations

from datetime import datetime, timezone

from dtaidistance import dtw_ndim

from schemas.calibration import (
    CalibrationCollectedSample,
    GestureSequenceProfile,
    GestureSequenceProfileSet,
)
from schemas.gestures import GestureType
from services.gesture.sequence_features import (
    ACTIVE_SEQUENCE_GESTURES,
    DEFAULT_SEQUENCE_CHANNELS,
    PreparedGestureSequence,
    is_sequence_supported_gesture,
    resample_sequence_artifact,
)


def build_sequence_profile_set(
    samples: list[CalibrationCollectedSample],
    *,
    gestures: set[GestureType] | frozenset[GestureType] = ACTIVE_SEQUENCE_GESTURES,
    resample_points: int,
    window: int,
) -> GestureSequenceProfileSet | None:
    prepared_by_gesture = {
        gesture: _prepare_gesture_samples(
            samples=samples,
            gesture=gesture,
            resample_points=resample_points,
        )
        for gesture in sorted(gestures)
    }
    profiles: list[GestureSequenceProfile] = []
    for gesture in sorted(gestures):
        prepared_samples = prepared_by_gesture[gesture]
        if not prepared_samples:
            continue

        distance_matrix = _build_distance_matrix(prepared_samples, window=window)
        medoid_index = min(
            range(len(prepared_samples)),
            key=lambda index: sum(distance_matrix[index]),
        )
        medoid_distances = [
            distance_matrix[medoid_index][index]
            for index in range(len(prepared_samples))
            if index != medoid_index
        ]
        threshold = _resolve_distance_threshold(
            distances=medoid_distances,
            reference=prepared_samples[medoid_index][1],
            impostors=[
                prepared
                for other_gesture, other_samples in prepared_by_gesture.items()
                if other_gesture != gesture
                for _, prepared in other_samples
            ],
            window=window,
        )
        source_sample, _ = prepared_samples[medoid_index]
        profiles.append(
            GestureSequenceProfile(
                profile_id=f"{gesture}:primary",
                gesture=gesture,
                source_sample_ids=[sample.sample_id for sample, _ in prepared_samples],
                medoid_sample_id=source_sample.sample_id,
                distance_threshold=threshold,
                median_distance=_median(medoid_distances),
                p90_distance=_percentile(medoid_distances, 0.90),
                sequence=source_sample.gesture_payload.sequence,
            )
        )

    if not profiles:
        return None

    return GestureSequenceProfileSet(
        generated_at=datetime.now(timezone.utc),
        resample_points=resample_points,
        window=window,
        channel_names=list(DEFAULT_SEQUENCE_CHANNELS),
        profiles=profiles,
    )


def _prepare_gesture_samples(
    *,
    samples: list[CalibrationCollectedSample],
    gesture: GestureType,
    resample_points: int,
) -> list[tuple[CalibrationCollectedSample, PreparedGestureSequence]]:
    prepared: list[tuple[CalibrationCollectedSample, PreparedGestureSequence]] = []
    for sample in samples:
        payload = sample.gesture_payload
        if (
            not sample.accepted
            or sample.target_id != gesture
            or payload is None
            or payload.sequence is None
            or payload.gesture != gesture
            or not is_sequence_supported_gesture(payload.gesture)
        ):
            continue
        prepared.append(
            (
                sample,
                resample_sequence_artifact(
                    payload.sequence,
                    target_points=resample_points,
                ),
            )
        )
    return prepared


def _build_distance_matrix(
    prepared_samples: list[tuple[CalibrationCollectedSample, PreparedGestureSequence]],
    *,
    window: int,
) -> list[list[float]]:
    matrix = [
        [0.0 for _ in range(len(prepared_samples))]
        for _ in range(len(prepared_samples))
    ]
    for row_index, (_, left_sequence) in enumerate(prepared_samples):
        for column_index in range(row_index + 1, len(prepared_samples)):
            distance = float(
                dtw_ndim.distance_fast(
                    left_sequence.values,
                    prepared_samples[column_index][1].values,
                    use_pruning=True,
                    window=window,
                )
            )
            matrix[row_index][column_index] = distance
            matrix[column_index][row_index] = distance
    return matrix


def _resolve_distance_threshold(
    *,
    distances: list[float],
    reference: PreparedGestureSequence,
    impostors: list[PreparedGestureSequence],
    window: int,
) -> float:
    if not distances:
        if not impostors:
            return 0.35

        nearest_impostor_distance = min(
            float(
                dtw_ndim.distance_fast(
                    reference.values,
                    impostor.values,
                    use_pruning=True,
                    window=window,
                )
            )
            for impostor in impostors
        )
        return max(0.35, nearest_impostor_distance * 0.75)
    p90_distance = _percentile(distances, 0.90)
    max_distance = max(distances)
    baseline = max(p90_distance or 0.0, max_distance)
    return max(0.35, baseline * 1.15)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    center = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[center]
    return (ordered[center - 1] + ordered[center]) / 2.0


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * fraction
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    lower_weight = upper_index - position
    upper_weight = position - lower_index
    return ordered[lower_index] * lower_weight + ordered[upper_index] * upper_weight