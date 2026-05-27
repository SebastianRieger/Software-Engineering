from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from statistics import quantiles
from typing import Any, TypedDict, cast

import cv2

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = BACKEND_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from schemas.calibration import (
    CalibrationCollectedSample,
    GestureCalibrationSamplePayload,
    GestureSequenceArtifact,
)
from schemas.gestures import GestureConfig, GestureType
from services.gesture.runtime import GestureService
from services.gesture.contracts import default_gesture_contracts, get_gesture_contract
from services.gesture.detection import (
    detect_gesture_with_confidence,
    extract_gesture_features,
    extract_temporal_gesture_window,
)
from services.gesture.offline.push_cycle_analysis import (
    PushCycle,
    PushGestureName,
    PushCycleProfile,
    PushFrameSample,
    profile_push_cycles,
    segment_push_cycles,
    summarize_push_profiles,
)
from services.gesture.offline.swipe_cycle_analysis import (
    SwipeCycle,
    SwipeCycleProfile,
    SwipeFrameSample,
    profile_swipe_cycles,
    segment_swipe_cycles,
    summarize_swipe_profiles,
)
from services.gesture.sequence_matcher import GestureSequenceMatcher
from services.gesture.sequence_profiles import build_sequence_profile_set
from services.gesture.tracking import MediaPipeHandsAdapter, extract_hand_pose_features


VIDEO_LABELS: dict[str, GestureType] = {
    "Swipeleft.mkv": "swipe_left",
    "swiperight.mkv": "swipe_right",
    "swipeup.mkv": "swipe_up",
    "swipedown.mkv": "swipe_down",
    "kreis.mkv": "circle",
    "kreiserneut.mkv": "circle",
    "anklickenkurz.mkv": "push_click_short",
    "anklickenlang.mkv": "push_click_long",
    "rauszoomen.mkv": "zoom_out_hands",
    "reinzoomen.mkv": "zoom_in_hands",
}

VIDEO_PREFIX_LABELS: tuple[tuple[str, GestureType], ...] = (
    ("swipeleft", "swipe_left"),
    ("swiperight", "swipe_right"),
    ("swipeup", "swipe_up"),
    ("swipedown", "swipe_down"),
    ("kreis", "circle"),
    ("klickkurz", "push_click_short"),
    ("klicklang", "push_click_long"),
    ("reinzoom", "zoom_in_hands"),
    ("reinzoomen", "zoom_in_hands"),
    ("rauszoom", "zoom_out_hands"),
    ("rauszoomen", "zoom_out_hands"),
)


def infer_video_label(file_name: str) -> GestureType | None:
    exact_match = VIDEO_LABELS.get(file_name)
    if exact_match is not None:
        return exact_match

    stem = Path(file_name).stem.lower()
    for prefix, label in VIDEO_PREFIX_LABELS:
        if not stem.startswith(prefix):
            continue
        suffix = stem[len(prefix) :]
        if suffix == "" or re.fullmatch(r"\d+", suffix):
            return label
    return None


def discover_video_labels(videos_dir: Path) -> list[tuple[str, GestureType]]:
    discovered: list[tuple[str, GestureType]] = []
    for path in sorted(videos_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".mkv", ".mp4", ".mov", ".avi"}:
            continue
        label = infer_video_label(path.name)
        if label is not None:
            discovered.append((path.name, label))
    return discovered


@dataclass(slots=True)
class VideoGestureSample:
    file_name: str
    label: GestureType
    contract_id: str
    detected_gesture: str | None
    best_candidate_score: float
    best_any_candidate_score: float
    confidence: float | None
    active_phase: str
    reject_reason: str | None
    spec_id: str | None
    hand_size: float | None
    trajectory_points: int
    frame_count: int
    dx_total: float | None = None
    dy_total: float | None = None
    span_x: float | None = None
    span_y: float | None = None
    total_sweep: float | None = None
    radius_cv: float | None = None
    push_depth: float | None = None
    center_distance: float | None = None
    index_extension_ratio: float | None = None
    start_distance: float | None = None
    delta_distance: float | None = None
    duration_seconds: float | None = None
    avg_velocity_x: float | None = None
    avg_velocity_y: float | None = None
    peak_speed: float | None = None
    direction_stability: float | None = None
    hold_stability: float | None = None
    jitter: float | None = None


@dataclass(slots=True)
class VideoAnalysisResult:
    sample: VideoGestureSample
    sequence_artifact: GestureSequenceArtifact | None
    swipe_samples: list[SwipeFrameSample]
    swipe_cycles: list[SwipeCycle]
    swipe_profiles: list[SwipeCycleProfile]
    push_samples: list[PushFrameSample]
    push_cycles: list[PushCycle]
    push_profiles: list[PushCycleProfile]
    swipe_summary: dict[str, float | int | None] | None = None
    push_summary: dict[str, float | int | None] | None = None


@dataclass(slots=True)
class SwipeCycleEvaluation:
    cycle_index: int
    expected_gesture: str
    detected_gesture: str | None
    confidence: float | None
    correct: bool
    trajectory_points: int
    reason: str | None


@dataclass(slots=True)
class NegativeSwipeEvaluation:
    source_label: str
    expected_swipe: str
    observed_gesture: str
    cycle_index: int
    detected_gesture: str | None
    confidence: float | None
    false_positive: bool
    trajectory_points: int


@dataclass(slots=True)
class NegativeSwipeVideoEvaluation:
    source_label: str
    detected_gesture: str | None
    false_positive: bool
    confidence: float | None


@dataclass(slots=True)
class PushCycleEvaluation:
    cycle_index: int
    expected_gesture: str
    detected_gesture: str | None
    correct: bool
    boundary_truncated: bool
    duration_seconds: float
    forward_depth: float
    hold_duration_seconds: float
    reason: str | None


@dataclass(slots=True)
class NegativePushEvaluation:
    source_label: str
    expected_push: str
    observed_gesture: str
    cycle_index: int
    detected_gesture: str | None
    false_positive: bool
    duration_seconds: float
    forward_depth: float


@dataclass(slots=True)
class SwipeTuningMetrics:
    label_accuracy: float | None
    observed_accuracy: float | None
    wrong_label_cycles: int
    not_detected_cycles: int
    negative_cycle_false_positive_rate: float | None
    negative_video_false_positive_rate: float | None


@dataclass(slots=True)
class SwipeTuningResult:
    config: dict[str, float | int]
    baseline: SwipeTuningMetrics
    tuned: SwipeTuningMetrics


@dataclass(slots=True)
class SequenceShadowEvaluation:
    file_name: str
    label: GestureType
    heuristic_detected_gesture: str | None
    sequence_detected_gesture: str | None
    heuristic_correct: bool
    sequence_correct: bool
    sequence_score: float | None
    sequence_distance: float | None
    sequence_margin: float | None
    sequence_profile_id: str | None


class SwipeCycleKwargs(TypedDict):
    min_cycle_points: int
    motion_step_threshold: float
    edge_speed_threshold: float
    active_gap_seconds: float
    axis_ratio_threshold: float
    min_cycle_displacement: float
    edge_gap_ratio: float
    edge_gap_max_seconds: float


class PushCycleKwargs(TypedDict):
    min_cycle_points: int
    activation_depth_threshold: float
    release_depth_threshold: float
    active_gap_seconds: float
    min_pose_valid_ratio: float
    min_index_extension_ratio: float
    min_folded_fingers: int
    center_distance_max: float
    long_click_seconds: float
    inactive_grace_seconds: float


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    cuts = quantiles(sorted(values), n=100, method="inclusive")
    index = max(0, min(98, round(probability * 100) - 1))
    return cuts[index]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _effective_frame_stride(label: GestureType, requested_frame_stride: int) -> int:
    if label.startswith("swipe_"):
        return min(max(1, requested_frame_stride), 4)
    return max(1, requested_frame_stride)


def _open_video_capture(video_path: Path):
    video_capture = getattr(cv2, "VideoCapture")
    return video_capture(str(video_path))


def _capture_fps(capture) -> float:
    fps_property = getattr(cv2, "CAP_PROP_FPS")
    return float(capture.get(fps_property) or 30.0)


def _seek_capture_frame(capture, frame_index: int) -> None:
    if frame_index <= 0:
        return
    frame_property = getattr(cv2, "CAP_PROP_POS_FRAMES")
    capture.set(frame_property, float(frame_index))


def _set_runtime_config(service: GestureService, config: GestureConfig) -> None:
    setattr(service, "_active_config", config.model_copy(deep=True))


def _set_push_state(service: GestureService, value: Any) -> None:
    setattr(service, "_push_state", value)


def _create_hands_tracker(adapter: MediaPipeHandsAdapter):
    return getattr(adapter, "_create_hands_tracker")()


def _extract_observation(adapter: MediaPipeHandsAdapter, frame, hands):
    extractor = getattr(adapter, "_extract_observation")
    return extractor(frame, hands_instance=hands)


def _reset_sequence_state(service: GestureService, missing_observed_at: float) -> None:
    reset_sequence = getattr(service, "_reset_sequence_state")
    reset_sequence(missing_observed_at=missing_observed_at)


def _runtime_lifecycle(service: GestureService) -> Any:
    return getattr(service, "_lifecycle")


def _analyze_runtime_gesture(service: GestureService, **kwargs) -> Any:
    analyzer = getattr(service, "_analyze_runtime_gesture")
    return analyzer(**kwargs)


def _advance_pending_gesture(service: GestureService, **kwargs) -> Any:
    advance = getattr(service, "_advance_pending_gesture")
    return advance(**kwargs)


def _flush_pending_gesture(service: GestureService, observed_at: float) -> Any:
    flush = getattr(service, "_flush_pending_gesture")
    return flush(observed_at)


def _select_runtime_single_hand_trajectory(service: GestureService, **kwargs) -> list[tuple[float, float]]:
    selector = getattr(service, "_select_runtime_single_hand_trajectory")
    return selector(**kwargs)


def _build_runtime_sequence_artifact(service: GestureService, **kwargs) -> GestureSequenceArtifact | None:
    builder = getattr(service, "_build_sequence_artifact_from_runtime_window")
    return builder(**kwargs)


def _offline_swipe_cycle_kwargs(config: GestureConfig) -> SwipeCycleKwargs:
    kwargs = config.offline_swipe_cycle_kwargs()
    return {
        "min_cycle_points": int(kwargs["min_cycle_points"]),
        "motion_step_threshold": float(kwargs["motion_step_threshold"]),
        "edge_speed_threshold": float(kwargs["edge_speed_threshold"]),
        "active_gap_seconds": float(kwargs["active_gap_seconds"]),
        "axis_ratio_threshold": float(kwargs["axis_ratio_threshold"]),
        "min_cycle_displacement": float(kwargs["min_cycle_displacement"]),
        "edge_gap_ratio": float(kwargs["edge_gap_ratio"]),
        "edge_gap_max_seconds": float(kwargs["edge_gap_max_seconds"]),
    }


def _offline_push_cycle_kwargs(config: GestureConfig) -> PushCycleKwargs:
    kwargs = config.offline_push_cycle_kwargs()
    return {
        "min_cycle_points": int(kwargs["min_cycle_points"]),
        "activation_depth_threshold": float(kwargs["activation_depth_threshold"]),
        "release_depth_threshold": float(kwargs["release_depth_threshold"]),
        "active_gap_seconds": float(kwargs["active_gap_seconds"]),
        "min_pose_valid_ratio": float(kwargs["min_pose_valid_ratio"]),
        "min_index_extension_ratio": float(kwargs["min_index_extension_ratio"]),
        "min_folded_fingers": int(kwargs["min_folded_fingers"]),
        "center_distance_max": float(kwargs["center_distance_max"]),
        "long_click_seconds": float(kwargs["long_click_seconds"]),
        "inactive_grace_seconds": float(kwargs["inactive_grace_seconds"]),
    }


def _simulate_video(
    video_path: Path,
    label: GestureType,
    config: GestureConfig,
    *,
    adapter: MediaPipeHandsAdapter,
    frame_stride: int,
    max_frames: int | None,
    start_frame: int = 0,
    end_frame: int | None = None,
) -> VideoAnalysisResult:
    capture = _open_video_capture(video_path)
    _seek_capture_frame(capture, start_frame)
    fps = _capture_fps(capture)
    hands = _create_hands_tracker(adapter)

    service = GestureService()
    _set_runtime_config(service, config)
    _set_push_state(service, None)
    setattr(service, "_pending_gesture", None)
    service.last_gesture_time_by_name = {}
    lifecycle = _runtime_lifecycle(service)
    lifecycle.reset_all()

    best_sample: VideoGestureSample | None = None
    best_sequence_artifact: GestureSequenceArtifact | None = None
    last_sample: VideoGestureSample | None = None
    swipe_samples: list[SwipeFrameSample] = []
    push_samples: list[PushFrameSample] = []
    frame_index = start_frame
    processed_frames = 0
    last_observed_at = float(start_frame) / fps if fps > 0 else 0.0

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                break

            current_frame_index = frame_index
            frame_index += 1
            if end_frame is not None and current_frame_index > end_frame:
                break
            if current_frame_index % frame_stride != 0:
                continue
            if max_frames is not None and processed_frames >= max_frames:
                break

            observed_at = current_frame_index / fps
            last_observed_at = observed_at
            processed_frames += 1
            observation = _extract_observation(adapter, frame, hands)

            if observation.point is None:
                _reset_sequence_state(service, observed_at)
                lifecycle.reset_motion_window(clear_post_fire=True)
                continue

            pose = extract_hand_pose_features(observation)

            recorded_point = lifecycle.append_point(
                point=observation.point,
                observed_at=observed_at,
                hand_size=observation.hand_size,
                hand_count=len(observation.hands) if observation.hands else 1,
                pose_features=pose,
                smoothing_alpha=config.smoothing_alpha,
                max_points=config.max_trajectory_points,
            )
            if recorded_point is None:
                continue

            trajectory_snapshot, timestamp_snapshot, hand_size_snapshot = lifecycle.copy_motion_snapshot()
            sequence_channels_snapshot = lifecycle.copy_sequence_channel_snapshot()
            analysis = _analyze_runtime_gesture(
                service,
                observation=observation,
                observed_at=observed_at,
                trajectory=trajectory_snapshot,
                trajectory_timestamps=timestamp_snapshot,
                hand_size=hand_size_snapshot,
                pose_features=pose,
            )
            lifecycle.set_last_active_phase(analysis.active_phase)
            finalized_detection = _advance_pending_gesture(
                service,
                analysis=analysis,
                observed_at=observed_at,
            )
            effective_detection = finalized_detection or analysis.detection
            folded_fingers_count = 0
            push_pose_valid = False
            if pose is not None:
                folded_fingers_count = sum(
                    1
                    for finger_name in ("middle", "ring", "pinky")
                    if pose.finger_states.get(finger_name) is not None and pose.finger_states[finger_name].label == "curled"
                )
                push_pose_valid = (
                    pose.center_distance <= config.center_tolerance
                    and pose.index_extension_ratio > config.push_pose_extension_ratio
                    and folded_fingers_count >= 2
                )
            if label.startswith("swipe_"):
                swipe_samples.append(
                    SwipeFrameSample(
                        timestamp=observed_at,
                        point=recorded_point,
                        hand_size=observation.hand_size,
                        phase=analysis.active_phase,
                        candidate_score=analysis.candidate_scores.get(label, 0.0),
                        tracking_quality=analysis.tracking_quality,
                    )
                )
            push_samples.append(
                PushFrameSample(
                    timestamp=observed_at,
                    push_depth=pose.push_depth if pose is not None else 0.0,
                    pose_valid=push_pose_valid,
                    hand_size=observation.hand_size,
                    center_distance=pose.center_distance if pose is not None else None,
                    index_extension_ratio=pose.index_extension_ratio if pose is not None else None,
                    folded_fingers_count=folded_fingers_count,
                    hand=observation.hand,
                    tracking_quality=analysis.tracking_quality,
                )
            )
            label_score = analysis.candidate_scores.get(label, 0.0)
            best_any_score = max(analysis.candidate_scores.values(), default=0.0)
            detected = effective_detection.gesture if effective_detection is not None else None

            selected_trajectory = _select_runtime_single_hand_trajectory(
                service,
                trajectory=trajectory_snapshot,
                trajectory_timestamps=timestamp_snapshot,
                observed_at=observed_at,
            )
            selected_timestamps = timestamp_snapshot[-len(selected_trajectory):] if selected_trajectory else []
            selected_point_count = len(selected_trajectory)
            selected_sequence_artifact = (
                _build_runtime_sequence_artifact(
                    service,
                    trajectory=selected_trajectory,
                    trajectory_timestamps=selected_timestamps,
                    hand_size=hand_size_snapshot,
                    hand_openness=sequence_channels_snapshot["hand_openness"][-selected_point_count:],
                    index_extension_ratios=sequence_channels_snapshot["index_extension_ratio"][-selected_point_count:],
                    push_depths=sequence_channels_snapshot["push_depth"][-selected_point_count:],
                    center_distances=sequence_channels_snapshot["center_distance"][-selected_point_count:],
                    active_phases=lifecycle.copy_active_phase_snapshot()[-selected_point_count:],
                )
                if selected_point_count > 0
                else None
            )
            hand_count = len(observation.hands) if observation.hands else 1
            temporal = extract_temporal_gesture_window(
                trajectory=selected_trajectory,
                trajectory_timestamps=selected_timestamps,
                hand_count=hand_count,
                pose_features=pose,
                hand_size=hand_size_snapshot,
                cooldown_active=False,
                distance_window=lifecycle.copy_two_hand_history(),
            )
            features = extract_gesture_features(
                trajectory=selected_trajectory,
                min_detection_points=2,
                hand_size=hand_size_snapshot,
                hand_size_reference=config.hand_size_reference,
                hand_size_scale_min=config.hand_size_scale_min,
                hand_size_scale_max=config.hand_size_scale_max,
            )

            sample = VideoGestureSample(
                file_name=video_path.name,
                label=label,
                contract_id=get_gesture_contract(label).contract_id,
                detected_gesture=detected,
                best_candidate_score=label_score,
                best_any_candidate_score=best_any_score,
                confidence=effective_detection.confidence if effective_detection is not None and effective_detection.gesture == label else None,
                active_phase=analysis.active_phase,
                reject_reason=analysis.reject_reason,
                spec_id=effective_detection.spec_id if effective_detection is not None else analysis.spec_id,
                hand_size=hand_size_snapshot,
                trajectory_points=len(selected_trajectory),
                frame_count=temporal.frame_count,
                dx_total=features.dx_total if features is not None else None,
                dy_total=features.dy_total if features is not None else None,
                span_x=features.span_x if features is not None else None,
                span_y=features.span_y if features is not None else None,
                total_sweep=features.total_sweep if features is not None else None,
                radius_cv=features.radius_cv if features is not None else None,
                push_depth=pose.push_depth if pose is not None else None,
                center_distance=pose.center_distance if pose is not None else None,
                index_extension_ratio=pose.index_extension_ratio if pose is not None else None,
                start_distance=temporal.start_distance,
                delta_distance=temporal.delta_distance,
                duration_seconds=temporal.duration_seconds,
                avg_velocity_x=temporal.avg_velocity_x,
                avg_velocity_y=temporal.avg_velocity_y,
                peak_speed=temporal.peak_speed,
                direction_stability=temporal.direction_stability,
                hold_stability=temporal.hold_stability,
                jitter=temporal.jitter,
            )
            last_sample = sample
            current_rank = (sample.best_candidate_score, 1.0 if sample.detected_gesture == label else 0.0, best_any_score, float(sample.trajectory_points))
            best_rank = None
            if best_sample is not None:
                best_rank = (
                    best_sample.best_candidate_score,
                    1.0 if best_sample.detected_gesture == label else 0.0,
                    best_sample.best_any_candidate_score,
                    float(best_sample.trajectory_points),
                )
            if best_sample is None or best_rank is None or current_rank >= best_rank:
                best_sample = sample
                best_sequence_artifact = selected_sequence_artifact
    finally:
        hands.close()
        capture.release()

    flushed_detection = _flush_pending_gesture(service, last_observed_at)
    if flushed_detection is not None and last_sample is not None:
        flushed_sample = replace(
            last_sample,
            detected_gesture=flushed_detection.gesture,
            confidence=flushed_detection.confidence if flushed_detection.gesture == label else None,
            spec_id=flushed_detection.spec_id,
        )
        current_rank = (
            flushed_sample.best_candidate_score,
            1.0 if flushed_sample.detected_gesture == label else 0.0,
            flushed_sample.best_any_candidate_score,
            float(flushed_sample.trajectory_points),
        )
        best_rank = None
        if best_sample is not None:
            best_rank = (
                best_sample.best_candidate_score,
                1.0 if best_sample.detected_gesture == label else 0.0,
                best_sample.best_any_candidate_score,
                float(best_sample.trajectory_points),
            )
        if best_sample is None or best_rank is None or current_rank >= best_rank:
            best_sample = flushed_sample

    swipe_cycles: list[SwipeCycle] = []
    swipe_profiles: list[SwipeCycleProfile] = []
    push_cycles: list[PushCycle] = []
    push_profiles: list[PushCycleProfile] = []
    swipe_summary: dict[str, float | int | None] | None = None
    push_summary: dict[str, float | int | None] | None = None
    if label.startswith("swipe_"):
        swipe_cycles = segment_swipe_cycles(
            swipe_samples,
            expected_gesture=label,
            **_offline_swipe_cycle_kwargs(config),
        )
        swipe_profiles = profile_swipe_cycles(swipe_samples, swipe_cycles)
        swipe_summary = summarize_swipe_profiles(swipe_profiles)
    if label.startswith("push_click"):
        push_cycles = segment_push_cycles(
            push_samples,
            expected_gesture=cast(PushGestureName, label),
            **_offline_push_cycle_kwargs(config),
        )
        push_profiles = profile_push_cycles(push_samples, push_cycles)
        push_summary = summarize_push_profiles(push_profiles)

    if best_sample is None:
        best_sample = VideoGestureSample(
            file_name=video_path.name,
            label=label,
            contract_id=get_gesture_contract(label).contract_id,
            detected_gesture=None,
            best_candidate_score=0.0,
            best_any_candidate_score=0.0,
            confidence=None,
            active_phase="idle",
            reject_reason="no_candidate",
            spec_id=None,
            hand_size=None,
            trajectory_points=0,
            frame_count=0,
        )
    return VideoAnalysisResult(
        sample=best_sample,
        sequence_artifact=best_sequence_artifact,
        swipe_samples=swipe_samples,
        swipe_cycles=swipe_cycles,
        swipe_profiles=swipe_profiles,
        push_samples=push_samples,
        push_cycles=push_cycles,
        push_profiles=push_profiles,
        swipe_summary=swipe_summary,
        push_summary=push_summary,
    )


def _evaluate_push_cycles(
    profiles: list[PushCycleProfile],
) -> list[PushCycleEvaluation]:
    evaluations: list[PushCycleEvaluation] = []
    for cycle_index, profile in enumerate(profiles):
        detected_gesture = profile.observed_gesture
        evaluations.append(
            PushCycleEvaluation(
                cycle_index=cycle_index,
                expected_gesture=profile.gesture,
                detected_gesture=detected_gesture,
                correct=detected_gesture == profile.gesture,
                boundary_truncated=profile.boundary_truncated,
                duration_seconds=profile.duration_seconds,
                forward_depth=profile.forward_depth,
                hold_duration_seconds=profile.hold_duration_seconds,
                reason=None,
            )
        )
    return evaluations


def _collect_negative_push_cycles(
    push_samples: list[PushFrameSample],
    config: GestureConfig,
) -> list[PushCycle]:
    candidate_cycles: list[PushCycle] = []
    for expected_push in ("push_click_short", "push_click_long"):
        candidate_cycles.extend(
            segment_push_cycles(
                push_samples,
                expected_gesture=expected_push,
                **_offline_push_cycle_kwargs(config),
            )
        )

    deduped: list[PushCycle] = []
    seen_ranges: set[tuple[int, int, str]] = set()
    for cycle in sorted(candidate_cycles, key=lambda item: (item.start_index, item.end_index, item.observed_gesture)):
        key = (cycle.start_index, cycle.end_index, cycle.observed_gesture)
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        deduped.append(cycle)
    return deduped


def _evaluate_negative_push_cycles(
    source_label: str,
    profiles: list[PushCycleProfile],
) -> list[NegativePushEvaluation]:
    evaluations: list[NegativePushEvaluation] = []
    for cycle_index, profile in enumerate(profiles):
        evaluations.append(
            NegativePushEvaluation(
                source_label=source_label,
                expected_push=profile.gesture,
                observed_gesture=profile.observed_gesture,
                cycle_index=cycle_index,
                detected_gesture=profile.observed_gesture,
                false_positive=True,
                duration_seconds=profile.duration_seconds,
                forward_depth=profile.forward_depth,
            )
        )
    return evaluations


def _evaluate_swipe_cycles(
    cycles: list[SwipeCycle],
    config: GestureConfig,
    *,
    use_observed_gesture: bool = False,
) -> list[SwipeCycleEvaluation]:
    evaluations: list[SwipeCycleEvaluation] = []
    runtime_min_detection_points = max(4, config.min_detection_points - 2)
    for cycle_index, cycle in enumerate(cycles):
        detection_kwargs = config.trajectory_detection_kwargs()
        detection_kwargs["min_detection_points"] = min(runtime_min_detection_points, len(cycle.trajectory))
        detection = detect_gesture_with_confidence(
            trajectory=cycle.trajectory,
            hand_size=cycle.average_hand_size,
            tracking_source="swipe_cycle",
            **detection_kwargs,
        )
        detected_gesture = detection.gesture if detection is not None else None
        evaluations.append(
            SwipeCycleEvaluation(
                cycle_index=cycle_index,
                expected_gesture=cycle.observed_gesture if use_observed_gesture else cycle.gesture,
                detected_gesture=detected_gesture,
                confidence=detection.confidence if detection is not None else None,
                correct=detected_gesture == (cycle.observed_gesture if use_observed_gesture else cycle.gesture),
                trajectory_points=len(cycle.trajectory),
                reason=None if detection is not None else "not_detected",
            )
        )
    return evaluations


def _collect_negative_swipe_cycles(
    swipe_samples: list[SwipeFrameSample],
    config: GestureConfig,
) -> list[SwipeCycle]:
    candidate_cycles: list[SwipeCycle] = []
    for expected_swipe in ("swipe_left", "swipe_right", "swipe_up", "swipe_down"):
        candidate_cycles.extend(
            segment_swipe_cycles(
                swipe_samples,
                expected_gesture=expected_swipe,
                **_offline_swipe_cycle_kwargs(config),
            )
        )

    deduped: list[SwipeCycle] = []
    seen_ranges: set[tuple[int, int, str]] = set()
    for cycle in sorted(candidate_cycles, key=lambda item: (item.start_index, item.end_index, item.observed_gesture)):
        key = (cycle.start_index, cycle.end_index, cycle.observed_gesture)
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        deduped.append(cycle)
    return deduped


def _evaluate_negative_swipe_cycles(
    source_label: str,
    cycles: list[SwipeCycle],
    config: GestureConfig,
) -> list[NegativeSwipeEvaluation]:
    evaluations: list[NegativeSwipeEvaluation] = []
    runtime_min_detection_points = max(4, config.min_detection_points - 2)
    for cycle_index, cycle in enumerate(cycles):
        detection_kwargs = config.trajectory_detection_kwargs()
        detection_kwargs["min_detection_points"] = min(runtime_min_detection_points, len(cycle.trajectory))
        detection = detect_gesture_with_confidence(
            trajectory=cycle.trajectory,
            hand_size=cycle.average_hand_size,
            tracking_source="negative_swipe_cycle",
            **detection_kwargs,
        )
        detected_gesture = detection.gesture if detection is not None else None
        evaluations.append(
            NegativeSwipeEvaluation(
                source_label=source_label,
                expected_swipe=cycle.gesture,
                observed_gesture=cycle.observed_gesture,
                cycle_index=cycle_index,
                detected_gesture=detected_gesture,
                confidence=detection.confidence if detection is not None else None,
                false_positive=detected_gesture is not None,
                trajectory_points=len(cycle.trajectory),
            )
        )
    return evaluations


def _evaluate_negative_swipe_video(
    sample: VideoGestureSample,
) -> NegativeSwipeVideoEvaluation:
    detected_gesture = sample.detected_gesture if sample.detected_gesture and sample.detected_gesture.startswith("swipe_") else None
    return NegativeSwipeVideoEvaluation(
        source_label=sample.label,
        detected_gesture=detected_gesture,
        false_positive=detected_gesture is not None,
        confidence=sample.confidence if detected_gesture is not None else None,
    )


def _build_confusion_matrix(
    evaluations: list[SwipeCycleEvaluation],
) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for evaluation in evaluations:
        row = matrix.setdefault(evaluation.expected_gesture, {})
        column = evaluation.detected_gesture or "not_detected"
        row[column] = row.get(column, 0) + 1
    return matrix


def _build_negative_confusion_matrix(
    evaluations: list[NegativeSwipeEvaluation],
) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for evaluation in evaluations:
        row = matrix.setdefault(evaluation.source_label, {})
        column = evaluation.detected_gesture or "not_detected"
        row[column] = row.get(column, 0) + 1
    return matrix


def _make_sequence_calibration_sample(
    result: VideoAnalysisResult,
) -> CalibrationCollectedSample | None:
    label = result.sample.label
    if result.sequence_artifact is None or (
        not label.startswith("swipe_") and label != "circle"
    ):
        return None
    return CalibrationCollectedSample(
        sample_id=f"video::{result.sample.file_name}",
        modality="gesture",
        target_id=label,
        collected_at=datetime.now(timezone.utc),
        gesture_payload=GestureCalibrationSamplePayload(
            gesture=label,
            confidence=max(result.sample.best_candidate_score, result.sample.confidence or 0.0),
            tracking_source="video_tuner",
            sequence=result.sequence_artifact,
        ),
    )


def _evaluate_sequence_shadow(
    results: list[VideoAnalysisResult],
    config: GestureConfig,
) -> list[SequenceShadowEvaluation]:
    evaluations: list[SequenceShadowEvaluation] = []
    candidates = [
        (result, calibration_sample)
        for result in results
        for calibration_sample in [_make_sequence_calibration_sample(result)]
        if calibration_sample is not None
    ]
    for result, calibration_sample in candidates:
        payload = calibration_sample.gesture_payload
        if payload is None or payload.sequence is None:
            continue
        training_samples = [
            sample
            for other_result, sample in candidates
            if other_result.sample.file_name != result.sample.file_name
        ]
        if not any(sample.target_id == result.sample.label for sample in training_samples):
            continue
        profile_set = build_sequence_profile_set(
            training_samples,
            resample_points=config.sequence_resample_points,
            window=config.sequence_window,
        )
        best_match = None
        if profile_set is not None:
            matches = GestureSequenceMatcher(profile_set).match_artifact(
                payload.sequence,
                gestures={profile.gesture for profile in profile_set.profiles},
            )
            best_match = matches[0] if matches else None

        heuristic_detected = result.sample.detected_gesture
        heuristic_correct = heuristic_detected == result.sample.label
        sequence_detected = None
        if best_match is not None and best_match.score > 0.0:
            if best_match.margin is None or best_match.margin >= config.sequence_min_margin:
                sequence_detected = best_match.gesture
        evaluations.append(
            SequenceShadowEvaluation(
                file_name=result.sample.file_name,
                label=result.sample.label,
                heuristic_detected_gesture=heuristic_detected,
                sequence_detected_gesture=sequence_detected,
                heuristic_correct=heuristic_correct,
                sequence_correct=sequence_detected == result.sample.label,
                sequence_score=best_match.score if best_match is not None else None,
                sequence_distance=best_match.distance if best_match is not None else None,
                sequence_margin=best_match.margin if best_match is not None else None,
                sequence_profile_id=best_match.profile_id if best_match is not None else None,
            )
        )
    return evaluations


def _build_sequence_shadow_confusion_matrix(
    evaluations: list[SequenceShadowEvaluation],
) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for evaluation in evaluations:
        row = matrix.setdefault(evaluation.label, {})
        column = evaluation.sequence_detected_gesture or "not_detected"
        row[column] = row.get(column, 0) + 1
    return matrix


def _summarize_sequence_shadow_evaluations(
    evaluations: list[SequenceShadowEvaluation],
) -> dict[str, float | int | None | bool]:
    if not evaluations:
        return {
            "video_count": 0,
            "heuristic_correct_videos": 0,
            "heuristic_accuracy": None,
            "sequence_correct_videos": 0,
            "sequence_accuracy": None,
            "changed_predictions": 0,
            "net_correct_delta": 0,
            "promotion_ready": False,
        }

    heuristic_correct_videos = sum(1 for evaluation in evaluations if evaluation.heuristic_correct)
    sequence_correct_videos = sum(1 for evaluation in evaluations if evaluation.sequence_correct)
    changed_predictions = sum(
        1
        for evaluation in evaluations
        if evaluation.heuristic_detected_gesture != evaluation.sequence_detected_gesture
    )
    heuristic_accuracy = heuristic_correct_videos / float(len(evaluations))
    sequence_accuracy = sequence_correct_videos / float(len(evaluations))
    return {
        "video_count": len(evaluations),
        "heuristic_correct_videos": heuristic_correct_videos,
        "heuristic_accuracy": heuristic_accuracy,
        "sequence_correct_videos": sequence_correct_videos,
        "sequence_accuracy": sequence_accuracy,
        "changed_predictions": changed_predictions,
        "net_correct_delta": sequence_correct_videos - heuristic_correct_videos,
        "promotion_ready": sequence_accuracy >= heuristic_accuracy,
    }


def _summarize_swipe_evaluations(
    evaluations: list[SwipeCycleEvaluation],
) -> dict[str, float | int | None]:
    if not evaluations:
        return {
            "cycle_count": 0,
            "correct_cycles": 0,
            "accuracy": None,
            "wrong_label_cycles": 0,
            "not_detected_cycles": 0,
        }

    correct_cycles = sum(1 for evaluation in evaluations if evaluation.correct)
    wrong_label_cycles = sum(
        1
        for evaluation in evaluations
        if evaluation.detected_gesture is not None and evaluation.detected_gesture != evaluation.expected_gesture
    )
    not_detected_cycles = sum(1 for evaluation in evaluations if evaluation.detected_gesture is None)
    return {
        "cycle_count": len(evaluations),
        "correct_cycles": correct_cycles,
        "accuracy": correct_cycles / float(len(evaluations)),
        "wrong_label_cycles": wrong_label_cycles,
        "not_detected_cycles": not_detected_cycles,
    }


def _summarize_negative_swipe_evaluations(
    evaluations: list[NegativeSwipeEvaluation],
) -> dict[str, float | int | None]:
    if not evaluations:
        return {
            "cycle_count": 0,
            "false_positive_cycles": 0,
            "false_positive_rate": None,
            "clean_cycles": 0,
        }

    false_positive_cycles = sum(1 for evaluation in evaluations if evaluation.false_positive)
    clean_cycles = len(evaluations) - false_positive_cycles
    return {
        "cycle_count": len(evaluations),
        "false_positive_cycles": false_positive_cycles,
        "false_positive_rate": false_positive_cycles / float(len(evaluations)),
        "clean_cycles": clean_cycles,
    }


def _summarize_negative_swipe_videos(
    evaluations: list[NegativeSwipeVideoEvaluation],
) -> dict[str, float | int | None]:
    if not evaluations:
        return {
            "video_count": 0,
            "false_positive_videos": 0,
            "false_positive_rate": None,
            "clean_videos": 0,
        }

    false_positive_videos = sum(1 for evaluation in evaluations if evaluation.false_positive)
    clean_videos = len(evaluations) - false_positive_videos
    return {
        "video_count": len(evaluations),
        "false_positive_videos": false_positive_videos,
        "false_positive_rate": false_positive_videos / float(len(evaluations)),
        "clean_videos": clean_videos,
    }


def _summarize_push_evaluations(
    evaluations: list[PushCycleEvaluation],
) -> dict[str, float | int | None]:
    if not evaluations:
        return {
            "cycle_count": 0,
            "correct_cycles": 0,
            "accuracy": None,
            "wrong_label_cycles": 0,
            "complete_cycle_count": 0,
            "complete_accuracy": None,
            "complete_wrong_label_cycles": 0,
        }

    correct_cycles = sum(1 for evaluation in evaluations if evaluation.correct)
    wrong_label_cycles = len(evaluations) - correct_cycles
    complete_evaluations = [evaluation for evaluation in evaluations if not evaluation.boundary_truncated]
    complete_correct_cycles = sum(1 for evaluation in complete_evaluations if evaluation.correct)
    complete_wrong_label_cycles = len(complete_evaluations) - complete_correct_cycles
    return {
        "cycle_count": len(evaluations),
        "correct_cycles": correct_cycles,
        "accuracy": correct_cycles / float(len(evaluations)),
        "wrong_label_cycles": wrong_label_cycles,
        "complete_cycle_count": len(complete_evaluations),
        "complete_accuracy": (complete_correct_cycles / float(len(complete_evaluations))) if complete_evaluations else None,
        "complete_wrong_label_cycles": complete_wrong_label_cycles,
    }


def _summarize_negative_push_evaluations(
    evaluations: list[NegativePushEvaluation],
) -> dict[str, float | int | None]:
    if not evaluations:
        return {
            "cycle_count": 0,
            "false_positive_cycles": 0,
            "false_positive_rate": None,
            "clean_cycles": 0,
        }

    false_positive_cycles = sum(1 for evaluation in evaluations if evaluation.false_positive)
    clean_cycles = len(evaluations) - false_positive_cycles
    return {
        "cycle_count": len(evaluations),
        "false_positive_cycles": false_positive_cycles,
        "false_positive_rate": false_positive_cycles / float(len(evaluations)),
        "clean_cycles": clean_cycles,
    }


def _candidate_float_values(*values: float, lower: float, upper: float, precision: int = 4) -> list[float]:
    deduped: set[float] = set()
    for value in values:
        bounded = _clamp(value, lower, upper)
        deduped.add(round(bounded, precision))
    return sorted(deduped)


def _metrics_from_evaluations(
    label_evaluations: list[SwipeCycleEvaluation],
    observed_evaluations: list[SwipeCycleEvaluation],
    negative_cycle_evaluations: list[NegativeSwipeEvaluation],
    negative_video_evaluations: list[NegativeSwipeVideoEvaluation],
) -> SwipeTuningMetrics:
    label_summary = _summarize_swipe_evaluations(label_evaluations)
    observed_summary = _summarize_swipe_evaluations(observed_evaluations)
    negative_cycle_summary = _summarize_negative_swipe_evaluations(negative_cycle_evaluations)
    negative_video_summary = _summarize_negative_swipe_videos(negative_video_evaluations)
    return SwipeTuningMetrics(
        label_accuracy=label_summary["accuracy"],
        observed_accuracy=observed_summary["accuracy"],
        wrong_label_cycles=int(label_summary["wrong_label_cycles"] or 0),
        not_detected_cycles=int(label_summary["not_detected_cycles"] or 0),
        negative_cycle_false_positive_rate=negative_cycle_summary["false_positive_rate"],
        negative_video_false_positive_rate=negative_video_summary["false_positive_rate"],
    )


def _tuning_rank(metrics: SwipeTuningMetrics) -> tuple[float, float, float, int, float, int]:
    negative_video_rate = metrics.negative_video_false_positive_rate or 0.0
    negative_cycle_rate = metrics.negative_cycle_false_positive_rate or 0.0
    observed_accuracy = metrics.observed_accuracy or 0.0
    label_accuracy = metrics.label_accuracy or 0.0
    return (
        -negative_video_rate,
        -negative_cycle_rate,
        observed_accuracy,
        -metrics.not_detected_cycles,
        label_accuracy,
        -metrics.wrong_label_cycles,
    )


def _derive_tuned_swipe_result(
    base_config: GestureConfig,
    swipe_profiles: list[SwipeCycleProfile],
    positive_cycles: list[SwipeCycle],
    negative_cycles: list[NegativeSwipeEvaluation],
    negative_videos: list[NegativeSwipeVideoEvaluation],
) -> SwipeTuningResult | None:
    if not swipe_profiles or not positive_cycles:
        return None

    all_displacements = [profile.normalized_signed_displacement for profile in swipe_profiles]
    all_spans = [profile.normalized_axis_span for profile in swipe_profiles]
    up_displacements = [profile.normalized_signed_displacement for profile in swipe_profiles if profile.observed_gesture == "swipe_up"]
    down_displacements = [profile.normalized_signed_displacement for profile in swipe_profiles if profile.observed_gesture == "swipe_down"]

    displacement_p10 = _percentile(all_displacements, 0.10) or base_config.swipe_threshold
    span_p10 = _percentile(all_spans, 0.10) or base_config.swipe_min_span
    up_p10 = _percentile(up_displacements, 0.10) or base_config.up_threshold
    down_p10 = _percentile(down_displacements, 0.10) or base_config.down_threshold

    swipe_threshold_candidates = _candidate_float_values(
        base_config.swipe_threshold,
        displacement_p10 * 0.45,
        displacement_p10 * 0.55,
        displacement_p10 * 0.65,
        lower=0.05,
        upper=0.3,
    )
    swipe_min_span_candidates = _candidate_float_values(
        base_config.swipe_min_span,
        span_p10 * 0.4,
        span_p10 * 0.5,
        span_p10 * 0.6,
        lower=0.03,
        upper=0.25,
    )
    up_threshold_candidates = _candidate_float_values(
        base_config.up_threshold,
        up_p10 * 0.45,
        up_p10 * 0.55,
        up_p10 * 0.65,
        lower=0.05,
        upper=0.3,
    )
    down_threshold_candidates = _candidate_float_values(
        base_config.down_threshold,
        down_p10 * 0.45,
        down_p10 * 0.55,
        down_p10 * 0.65,
        lower=0.05,
        upper=0.3,
    )
    min_detection_point_candidates = sorted({4, 5, int(base_config.min_detection_points)})

    baseline_label_evaluations = _evaluate_swipe_cycles(positive_cycles, base_config)
    baseline_observed_evaluations = _evaluate_swipe_cycles(positive_cycles, base_config, use_observed_gesture=True)
    baseline_metrics = _metrics_from_evaluations(
        baseline_label_evaluations,
        baseline_observed_evaluations,
        negative_cycles,
        negative_videos,
    )

    best_config = base_config
    best_metrics = baseline_metrics
    best_rank = _tuning_rank(baseline_metrics)

    for swipe_threshold in swipe_threshold_candidates:
        for swipe_min_span in swipe_min_span_candidates:
            for up_threshold in up_threshold_candidates:
                for down_threshold in down_threshold_candidates:
                    for min_detection_points in min_detection_point_candidates:
                        candidate_config = base_config.model_copy(
                            update={
                                "swipe_threshold": swipe_threshold,
                                "swipe_min_span": swipe_min_span,
                                "up_threshold": up_threshold,
                                "down_threshold": down_threshold,
                                "min_detection_points": min_detection_points,
                            }
                        )
                        label_evaluations = _evaluate_swipe_cycles(positive_cycles, candidate_config)
                        observed_evaluations = _evaluate_swipe_cycles(positive_cycles, candidate_config, use_observed_gesture=True)
                        metrics = _metrics_from_evaluations(
                            label_evaluations,
                            observed_evaluations,
                            negative_cycles,
                            negative_videos,
                        )
                        rank = _tuning_rank(metrics)
                        if rank > best_rank:
                            best_rank = rank
                            best_config = candidate_config
                            best_metrics = metrics

    return SwipeTuningResult(
        config={
            "swipe_threshold": best_config.swipe_threshold,
            "swipe_min_span": best_config.swipe_min_span,
            "up_threshold": best_config.up_threshold,
            "down_threshold": best_config.down_threshold,
            "min_detection_points": int(best_config.min_detection_points),
        },
        baseline=baseline_metrics,
        tuned=best_metrics,
    )


def _recommendations(
    samples: list[VideoGestureSample],
    config: GestureConfig,
    *,
    swipe_profiles: list[SwipeCycleProfile],
    swipe_tuning_result: SwipeTuningResult | None = None,
) -> dict[str, float]:
    circle_samples = [sample for sample in samples if sample.label == "circle"]
    push_samples = [sample for sample in samples if sample.label.startswith("push_click")]
    long_push_samples = [sample for sample in samples if sample.label == "push_click_long"]
    zoom_samples = [sample for sample in samples if sample.label.startswith("zoom_")]

    circle_sweeps = [abs(sample.total_sweep) for sample in circle_samples if sample.total_sweep is not None]
    circle_cvs = [sample.radius_cv for sample in circle_samples if sample.radius_cv is not None]
    push_depths = [sample.push_depth for sample in push_samples if sample.push_depth is not None]
    center_distances = [sample.center_distance for sample in push_samples if sample.center_distance is not None]
    extension_ratios = [sample.index_extension_ratio for sample in push_samples if sample.index_extension_ratio is not None]
    long_durations = [sample.duration_seconds for sample in long_push_samples if sample.duration_seconds is not None]
    zoom_deltas = [abs(sample.delta_distance) for sample in zoom_samples if sample.delta_distance is not None]
    zoom_out_starts = [sample.start_distance for sample in zoom_samples if sample.label == "zoom_out_hands" and sample.start_distance is not None]
    zoom_in_starts = [sample.start_distance for sample in zoom_samples if sample.label == "zoom_in_hands" and sample.start_distance is not None]
    zoom_frames = [float(sample.frame_count) for sample in zoom_samples if sample.frame_count]

    hold_peak_speeds = [sample.peak_speed for sample in push_samples if sample.peak_speed is not None]
    hold_stabilities = [sample.hold_stability for sample in push_samples if sample.hold_stability is not None]
    preparing_durations = [profile.duration_seconds for profile in swipe_profiles]
    preparing_durations.extend(sample.duration_seconds for sample in circle_samples + zoom_samples if sample.duration_seconds is not None)
    release_ratios = [
        abs(sample.avg_velocity_x or sample.avg_velocity_y or 0.0) / max(sample.peak_speed, 1e-6)
        for sample in samples
        if sample.peak_speed is not None and sample.peak_speed > 0 and (sample.avg_velocity_x is not None or sample.avg_velocity_y is not None)
    ]

    recommended_swipe_threshold = config.swipe_threshold
    recommended_swipe_min_span = config.swipe_min_span
    recommended_down_threshold = config.down_threshold
    recommended_up_threshold = config.up_threshold
    if swipe_tuning_result is not None:
        recommended_swipe_threshold = float(swipe_tuning_result.config["swipe_threshold"])
        recommended_swipe_min_span = float(swipe_tuning_result.config["swipe_min_span"])
        recommended_down_threshold = float(swipe_tuning_result.config["down_threshold"])
        recommended_up_threshold = float(swipe_tuning_result.config["up_threshold"])

    recommendations = {
        "swipe_threshold": recommended_swipe_threshold,
        "swipe_min_span": recommended_swipe_min_span,
        "down_threshold": recommended_down_threshold,
        "up_threshold": recommended_up_threshold,
        "circle_sweep_min": _clamp((_percentile(circle_sweeps, 0.10) or config.circle_sweep_min) * 0.9, 3.2, 8.5),
        "circle_radius_cv_max": _clamp((_percentile(circle_cvs, 0.90) or config.circle_radius_cv_max) * 1.08, 0.05, 1.0),
        "push_depth_threshold": _clamp((_percentile(push_depths, 0.10) or config.push_depth_threshold) * 0.85, 0.02, 0.35),
        "center_tolerance": _clamp((_percentile(center_distances, 0.90) or config.center_tolerance) * 1.08, 0.04, 0.35),
        "push_pose_extension_ratio": _clamp((_percentile(extension_ratios, 0.10) or config.push_pose_extension_ratio) * 0.96, 1.05, 2.5),
        "long_click_seconds": _clamp((_percentile(long_durations, 0.10) or config.long_click_seconds) * 0.92, 0.2, 2.5),
        "zoom_distance_delta_threshold": _clamp((_percentile(zoom_deltas, 0.10) or config.zoom_distance_delta_threshold) * 0.9, 0.03, 0.6),
        "zoom_start_near_distance": _clamp((_percentile(zoom_out_starts, 0.90) or config.zoom_start_near_distance) * 1.03, 0.05, 0.8),
        "zoom_start_far_distance": _clamp((_percentile(zoom_in_starts, 0.10) or config.zoom_start_far_distance) * 0.97, 0.12, 1.5),
        "two_hand_min_frames": float(int(_clamp(round((_percentile(zoom_frames, 0.10) or float(config.two_hand_min_frames)) - 1), 2, 32))),
        "temporal_hold_peak_speed_max": _clamp((_percentile(hold_peak_speeds, 0.90) or 0.08) * 1.05, 0.03, 0.2),
        "temporal_hold_min_stability": _clamp((_percentile(hold_stabilities, 0.10) or 0.68) * 0.95, 0.3, 0.95),
        "temporal_preparing_window_seconds": _clamp((_percentile(preparing_durations, 0.10) or 0.14) * 0.55, 0.05, 0.35),
        "temporal_releasing_speed_ratio": _clamp((_percentile(release_ratios, 0.35) or 0.35), 0.1, 0.8),
    }
    return recommendations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos-dir", type=Path, required=True)
    parser.add_argument("--video", action="append", default=[])
    parser.add_argument("--frame-stride", type=int, default=2)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--end-frame", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    config = GestureConfig()
    adapter = MediaPipeHandsAdapter()
    requested_files = set(args.video)
    selected_videos: list[tuple[str, GestureType]] = [
        (file_name, label)
        for file_name, label in discover_video_labels(args.videos_dir)
        if not requested_files or file_name in requested_files
    ]
    results = [
        _simulate_video(
            args.videos_dir / file_name,
            label,
            config,
            adapter=adapter,
            frame_stride=_effective_frame_stride(label, args.frame_stride),
            max_frames=args.max_frames,
            start_frame=max(0, args.start_frame),
            end_frame=args.end_frame,
        )
        for file_name, label in selected_videos
    ]
    try:
        samples = [result.sample for result in results]
        swipe_profiles = [profile for result in results for profile in result.swipe_profiles]
        positive_evaluations_by_file = {
            result.sample.file_name: _evaluate_swipe_cycles(result.swipe_cycles, config)
            for result in results
            if result.sample.label.startswith("swipe_")
        }
        negative_evaluations_by_file = {
            result.sample.file_name: _evaluate_negative_swipe_cycles(
                result.sample.label,
                _collect_negative_swipe_cycles(result.swipe_samples, config),
                config,
            )
            for result in results
            if not result.sample.label.startswith("swipe_")
        }
        negative_video_evaluations_by_file = {
            result.sample.file_name: _evaluate_negative_swipe_video(result.sample)
            for result in results
            if not result.sample.label.startswith("swipe_")
        }
        push_evaluations_by_file = {
            result.sample.file_name: _evaluate_push_cycles(result.push_profiles)
            for result in results
            if result.sample.label.startswith("push_click")
        }
        negative_push_evaluations_by_file = {
            result.sample.file_name: _evaluate_negative_push_cycles(
                result.sample.label,
                profile_push_cycles(result.push_samples, _collect_negative_push_cycles(result.push_samples, config)),
            )
            for result in results
            if not result.sample.label.startswith("push_click")
        }
        positive_cycles = [cycle for result in results for cycle in result.swipe_cycles]
        negative_cycle_evaluations = [evaluation for evaluations in negative_evaluations_by_file.values() for evaluation in evaluations]
        negative_video_evaluations = list(negative_video_evaluations_by_file.values())
        swipe_tuning_result = _derive_tuned_swipe_result(
            config,
            swipe_profiles,
            positive_cycles,
            negative_cycle_evaluations,
            negative_video_evaluations,
        ) if positive_cycles else None
        sequence_shadow_evaluations = _evaluate_sequence_shadow(results, config)
        swipe_cycle_reports = [
            {
                "file_name": result.sample.file_name,
                "label": result.sample.label,
                "cycle_summary": result.swipe_summary,
                "evaluation_summary": _summarize_swipe_evaluations(positive_evaluations_by_file[result.sample.file_name]),
                "evaluations": [asdict(evaluation) for evaluation in positive_evaluations_by_file[result.sample.file_name]],
                "cycles": [asdict(profile) for profile in result.swipe_profiles],
            }
            for result in results
            if result.sample.label.startswith("swipe_")
        ]
        swipe_models = {
            gesture: summarize_swipe_profiles([profile for profile in swipe_profiles if profile.gesture == gesture])
            for gesture in sorted({profile.gesture for profile in swipe_profiles})
        }
        swipe_evaluation_models = {
            gesture: _summarize_swipe_evaluations(
                [
                    evaluation
                    for result in results
                    if result.sample.label == gesture
                    for evaluation in positive_evaluations_by_file.get(result.sample.file_name, [])
                ]
            )
            for gesture in sorted({result.sample.label for result in results if result.sample.label.startswith("swipe_")})
        }
        swipe_confusion_matrix = _build_confusion_matrix(
            [evaluation for evaluations in positive_evaluations_by_file.values() for evaluation in evaluations]
        )
        negative_swipe_reports = [
            {
                "file_name": result.sample.file_name,
                "label": result.sample.label,
                "evaluation_summary": _summarize_negative_swipe_evaluations(negative_evaluations_by_file[result.sample.file_name]),
                "video_evaluation": asdict(negative_video_evaluations_by_file[result.sample.file_name]),
                "evaluations": [asdict(evaluation) for evaluation in negative_evaluations_by_file[result.sample.file_name]],
            }
            for result in results
            if not result.sample.label.startswith("swipe_")
        ]
        negative_swipe_confusion = _build_negative_confusion_matrix(
            negative_cycle_evaluations
        )
        negative_swipe_summary = {
            label: {
                "cycle_summary": _summarize_negative_swipe_evaluations(
                    [
                        evaluation
                        for result in results
                        if result.sample.label == label
                        for evaluation in negative_evaluations_by_file.get(result.sample.file_name, [])
                    ]
                ),
                "video_summary": _summarize_negative_swipe_videos(
                    [
                        negative_video_evaluations_by_file[result.sample.file_name]
                        for result in results
                        if result.sample.label == label
                    ]
                ),
            }
            for label in sorted({result.sample.label for result in results if not result.sample.label.startswith("swipe_")})
        }
        push_cycle_reports = [
            {
                "file_name": result.sample.file_name,
                "label": result.sample.label,
                "cycle_summary": result.push_summary,
                "evaluation_summary": _summarize_push_evaluations(push_evaluations_by_file[result.sample.file_name]),
                "evaluations": [asdict(evaluation) for evaluation in push_evaluations_by_file[result.sample.file_name]],
                "cycles": [asdict(profile) for profile in result.push_profiles],
            }
            for result in results
            if result.sample.label.startswith("push_click")
        ]
        push_models = {
            gesture: summarize_push_profiles([profile for profile in [push_profile for result in results for push_profile in result.push_profiles] if profile.gesture == gesture])
            for gesture in sorted({profile.gesture for result in results for profile in result.push_profiles})
        }
        negative_push_reports = [
            {
                "file_name": result.sample.file_name,
                "label": result.sample.label,
                "evaluation_summary": _summarize_negative_push_evaluations(negative_push_evaluations_by_file[result.sample.file_name]),
                "evaluations": [asdict(evaluation) for evaluation in negative_push_evaluations_by_file[result.sample.file_name]],
            }
            for result in results
            if not result.sample.label.startswith("push_click")
        ]
        negative_push_summary = {
            label: _summarize_negative_push_evaluations(
                [
                    evaluation
                    for result in results
                    if result.sample.label == label
                    for evaluation in negative_push_evaluations_by_file.get(result.sample.file_name, [])
                ]
            )
            for label in sorted({result.sample.label for result in results if not result.sample.label.startswith("push_click")})
        }
        sequence_shadow_reports = [asdict(evaluation) for evaluation in sequence_shadow_evaluations]
        sequence_shadow_summary = _summarize_sequence_shadow_evaluations(
            sequence_shadow_evaluations
        )
        sequence_shadow_confusion = _build_sequence_shadow_confusion_matrix(
            sequence_shadow_evaluations
        )
        payload: dict[str, Any] = {
            "gesture_contracts": {gesture: asdict(contract) for gesture, contract in default_gesture_contracts().items()},
            "samples": [asdict(sample) for sample in samples],
            "swipe_cycle_reports": swipe_cycle_reports,
            "swipe_models": swipe_models,
            "swipe_evaluation_models": swipe_evaluation_models,
            "swipe_confusion_matrix": swipe_confusion_matrix,
            "sequence_shadow_reports": sequence_shadow_reports,
            "sequence_shadow_summary": sequence_shadow_summary,
            "sequence_shadow_confusion": sequence_shadow_confusion,
            "negative_swipe_reports": negative_swipe_reports,
            "negative_swipe_summary": negative_swipe_summary,
            "negative_swipe_confusion": negative_swipe_confusion,
            "push_cycle_reports": push_cycle_reports,
            "push_models": push_models,
            "negative_push_reports": negative_push_reports,
            "negative_push_summary": negative_push_summary,
            "swipe_tuning_result": asdict(swipe_tuning_result) if swipe_tuning_result is not None else None,
            "recommendations": _recommendations(samples, config, swipe_profiles=swipe_profiles, swipe_tuning_result=swipe_tuning_result),
        }
        output_text = json.dumps(payload, indent=2, sort_keys=True)
        if args.output is not None:
            args.output.write_text(output_text, encoding="utf-8")
        else:
            print(output_text)
        return 0
    finally:
        pass


if __name__ == "__main__":
    raise SystemExit(main())