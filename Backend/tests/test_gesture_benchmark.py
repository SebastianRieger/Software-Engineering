import importlib.util
from pathlib import Path


def _load_gesture_benchmark_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "gesture_benchmark.py"
    )
    spec = importlib.util.spec_from_file_location(
        "gesture_benchmark_under_test", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_summary_passes_sequence_promotion_gate_when_shadow_is_better():
    module = _load_gesture_benchmark_module()

    summary = module._build_summary(
        {
            "samples": [
                {
                    "file_name": "left.mp4",
                    "label": "swipe_left",
                    "detected_gesture": "swipe_left",
                },
                {
                    "file_name": "right.mp4",
                    "label": "swipe_right",
                    "detected_gesture": "swipe_left",
                },
            ],
            "sequence_shadow_summary": {
                "promotion_ready": True,
                "sequence_accuracy": 1.0,
            },
        },
        videos_dir=Path("/tmp/videos"),
        target_accuracy=0.5,
    )

    assert summary["video_summary"]["video_accuracy"] == 0.5
    assert summary["passes_video_accuracy_target"] is True
    assert summary["passes_sequence_promotion_gate"] is True


def test_build_summary_blocks_sequence_promotion_gate_when_shadow_regresses():
    module = _load_gesture_benchmark_module()

    summary = module._build_summary(
        {
            "samples": [
                {
                    "file_name": "left.mp4",
                    "label": "swipe_left",
                    "detected_gesture": "swipe_left",
                },
                {
                    "file_name": "right.mp4",
                    "label": "swipe_right",
                    "detected_gesture": "swipe_right",
                },
            ],
            "sequence_shadow_summary": {
                "promotion_ready": True,
                "sequence_accuracy": 0.5,
            },
        },
        videos_dir=Path("/tmp/videos"),
        target_accuracy=0.9,
    )

    assert summary["video_summary"]["video_accuracy"] == 1.0
    assert summary["passes_video_accuracy_target"] is True
    assert summary["passes_sequence_promotion_gate"] is False
