from __future__ import annotations

from dataclasses import dataclass

from dtaidistance import dtw_ndim

from schemas.calibration import GestureSequenceArtifact, GestureSequenceProfileSet
from schemas.gestures import GestureType
from services.gesture.sequence_features import resample_sequence_artifact


@dataclass(slots=True)
class GestureSequenceMatch:
    gesture: GestureType
    profile_id: str
    distance: float
    score: float
    margin: float | None
    distance_threshold: float


class GestureSequenceMatcher:
    def __init__(self, profile_set: GestureSequenceProfileSet) -> None:
        self._profile_set = profile_set

    def match_artifact(
        self,
        artifact: GestureSequenceArtifact,
        *,
        gestures: set[GestureType] | None = None,
    ) -> list[GestureSequenceMatch]:
        prepared = resample_sequence_artifact(
            artifact,
            target_points=self._profile_set.resample_points,
        )
        matches_by_gesture: dict[GestureType, GestureSequenceMatch] = {}
        for profile in self._profile_set.profiles:
            if gestures is not None and profile.gesture not in gestures:
                continue
            reference = resample_sequence_artifact(
                profile.sequence,
                target_points=self._profile_set.resample_points,
            )
            distance = float(
                dtw_ndim.distance_fast(
                    prepared.values,
                    reference.values,
                    use_pruning=True,
                    window=self._profile_set.window,
                )
            )
            score = _distance_to_score(distance, profile.distance_threshold)
            current = matches_by_gesture.get(profile.gesture)
            if current is None or distance < current.distance:
                matches_by_gesture[profile.gesture] = GestureSequenceMatch(
                    gesture=profile.gesture,
                    profile_id=profile.profile_id,
                    distance=distance,
                    score=score,
                    margin=None,
                    distance_threshold=profile.distance_threshold,
                )

        ordered_matches = sorted(matches_by_gesture.values(), key=lambda match: match.distance)
        for index, match in enumerate(ordered_matches):
            next_distance = ordered_matches[index + 1].distance if index + 1 < len(ordered_matches) else None
            match.margin = None if next_distance is None else max(0.0, next_distance - match.distance)
        return ordered_matches


def _distance_to_score(distance: float, threshold: float) -> float:
    safe_threshold = max(threshold, 1e-6)
    return max(0.0, min(1.0, 1.0 - (distance / safe_threshold)))