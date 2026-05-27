from datetime import datetime, timezone

from schemas.calibration import (
    CalibrationCollectedSample,
    GestureCalibrationSamplePayload,
    GestureSequenceArtifact,
    GestureSequenceFrame,
)
from services.gesture.sequence_features import resample_sequence_artifact
from services.gesture.sequence_matcher import GestureSequenceMatcher
from services.gesture.sequence_profiles import build_sequence_profile_set


def make_sequence_sample(
    gesture: str,
    *,
    sample_id: str,
    direction_x: float,
    direction_y: float = 0.0,
) -> CalibrationCollectedSample:
    time_step = 0.05
    frames = []
    for index in range(5):
        frames.append(
            GestureSequenceFrame(
                t=index * time_step,
                x=direction_x * index,
                y=direction_y * index,
                velocity_x=0.0 if index == 0 else direction_x / time_step,
                velocity_y=0.0 if index == 0 else direction_y / time_step,
                hand_openness=0.28,
                index_extension_ratio=1.22,
                push_depth=0.0,
                center_distance=0.16,
                active_phase=(
                    "preparing"
                    if index < 2
                    else "committing" if index < 4 else "releasing"
                ),
            )
        )

    return CalibrationCollectedSample(
        sample_id=sample_id,
        modality="gesture",
        target_id=gesture,
        collected_at=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
        gesture_payload=GestureCalibrationSamplePayload(
            gesture=gesture,
            confidence=0.92,
            tracking_source="palm_center",
            sequence=GestureSequenceArtifact(
                point_count=len(frames),
                frame_count=len(frames),
                anchor_index=0,
                anchor_phase="preparing",
                origin_x=0.5,
                origin_y=0.5,
                normalized_by_hand_size=True,
                frames=frames,
            ),
        ),
    )


def test_resample_sequence_artifact_returns_expected_shape():
    sample = make_sequence_sample(
        "swipe_right",
        sample_id="sample-swipe-right-1",
        direction_x=0.22,
    )
    prepared = resample_sequence_artifact(
        sample.gesture_payload.sequence,
        target_points=24,
    )

    assert prepared.values.shape == (24, 8)
    assert prepared.source_points == 5
    assert prepared.channel_names[0] == "x"
    assert prepared.channel_names[-1] == "center_distance"


def test_build_sequence_profile_set_creates_profiles_for_supported_gestures():
    samples = [
        make_sequence_sample(
            "swipe_left", sample_id="sample-left-1", direction_x=-0.24
        ),
        make_sequence_sample(
            "swipe_left", sample_id="sample-left-2", direction_x=-0.22
        ),
        make_sequence_sample(
            "swipe_right", sample_id="sample-right-1", direction_x=0.24
        ),
        make_sequence_sample(
            "swipe_right", sample_id="sample-right-2", direction_x=0.22
        ),
    ]

    profile_set = build_sequence_profile_set(
        samples,
        resample_points=24,
        window=6,
    )

    assert profile_set is not None
    assert [profile.gesture for profile in profile_set.profiles] == [
        "swipe_left",
        "swipe_right",
    ]
    assert all(profile.distance_threshold > 0 for profile in profile_set.profiles)
    assert profile_set.channel_names == [
        "x",
        "y",
        "velocity_x",
        "velocity_y",
        "hand_openness",
        "index_extension_ratio",
        "push_depth",
        "center_distance",
    ]


def test_gesture_sequence_matcher_prefers_closest_profile():
    samples = [
        make_sequence_sample(
            "swipe_left", sample_id="sample-left-1", direction_x=-0.24
        ),
        make_sequence_sample(
            "swipe_left", sample_id="sample-left-2", direction_x=-0.22
        ),
        make_sequence_sample(
            "swipe_right", sample_id="sample-right-1", direction_x=0.24
        ),
        make_sequence_sample(
            "swipe_right", sample_id="sample-right-2", direction_x=0.22
        ),
    ]
    profile_set = build_sequence_profile_set(
        samples,
        resample_points=24,
        window=6,
    )
    matcher = GestureSequenceMatcher(profile_set)
    probe_artifact = make_sequence_sample(
        "swipe_right",
        sample_id="probe-right",
        direction_x=0.23,
    ).gesture_payload.sequence

    matches = matcher.match_artifact(
        probe_artifact,
        gestures={"swipe_left", "swipe_right"},
    )

    assert matches[0].gesture == "swipe_right"
    assert matches[0].score > matches[1].score
    assert matches[0].distance < matches[1].distance


def test_build_sequence_profile_set_uses_impostor_distance_for_singleton_thresholds():
    samples = [
        make_sequence_sample(
            "swipe_left", sample_id="sample-left-1", direction_x=-0.24
        ),
        make_sequence_sample(
            "swipe_right", sample_id="sample-right-1", direction_x=0.24
        ),
        make_sequence_sample(
            "swipe_up", sample_id="sample-up-1", direction_x=0.0, direction_y=-0.24
        ),
    ]

    profile_set = build_sequence_profile_set(
        samples,
        resample_points=24,
        window=6,
    )

    assert profile_set is not None
    thresholds = {
        profile.gesture: profile.distance_threshold for profile in profile_set.profiles
    }
    assert thresholds["swipe_left"] > 0.35
    assert thresholds["swipe_right"] > 0.35
    assert thresholds["swipe_up"] > 0.35
