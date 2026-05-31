from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


SCRIPT_ROOT = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = SCRIPT_ROOT / "gesture_benchmark.py"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TARGETS = ["pinch_close", "pinch_open", "circle"]


class ApiError(RuntimeError):
    pass


def _request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    api_request = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(api_request) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"{method} {path} failed with HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise ApiError(f"{method} {path} failed: {exc.reason}") from exc


def _post(
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _request_json(base_url=base_url, method="POST", path=path, payload=payload)


def _get(base_url: str, path: str) -> dict[str, Any]:
    return _request_json(base_url=base_url, method="GET", path=path)


def _progress_text(session: dict[str, Any], target_id: str | None) -> str:
    if not target_id:
        return ""
    for progress in session.get("progress", []):
        if progress.get("target_id") != target_id:
            continue
        return (
            f"{progress.get('collected_samples', 0)}/{progress.get('target_repetitions', 0)}"
            f" accepted for {target_id}"
        )
    return target_id


def _print_take_feedback(session: dict[str, Any]) -> None:
    pending_take = session.get("pending_take")
    if not pending_take:
        return
    advisory = pending_take.get("advisory_recognition") or {}
    sample = pending_take.get("sample") or {}
    payload = sample.get("gesture_payload") or {}
    recognized = advisory.get("recognized_target_id") or "none"
    confidence = advisory.get("confidence")
    sample_gesture = payload.get("gesture") or sample.get("target_id") or "unknown"
    if confidence is None:
        print(f"Advisory recognition: {recognized}")
    else:
        print(f"Advisory recognition: {recognized} ({confidence:.2f})")
    print(f"Captured sample gesture: {sample_gesture}")


def _run_benchmark(
    *,
    videos_dir: Path,
    videos: list[str],
    target_accuracy: float,
    output_path: Path | None,
    fail_below_target: bool,
) -> int:
    command = [
        sys.executable,
        str(BENCHMARK_SCRIPT),
        "--videos-dir",
        str(videos_dir),
        "--target-accuracy",
        str(target_accuracy),
    ]
    for video in videos:
        command.extend(["--video", video])
    if output_path is not None:
        command.extend(["--output", str(output_path)])
    if fail_below_target:
        command.append("--fail-below-target")
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--profile", default="default")
    parser.add_argument("--target", action="append", dest="targets")
    parser.add_argument("--target-repetitions", type=int, default=5)
    parser.add_argument("--camera-index", type=int)
    parser.add_argument("--session-output", type=Path)
    parser.add_argument("--complete", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--benchmark-videos-dir", type=Path)
    parser.add_argument("--benchmark-video", action="append", default=[])
    parser.add_argument("--benchmark-output", type=Path)
    parser.add_argument("--target-accuracy", type=float, default=0.9)
    parser.add_argument("--fail-below-target", action="store_true")
    args = parser.parse_args()

    selected_targets = args.targets or list(DEFAULT_TARGETS)
    if args.benchmark_videos_dir is not None and not args.apply:
        raise SystemExit("--benchmark-videos-dir requires --apply so the benchmark sees the calibrated config.")

    session_response = _post(
        args.base_url,
        "/api/v1/calibration/sessions",
        {
            "modality": "gesture",
            "selected_targets": selected_targets,
            "target_repetitions": args.target_repetitions,
            "profile": args.profile,
            "camera_index": args.camera_index,
        },
    )
    session = session_response["session"]
    session_id = session["session_id"]
    print(f"Started calibration session {session_id} for targets: {', '.join(selected_targets)}")

    try:
        while session.get("status") == "collecting":
            active_target = session.get("active_target_id")
            if not active_target:
                break
            print(f"Next target: {_progress_text(session, active_target)}")
            input("Press Enter to prepare the next take...")
            session = _post(
                args.base_url,
                f"/api/v1/calibration/sessions/{session_id}/takes/prepare",
            )["session"]

            input(f"Press Enter to start recording for {active_target}...")
            session = _post(
                args.base_url,
                f"/api/v1/calibration/sessions/{session_id}/takes/start",
            )["session"]

            input(f"Perform {active_target} now, then press Enter to stop recording...")
            session = _post(
                args.base_url,
                f"/api/v1/calibration/sessions/{session_id}/takes/stop",
            )["session"]
            _print_take_feedback(session)

            while True:
                decision = input("Accept take? [a]ccept/[d]iscard/[q]uit: ").strip().lower()
                if decision in {"a", "accept", ""}:
                    session = _post(
                        args.base_url,
                        f"/api/v1/calibration/sessions/{session_id}/takes/accept",
                    )["session"]
                    break
                if decision in {"d", "discard"}:
                    session = _post(
                        args.base_url,
                        f"/api/v1/calibration/sessions/{session_id}/takes/discard",
                    )["session"]
                    break
                if decision in {"q", "quit"}:
                    _post(
                        args.base_url,
                        f"/api/v1/calibration/sessions/{session_id}/cancel",
                    )
                    print("Session cancelled.")
                    return 130
                print("Please enter a, d, or q.")

        if args.complete:
            session = _post(
                args.base_url,
                f"/api/v1/calibration/sessions/{session_id}/complete",
            )["session"]
            analysis = session.get("analysis") or {}
            print(analysis.get("summary") or "Calibration analysis completed.")
            patch = analysis.get("gesture_config_patch") or {}
            for operation in patch.get("operations", []):
                print(
                    f"- {operation['parameter']}: {operation['current_value']} -> {operation['new_value']}"
                )

        if args.apply:
            session = _post(
                args.base_url,
                f"/api/v1/calibration/sessions/{session_id}/apply",
            )["session"]
            print(f"Applied calibrated profile for session {session_id}.")

        if args.session_output is not None:
            latest = _get(args.base_url, f"/api/v1/calibration/sessions/{session_id}")
            args.session_output.write_text(
                json.dumps(latest, indent=2, sort_keys=True),
                encoding="utf-8",
            )

        if args.benchmark_videos_dir is not None:
            return _run_benchmark(
                videos_dir=args.benchmark_videos_dir,
                videos=list(args.benchmark_video),
                target_accuracy=args.target_accuracy,
                output_path=args.benchmark_output,
                fail_below_target=args.fail_below_target,
            )
        return 0
    except KeyboardInterrupt:
        _post(args.base_url, f"/api/v1/calibration/sessions/{session_id}/cancel")
        print("Session cancelled after keyboard interrupt.")
        return 130
    except ApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())