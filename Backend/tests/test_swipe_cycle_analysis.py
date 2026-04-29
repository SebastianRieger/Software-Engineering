from services.swipe_cycle_analysis import (
    SwipeFrameSample,
    profile_swipe_cycles,
    segment_swipe_cycles,
    summarize_swipe_profiles,
)


def test_segment_swipe_cycles_splits_repeated_horizontal_cycles():
    samples = [
        SwipeFrameSample(timestamp=0.00, point=(0.10, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.10, point=(0.12, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.20, point=(0.18, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.30, point=(0.26, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.40, point=(0.35, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.50, point=(0.36, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.90, point=(0.37, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.00, point=(0.43, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.10, point=(0.50, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.20, point=(0.60, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.30, point=(0.71, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.40, point=(0.72, 0.50), hand_size=0.16),
    ]

    cycles = segment_swipe_cycles(
        samples,
        expected_gesture="swipe_left",
        motion_step_threshold=0.03,
        edge_speed_threshold=0.02,
        min_cycle_displacement=0.12,
    )

    assert len(cycles) == 2
    assert cycles[0].end_index == 5
    assert cycles[1].start_index == 6
    assert cycles[1].end_index == 11


def test_profile_swipe_cycles_extracts_temporal_and_directional_metrics():
    samples = [
        SwipeFrameSample(timestamp=0.00, point=(0.50, 0.80), hand_size=0.16),
        SwipeFrameSample(timestamp=0.10, point=(0.50, 0.72), hand_size=0.16),
        SwipeFrameSample(timestamp=0.20, point=(0.50, 0.62), hand_size=0.16),
        SwipeFrameSample(timestamp=0.30, point=(0.50, 0.49), hand_size=0.16),
        SwipeFrameSample(timestamp=0.40, point=(0.50, 0.36), hand_size=0.16),
        SwipeFrameSample(timestamp=0.50, point=(0.50, 0.31), hand_size=0.16),
    ]

    cycles = segment_swipe_cycles(
        samples,
        expected_gesture="swipe_up",
        motion_step_threshold=0.03,
        edge_speed_threshold=0.02,
        min_cycle_displacement=0.18,
    )
    profiles = profile_swipe_cycles(samples, cycles)

    assert len(profiles) == 1
    assert profiles[0].gesture == "swipe_up"
    assert profiles[0].signed_displacement > 0.4
    assert profiles[0].off_axis_displacement == 0.0
    assert profiles[0].direction_stability >= 0.99
    assert profiles[0].peak_speed > 0.7


def test_segment_swipe_cycles_keeps_horizontal_cycle_with_opposite_observed_direction():
    samples = [
        SwipeFrameSample(timestamp=0.00, point=(0.76, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.10, point=(0.69, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.20, point=(0.60, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.30, point=(0.50, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.40, point=(0.42, 0.50), hand_size=0.16),
    ]

    cycles = segment_swipe_cycles(
        samples,
        expected_gesture="swipe_left",
        motion_step_threshold=0.03,
        edge_speed_threshold=0.02,
        min_cycle_displacement=0.18,
    )

    assert len(cycles) == 1
    assert cycles[0].gesture == "swipe_left"
    assert cycles[0].observed_gesture == "swipe_right"


def test_summarize_swipe_profiles_returns_cycle_statistics():
    samples = [
        SwipeFrameSample(timestamp=0.00, point=(0.10, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.10, point=(0.16, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.20, point=(0.24, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.30, point=(0.33, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.40, point=(0.34, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.90, point=(0.34, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.00, point=(0.42, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.10, point=(0.52, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.20, point=(0.63, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=1.30, point=(0.64, 0.50), hand_size=0.16),
    ]

    cycles = segment_swipe_cycles(
        samples,
        expected_gesture="swipe_left",
        motion_step_threshold=0.03,
        edge_speed_threshold=0.02,
        min_cycle_displacement=0.14,
    )
    profiles = profile_swipe_cycles(samples, cycles)
    summary = summarize_swipe_profiles(profiles)

    assert summary["cycle_count"] == 2
    assert summary["signed_displacement_mean"] is not None
    assert summary["peak_speed_p90"] is not None
    assert summary["direction_stability_mean"] is not None