from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev

from core.config import settings
from services.gestures_tracking import GestureName, compute_hand_size_scale


@dataclass(slots=True)
class GestureFeatures:
    dx_total: float
    dy_total: float
    span_x: float
    span_y: float
    radius_mean: float | None
    radius_cv: float | None
    total_sweep: float | None
    hand_size: float | None
    hand_size_scale: float


@dataclass(slots=True)
class GestureDetectionCandidate:
    gesture: GestureName
    confidence: float


@dataclass(slots=True)
class GestureDetectionResult:
    gesture: GestureName
    confidence: float
    tracking_source: str | None = None


def detect_gesture_from_trajectory(
    trajectory: list[tuple[float, float]],
    swipe_threshold: float,
    down_threshold: float,
    circle_sweep_min: float,
    circle_cv_max: float,
    min_detection_points: int = settings.GESTURE_MIN_DETECTION_POINTS,
    swipe_min_span: float = settings.GESTURE_SWIPE_MIN_SPAN,
    circle_min_radius: float = settings.GESTURE_CIRCLE_MIN_RADIUS,
    hand_size: float | None = None,
    hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
    hand_size_scale_min: float = settings.GESTURE_HAND_SIZE_SCALE_MIN,
    hand_size_scale_max: float = settings.GESTURE_HAND_SIZE_SCALE_MAX,
) -> GestureName | None:
    result = detect_gesture_with_confidence(
        trajectory=trajectory,
        swipe_threshold=swipe_threshold,
        down_threshold=down_threshold,
        circle_sweep_min=circle_sweep_min,
        circle_cv_max=circle_cv_max,
        min_detection_points=min_detection_points,
        swipe_min_span=swipe_min_span,
        circle_min_radius=circle_min_radius,
        min_confidence=0.0,
        hand_size=hand_size,
        hand_size_reference=hand_size_reference,
        hand_size_scale_min=hand_size_scale_min,
        hand_size_scale_max=hand_size_scale_max,
    )
    return result.gesture if result is not None else None


def extract_gesture_features(
    trajectory: list[tuple[float, float]],
    min_detection_points: int,
    hand_size: float | None = None,
    hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
    hand_size_scale_min: float = settings.GESTURE_HAND_SIZE_SCALE_MIN,
    hand_size_scale_max: float = settings.GESTURE_HAND_SIZE_SCALE_MAX,
) -> GestureFeatures | None:
    if len(trajectory) < min_detection_points:
        return None

    xs = [point[0] for point in trajectory]
    ys = [point[1] for point in trajectory]

    dx_total = xs[-1] - xs[0]
    dy_total = ys[-1] - ys[0]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)

    center_x = mean(xs)
    center_y = mean(ys)
    vectors = [(x - center_x, y - center_y) for x, y in trajectory]
    radii = [math.hypot(x, y) for x, y in vectors]

    if not radii:
        radius_mean = None
        radius_cv = None
        total_sweep = None
    else:
        angles = [math.atan2(y, x) for x, y in vectors]
        total_sweep = 0.0
        previous_angle = angles[0]
        for angle in angles[1:]:
            delta = angle - previous_angle
            while delta > math.pi:
                delta -= 2 * math.pi
            while delta < -math.pi:
                delta += 2 * math.pi
            total_sweep += delta
            previous_angle = angle

        radius_mean = mean(radii)
        radius_cv = pstdev(radii) / (radius_mean + 1e-6)

    hand_size_scale = compute_hand_size_scale(
        hand_size=hand_size,
        hand_size_reference=hand_size_reference,
        hand_size_scale_min=hand_size_scale_min,
        hand_size_scale_max=hand_size_scale_max,
    )

    return GestureFeatures(
        dx_total=dx_total,
        dy_total=dy_total,
        span_x=span_x,
        span_y=span_y,
        radius_mean=radius_mean,
        radius_cv=radius_cv,
        total_sweep=total_sweep,
        hand_size=hand_size,
        hand_size_scale=hand_size_scale,
    )


def detect_gesture_candidates(
    features: GestureFeatures,
    swipe_threshold: float,
    down_threshold: float,
    circle_sweep_min: float,
    circle_cv_max: float,
    swipe_min_span: float,
    circle_min_radius: float,
) -> list[GestureDetectionCandidate]:
    candidates: list[GestureDetectionCandidate] = []

    normalized_dx_total = features.dx_total / max(features.hand_size_scale, 1e-6)
    normalized_dy_total = features.dy_total / max(features.hand_size_scale, 1e-6)
    normalized_span_x = features.span_x / max(features.hand_size_scale, 1e-6)
    normalized_span_y = features.span_y / max(features.hand_size_scale, 1e-6)
    normalized_radius_mean = (
        features.radius_mean / max(features.hand_size_scale, 1e-6)
        if features.radius_mean is not None
        else None
    )

    horizontal_margin = abs(normalized_dx_total) - swipe_threshold
    if (
        horizontal_margin > 0
        and abs(normalized_dx_total) > abs(normalized_dy_total) * 1.5
        and normalized_span_x > swipe_min_span
    ):
        gesture = "swipe_right" if normalized_dx_total > 0 else "swipe_left"
        confidence = min(1.0, horizontal_margin / max(swipe_threshold, 1e-6))
        candidates.append(GestureDetectionCandidate(gesture=gesture, confidence=confidence))

    vertical_margin = normalized_dy_total - down_threshold
    if (
        vertical_margin > 0
        and normalized_dy_total > abs(normalized_dx_total) * 1.2
        and normalized_span_y > swipe_min_span
    ):
        confidence = min(1.0, vertical_margin / max(down_threshold, 1e-6))
        candidates.append(GestureDetectionCandidate(gesture="swipe_down", confidence=confidence))

    if (
        normalized_radius_mean is not None
        and features.radius_cv is not None
        and features.total_sweep is not None
        and normalized_radius_mean > circle_min_radius
        and abs(features.total_sweep) > circle_sweep_min
        and features.radius_cv < circle_cv_max
    ):
        sweep_score = min(1.0, abs(features.total_sweep) / max(circle_sweep_min, 1e-6))
        radius_score = min(1.0, circle_cv_max / max(features.radius_cv, 1e-6))
        confidence = min(1.0, (sweep_score + radius_score) / 2)
        candidates.append(GestureDetectionCandidate(gesture="circle", confidence=confidence))

    return candidates


def select_best_gesture_candidate(
    candidates: list[GestureDetectionCandidate],
    min_confidence: float,
) -> GestureDetectionCandidate | None:
    if not candidates:
        return None

    best_candidate = max(candidates, key=lambda candidate: candidate.confidence)
    if best_candidate.confidence < min_confidence:
        return None

    return best_candidate


def detect_gesture_with_confidence(
    trajectory: list[tuple[float, float]],
    swipe_threshold: float,
    down_threshold: float,
    circle_sweep_min: float,
    circle_cv_max: float,
    min_detection_points: int = settings.GESTURE_MIN_DETECTION_POINTS,
    swipe_min_span: float = settings.GESTURE_SWIPE_MIN_SPAN,
    circle_min_radius: float = settings.GESTURE_CIRCLE_MIN_RADIUS,
    min_confidence: float = settings.GESTURE_MIN_CONFIDENCE,
    hand_size: float | None = None,
    hand_size_reference: float = settings.GESTURE_HAND_SIZE_REFERENCE,
    hand_size_scale_min: float = settings.GESTURE_HAND_SIZE_SCALE_MIN,
    hand_size_scale_max: float = settings.GESTURE_HAND_SIZE_SCALE_MAX,
    tracking_source: str | None = None,
) -> GestureDetectionResult | None:
    features = extract_gesture_features(
        trajectory=trajectory,
        min_detection_points=min_detection_points,
        hand_size=hand_size,
        hand_size_reference=hand_size_reference,
        hand_size_scale_min=hand_size_scale_min,
        hand_size_scale_max=hand_size_scale_max,
    )
    if features is None:
        return None

    candidates = detect_gesture_candidates(
        features=features,
        swipe_threshold=swipe_threshold,
        down_threshold=down_threshold,
        circle_sweep_min=circle_sweep_min,
        circle_cv_max=circle_cv_max,
        swipe_min_span=swipe_min_span,
        circle_min_radius=circle_min_radius,
    )
    best_candidate = select_best_gesture_candidate(candidates, min_confidence)
    if best_candidate is None:
        return None

    return GestureDetectionResult(
        gesture=best_candidate.gesture,
        confidence=best_candidate.confidence,
        tracking_source=tracking_source,
    )