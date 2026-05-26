import importlib.util
import sys
from pathlib import Path

from services.gesture.offline.swipe_cycle_analysis import (
    SwipeCycle,
    SwipeFrameSample,
    profile_swipe_cycles,
    segment_swipe_cycles,
    summarize_swipe_profiles,
)
from schemas.calibration import GestureSequenceArtifact, GestureSequenceFrame
from schemas.gestures import GestureConfig


def _load_gesture_video_tuner_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "gesture_video_tuner.py"
    )
    spec = importlib.util.spec_from_file_location(
        "gesture_video_tuner_under_test", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
        expected_gesture="swipe_right",
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
        expected_gesture="swipe_right",
        motion_step_threshold=0.03,
        edge_speed_threshold=0.02,
        min_cycle_displacement=0.18,
    )

    assert len(cycles) == 1
    assert cycles[0].gesture == "swipe_right"
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
        expected_gesture="swipe_right",
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


def test_segment_swipe_cycles_respects_gesture_config_kwargs():
    samples = [
        SwipeFrameSample(timestamp=0.00, point=(0.10, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.10, point=(0.12, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.20, point=(0.18, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.30, point=(0.26, 0.50), hand_size=0.16),
        SwipeFrameSample(timestamp=0.40, point=(0.35, 0.50), hand_size=0.16),
    ]

    config = GestureConfig(offline_swipe_motion_step_threshold=0.12)

    cycles = segment_swipe_cycles(
        samples,
        expected_gesture="swipe_right",
        **config.offline_swipe_cycle_kwargs(),
    )

    assert cycles == []


def test_gesture_video_tuner_swipe_evaluators_accept_runtime_detection_override():
    module = _load_gesture_video_tuner_module()
    cycle = SwipeCycle(
        gesture="swipe_right",
        observed_gesture="swipe_right",
        start_index=0,
        end_index=3,
        start_time=0.0,
        end_time=0.3,
        axis="x",
        sign=1.0,
        trajectory=[(0.10, 0.50), (0.18, 0.50), (0.28, 0.50), (0.40, 0.50)],
        timestamps=[0.0, 0.1, 0.2, 0.3],
        average_hand_size=0.16,
    )

    evaluations = module._evaluate_swipe_cycles([cycle], GestureConfig())
    negative_evaluations = module._evaluate_negative_swipe_cycles(
        "sample", [cycle], GestureConfig()
    )

    assert len(evaluations) == 1
    assert evaluations[0].trajectory_points == 4
    assert len(negative_evaluations) == 1
    assert negative_evaluations[0].trajectory_points == 4


def test_gesture_video_tuner_sequence_shadow_skips_leave_one_out_without_same_gesture_reference():
    module = _load_gesture_video_tuner_module()

    def make_result(file_name: str, label: str, direction_x: float):
        artifact = GestureSequenceArtifact(
            point_count=3,
            frame_count=3,
            anchor_index=0,
            anchor_phase="preparing",
            origin_x=0.5,
            origin_y=0.5,
            normalized_by_hand_size=True,
            frames=[
                GestureSequenceFrame(t=0.0, x=0.0, y=0.0, active_phase="preparing"),
                GestureSequenceFrame(
                    t=0.1,
                    x=direction_x,
                    y=0.0,
                    velocity_x=direction_x * 10.0,
                    velocity_y=0.0,
                    active_phase="committing",
                ),
                GestureSequenceFrame(
                    t=0.2,
                    x=direction_x * 2.0,
                    y=0.0,
                    velocity_x=direction_x * 10.0,
                    velocity_y=0.0,
                    active_phase="releasing",
                ),
            ],
        )
        sample = module.VideoGestureSample(
            file_name=file_name,
            label=label,
            contract_id=f"gesture_contract.{label}.v2",
            detected_gesture=label,
            best_candidate_score=0.9,
            best_any_candidate_score=0.9,
            confidence=0.9,
            active_phase="committing",
            reject_reason=None,
            spec_id=f"gesture.{label}",
            hand_size=0.16,
            trajectory_points=3,
            frame_count=3,
        )
        return module.VideoAnalysisResult(
            sample=sample,
            sequence_artifact=artifact,
            swipe_samples=[],
            swipe_cycles=[],
            swipe_profiles=[],
            push_samples=[],
            push_cycles=[],
            push_profiles=[],
        )

    results = [
        make_result("swipeleft1.mkv", "swipe_left", -0.2),
        make_result("swiperight1.mkv", "swipe_right", 0.2),
    ]

    evaluations = module._evaluate_sequence_shadow(results, GestureConfig())

    assert evaluations == []
