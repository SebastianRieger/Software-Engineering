from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_VIDEOS_DIR = REPO_ROOT / "pics"
TUNER_SCRIPT = SCRIPT_ROOT / "gesture_video_tuner.py"


def _run_tuner(
    *,
    videos_dir: Path,
    videos: list[str],
    frame_stride: int,
    max_frames: int | None,
    start_frame: int,
    end_frame: int | None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="gesture-benchmark-") as temp_dir:
        tuner_output_path = Path(temp_dir) / "gesture_tuner_output.json"
        stdout_path = Path(temp_dir) / "gesture_tuner_stdout.log"
        stderr_path = Path(temp_dir) / "gesture_tuner_stderr.log"
        command = [
            sys.executable,
            str(TUNER_SCRIPT),
            "--videos-dir",
            str(videos_dir),
            "--frame-stride",
            str(frame_stride),
            "--start-frame",
            str(start_frame),
            "--output",
            str(tuner_output_path),
        ]
        if max_frames is not None:
            command.extend(["--max-frames", str(max_frames)])
        if end_frame is not None:
            command.extend(["--end-frame", str(end_frame)])
        for video in videos:
            command.extend(["--video", video])

        with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
            process = subprocess.Popen(
                command,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )

            deadline = time.monotonic() + 300.0
            while time.monotonic() < deadline:
                payload = _try_read_json(tuner_output_path)
                if payload is not None:
                    if process.poll() is None:
                        try:
                            process.wait(timeout=2.0)
                        except subprocess.TimeoutExpired:
                            process.terminate()
                            try:
                                process.wait(timeout=5.0)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=5.0)
                    return payload

                if process.poll() is not None:
                    break

                time.sleep(0.2)

        stdout_text = stdout_path.read_text(encoding="utf-8")
        stderr_text = stderr_path.read_text(encoding="utf-8")
        payload = _try_read_json(tuner_output_path)
        if payload is not None and process.returncode in {0, None}:
            return payload
        raise RuntimeError(
            "gesture_video_tuner.py failed or did not finish cleanly\n"
            f"returncode: {process.returncode}\n"
            f"stdout:\n{stdout_text}\n"
            f"stderr:\n{stderr_text}"
        )


def _try_read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size <= 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _summarize_video_accuracy(samples: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    per_gesture_totals: dict[str, int] = defaultdict(int)
    per_gesture_correct: dict[str, int] = defaultdict(int)

    for sample in samples:
        label = str(sample["label"])
        detected = sample.get("detected_gesture")
        correct = detected == label
        per_gesture_totals[label] += 1
        if correct:
            per_gesture_correct[label] += 1
        else:
            failures.append(
                {
                    "file_name": sample.get("file_name"),
                    "label": label,
                    "detected_gesture": detected,
                    "best_candidate_score": sample.get("best_candidate_score"),
                    "confidence": sample.get("confidence"),
                    "active_phase": sample.get("active_phase"),
                    "reject_reason": sample.get("reject_reason"),
                    "spec_id": sample.get("spec_id"),
                    "contract_id": sample.get("contract_id"),
                    "trajectory_points": sample.get("trajectory_points"),
                    "frame_count": sample.get("frame_count"),
                }
            )

    total_videos = len(samples)
    correct_videos = total_videos - len(failures)
    per_gesture_accuracy = {
        gesture: {
            "video_count": total,
            "correct_videos": per_gesture_correct.get(gesture, 0),
            "video_accuracy": (per_gesture_correct.get(gesture, 0) / float(total)) if total else None,
        }
        for gesture, total in sorted(per_gesture_totals.items())
    }
    return {
        "video_count": total_videos,
        "correct_videos": correct_videos,
        "video_accuracy": (correct_videos / float(total_videos)) if total_videos else None,
        "per_gesture_video_accuracy": per_gesture_accuracy,
        "failures": failures,
    }


def _build_summary(payload: dict[str, Any], *, videos_dir: Path, target_accuracy: float) -> dict[str, Any]:
    samples = payload.get("samples", [])
    video_summary = _summarize_video_accuracy(samples)
    video_accuracy = video_summary["video_accuracy"]
    return {
        "videos_dir": str(videos_dir),
        "target_video_accuracy": target_accuracy,
        "passes_video_accuracy_target": (
            video_accuracy is not None and video_accuracy >= target_accuracy
        ),
        "video_summary": video_summary,
        "swipe_evaluation_models": payload.get("swipe_evaluation_models", {}),
        "swipe_confusion_matrix": payload.get("swipe_confusion_matrix", {}),
        "negative_swipe_summary": payload.get("negative_swipe_summary", {}),
        "push_cycle_reports": payload.get("push_cycle_reports", []),
        "negative_push_summary": payload.get("negative_push_summary", {}),
        "swipe_tuning_result": payload.get("swipe_tuning_result"),
        "recommendations": payload.get("recommendations", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos-dir", type=Path, default=DEFAULT_VIDEOS_DIR)
    parser.add_argument("--video", action="append", default=[])
    parser.add_argument("--frame-stride", type=int, default=2)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--end-frame", type=int)
    parser.add_argument("--target-accuracy", type=float, default=0.9)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-below-target", action="store_true")
    args = parser.parse_args()

    tuner_payload = _run_tuner(
        videos_dir=args.videos_dir,
        videos=list(args.video),
        frame_stride=args.frame_stride,
        max_frames=args.max_frames,
        start_frame=max(0, args.start_frame),
        end_frame=args.end_frame,
    )
    summary = _build_summary(
        tuner_payload,
        videos_dir=args.videos_dir,
        target_accuracy=args.target_accuracy,
    )

    output_text = json.dumps(summary, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(output_text, encoding="utf-8")
    else:
        print(output_text)

    if args.fail_below_target and not summary["passes_video_accuracy_target"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())