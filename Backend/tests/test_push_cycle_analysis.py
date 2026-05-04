from services.gesture.offline.push_cycle_analysis import (
    profile_push_cycles,
    segment_push_cycles,
    summarize_push_profiles,
    PushFrameSample,
)
from schemas.gestures import GestureConfig


def test_segment_push_cycles_detects_two_short_clicks() -> None:
    samples = [
        PushFrameSample(timestamp=0.00, push_depth=0.00, pose_valid=False, index_extension_ratio=0.9, folded_fingers_count=0),
        PushFrameSample(timestamp=0.05, push_depth=0.08, pose_valid=True, index_extension_ratio=1.45, folded_fingers_count=3, center_distance=0.08),
        PushFrameSample(timestamp=0.10, push_depth=0.15, pose_valid=True, index_extension_ratio=1.52, folded_fingers_count=3, center_distance=0.06),
        PushFrameSample(timestamp=0.16, push_depth=0.02, pose_valid=False, index_extension_ratio=0.95, folded_fingers_count=1, center_distance=0.12),
        PushFrameSample(timestamp=0.32, push_depth=0.00, pose_valid=False, index_extension_ratio=0.9, folded_fingers_count=0),
        PushFrameSample(timestamp=0.38, push_depth=0.09, pose_valid=True, index_extension_ratio=1.48, folded_fingers_count=3, center_distance=0.07),
        PushFrameSample(timestamp=0.45, push_depth=0.14, pose_valid=True, index_extension_ratio=1.50, folded_fingers_count=3, center_distance=0.06),
        PushFrameSample(timestamp=0.54, push_depth=0.01, pose_valid=False, index_extension_ratio=0.92, folded_fingers_count=1, center_distance=0.13),
    ]

    cycles = segment_push_cycles(samples, expected_gesture="push_click_short")

    assert len(cycles) == 2
    assert all(cycle.observed_gesture == "push_click_short" for cycle in cycles)
    assert cycles[0].start_time == 0.00
    assert cycles[0].end_time == 0.16


def test_segment_push_cycles_classifies_long_click_by_hold_duration() -> None:
    samples = [
        PushFrameSample(timestamp=0.00, push_depth=0.00, pose_valid=False, index_extension_ratio=0.9, folded_fingers_count=0),
        PushFrameSample(timestamp=0.06, push_depth=0.10, pose_valid=True, index_extension_ratio=1.42, folded_fingers_count=3, center_distance=0.08),
        PushFrameSample(timestamp=0.22, push_depth=0.14, pose_valid=True, index_extension_ratio=1.47, folded_fingers_count=3, center_distance=0.07),
        PushFrameSample(timestamp=0.44, push_depth=0.16, pose_valid=True, index_extension_ratio=1.46, folded_fingers_count=3, center_distance=0.08),
        PushFrameSample(timestamp=0.62, push_depth=0.12, pose_valid=True, index_extension_ratio=1.44, folded_fingers_count=3, center_distance=0.08),
        PushFrameSample(timestamp=0.74, push_depth=0.02, pose_valid=False, index_extension_ratio=0.96, folded_fingers_count=1, center_distance=0.12),
    ]

    cycles = segment_push_cycles(samples, expected_gesture="push_click_long", long_click_seconds=0.5)

    assert len(cycles) == 1
    assert cycles[0].observed_gesture == "push_click_long"


def test_profile_and_summary_capture_depth_pose_metrics() -> None:
    samples = [
        PushFrameSample(timestamp=0.00, push_depth=0.00, pose_valid=False, index_extension_ratio=0.9, folded_fingers_count=0, center_distance=0.12, hand_size=0.16),
        PushFrameSample(timestamp=0.04, push_depth=0.08, pose_valid=True, index_extension_ratio=1.40, folded_fingers_count=3, center_distance=0.08, hand_size=0.16),
        PushFrameSample(timestamp=0.08, push_depth=0.15, pose_valid=True, index_extension_ratio=1.52, folded_fingers_count=3, center_distance=0.06, hand_size=0.16),
        PushFrameSample(timestamp=0.12, push_depth=0.14, pose_valid=True, index_extension_ratio=1.50, folded_fingers_count=3, center_distance=0.06, hand_size=0.16),
        PushFrameSample(timestamp=0.18, push_depth=0.02, pose_valid=False, index_extension_ratio=0.95, folded_fingers_count=1, center_distance=0.11, hand_size=0.16),
    ]

    cycles = segment_push_cycles(samples, expected_gesture="push_click_short")
    profiles = profile_push_cycles(samples, cycles)
    summary = summarize_push_profiles(profiles)

    assert len(profiles) == 1
    assert profiles[0].forward_depth == 0.15
    assert profiles[0].release_depth == 0.02
    assert profiles[0].depth_delta == 0.13
    assert profiles[0].pose_valid_ratio >= 0.6
    assert profiles[0].index_extension_mean is not None
    assert summary["cycle_count"] == 1
    assert summary["forward_depth_mean"] == 0.15


def test_segment_push_cycles_keeps_long_click_through_brief_pose_dropout() -> None:
    samples = [
        PushFrameSample(timestamp=0.00, push_depth=0.00, pose_valid=False, index_extension_ratio=0.9, folded_fingers_count=0),
        PushFrameSample(timestamp=0.08, push_depth=0.10, pose_valid=True, index_extension_ratio=1.40, folded_fingers_count=3, center_distance=0.08),
        PushFrameSample(timestamp=0.24, push_depth=0.14, pose_valid=True, index_extension_ratio=1.46, folded_fingers_count=3, center_distance=0.07),
        PushFrameSample(timestamp=0.34, push_depth=0.10, pose_valid=False, index_extension_ratio=1.02, folded_fingers_count=2, center_distance=0.09),
        PushFrameSample(timestamp=0.50, push_depth=0.15, pose_valid=True, index_extension_ratio=1.44, folded_fingers_count=3, center_distance=0.07),
        PushFrameSample(timestamp=0.68, push_depth=0.12, pose_valid=True, index_extension_ratio=1.42, folded_fingers_count=3, center_distance=0.08),
        PushFrameSample(timestamp=0.82, push_depth=0.01, pose_valid=False, index_extension_ratio=0.94, folded_fingers_count=1, center_distance=0.12),
    ]

    cycles = segment_push_cycles(samples, expected_gesture="push_click_long", long_click_seconds=0.5)

    assert len(cycles) == 1
    assert cycles[0].observed_gesture == "push_click_long"


def test_segment_push_cycles_respects_gesture_config_kwargs() -> None:
    samples = [
        PushFrameSample(timestamp=0.00, push_depth=0.00, pose_valid=False, index_extension_ratio=0.9, folded_fingers_count=0),
        PushFrameSample(timestamp=0.05, push_depth=0.08, pose_valid=True, index_extension_ratio=1.45, folded_fingers_count=3, center_distance=0.08),
        PushFrameSample(timestamp=0.10, push_depth=0.15, pose_valid=True, index_extension_ratio=1.52, folded_fingers_count=3, center_distance=0.06),
        PushFrameSample(timestamp=0.16, push_depth=0.02, pose_valid=False, index_extension_ratio=0.95, folded_fingers_count=1, center_distance=0.12),
    ]

    config = GestureConfig(offline_push_min_cycle_points=6)

    cycles = segment_push_cycles(
        samples,
        expected_gesture="push_click_short",
        **config.offline_push_cycle_kwargs(),
    )

    assert cycles == []