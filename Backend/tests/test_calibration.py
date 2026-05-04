import asyncio
from datetime import datetime, timezone

import pytest

from core.config import settings
from core.database import init_db
from core.realtime import realtime_hub
from main import websocket_endpoint
from repositories.config import ConfigRepository
from schemas.calibration import (
    CalibrationAdvisoryRecognition,
    CalibrationSessionCreateRequest,
    CalibrationAppliedSnapshot,
    CalibrationConfigSnapshot,
    CalibrationCollectedSample,
    CalibrationProfile,
    CalibrationSessionRecord,
    CalibrationTargetProgress,
    GestureCalibrationSamplePayload,
    GestureTrajectorySummary,
)
from schemas.gestures import GestureConfig
from services.calibration import CalibrationService


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.messages = []
        self._incoming: asyncio.Queue[object] = asyncio.Queue()

    async def accept(self):
        self.accepted = True

    async def receive_text(self):
        item = await self._incoming.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def send_json(self, message):
        self.messages.append(message)

    def queue_disconnect(self):
        from fastapi import WebSocketDisconnect

        self._incoming.put_nowait(WebSocketDisconnect())


def build_calibration_repo(tmp_path) -> ConfigRepository:
    settings.DATABASE_URL = f"sqlite:///{tmp_path / 'calibration-test.db'}"
    init_db()
    return ConfigRepository()


def build_calibration_service(tmp_path, *, realtime=None) -> CalibrationService:
    build_calibration_repo(tmp_path)
    service = CalibrationService(
        realtime=realtime or realtime_hub,
        config_repository_factory=ConfigRepository,
    )
    service.startup()
    return service


def make_swipe_sample(target_id: str, *, confidence: float = 0.92) -> CalibrationCollectedSample:
    captured_at = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    return CalibrationCollectedSample(
        sample_id=f"sample-{target_id}-{confidence}",
        modality="gesture",
        target_id=target_id,
        collected_at=captured_at,
        gesture_payload=GestureCalibrationSamplePayload(
            gesture=target_id,
            confidence=confidence,
            tracking_source="palm_center",
            hand="right",
            duration_seconds=0.42,
            hand_size=0.16,
            hand_size_scale=1.0,
            trajectory=GestureTrajectorySummary(
                point_count=12,
                dx_total=0.34 if target_id == "swipe_right" else -0.34,
                dy_total=0.02,
                span_x=0.38,
                span_y=0.06,
                radius_mean=0.08,
                radius_cv=0.11,
                total_sweep=0.12,
            ),
        ),
    )


def test_config_repository_round_trips_calibration_session(tmp_path):
    repo = build_calibration_repo(tmp_path)
    captured_at = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    session = CalibrationSessionRecord(
        session_id="gesture-session-1",
        modality="gesture",
        profile="demo-user",
        status="collecting",
        target_repetitions=12,
        selected_targets=["swipe_left", "circle"],
        created_at=captured_at,
        updated_at=captured_at,
        original_snapshot=CalibrationConfigSnapshot(
            modality="gesture",
            profile="demo-user",
            captured_at=captured_at,
            gesture_config=GestureConfig(),
        ),
        samples=[
            CalibrationCollectedSample(
                sample_id="sample-1",
                modality="gesture",
                target_id="swipe_left",
                collected_at=captured_at,
                gesture_payload=GestureCalibrationSamplePayload(
                    gesture="swipe_left",
                    confidence=0.91,
                    tracking_source="palm_center",
                    hand="right",
                    duration_seconds=0.42,
                    hand_size=0.16,
                    hand_size_scale=1.0,
                    trajectory=GestureTrajectorySummary(
                        point_count=12,
                        dx_total=-0.34,
                        dy_total=0.02,
                        span_x=0.38,
                        span_y=0.06,
                        radius_mean=0.08,
                        radius_cv=0.11,
                        total_sweep=0.12,
                    ),
                ),
            )
        ],
        progress=[
            CalibrationTargetProgress(
                target_id="swipe_left",
                collected_samples=1,
                target_repetitions=12,
                completed=False,
                quality_metrics={"mean_confidence": 0.91},
            )
        ],
    )

    saved_session = repo.save_calibration_session(session)
    loaded_session = repo.get_calibration_session("gesture-session-1")
    listed_sessions = repo.list_calibration_sessions(modality="gesture")

    assert saved_session.updated_at >= captured_at
    assert loaded_session is not None
    assert loaded_session.profile == "demo-user"
    assert loaded_session.samples[0].gesture_payload is not None
    assert loaded_session.samples[0].gesture_payload.gesture == "swipe_left"
    assert listed_sessions[0].session_id == "gesture-session-1"


def test_config_repository_round_trips_calibration_profiles_and_snapshots(tmp_path):
    repo = build_calibration_repo(tmp_path)
    captured_at = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    original_snapshot = CalibrationConfigSnapshot(
        modality="gesture",
        profile="default",
        captured_at=captured_at,
        gesture_config=GestureConfig(swipe_threshold=0.18),
    )
    applied_snapshot = CalibrationConfigSnapshot(
        modality="gesture",
        profile="default",
        captured_at=captured_at,
        gesture_config=GestureConfig(swipe_threshold=0.14, circle_sweep_min=4.5),
    )
    profile = CalibrationProfile(
        modality="gesture",
        profile="default",
        source_session_id="gesture-session-1",
        saved_at=captured_at,
        gesture_config=applied_snapshot.gesture_config,
    )
    snapshot = CalibrationAppliedSnapshot(
        modality="gesture",
        profile="default",
        source_session_id="gesture-session-1",
        captured_at=captured_at,
        original_snapshot=original_snapshot,
        applied_snapshot=applied_snapshot,
    )

    saved_profile = repo.save_calibration_profile(profile)
    saved_snapshot = repo.save_last_applied_calibration_snapshot(snapshot)
    loaded_profile = repo.get_calibration_profile("gesture", "default")
    loaded_snapshot = repo.get_last_applied_calibration_snapshot("gesture", "default")

    assert saved_profile.saved_at >= captured_at
    assert saved_snapshot.captured_at >= captured_at
    assert loaded_profile is not None
    assert loaded_profile.gesture_config is not None
    assert loaded_profile.gesture_config.swipe_threshold == 0.14
    assert loaded_snapshot is not None
    assert loaded_snapshot.original_snapshot.gesture_config is not None
    assert loaded_snapshot.original_snapshot.gesture_config.swipe_threshold == 0.18


def test_calibration_startup_cancels_stale_collecting_sessions(tmp_path):
    repo = build_calibration_repo(tmp_path)
    captured_at = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
    session = CalibrationSessionRecord(
        session_id="stale-gesture-session",
        modality="gesture",
        profile="default",
        status="collecting",
        target_repetitions=10,
        selected_targets=["push_click_short"],
        active_target_id="push_click_short",
        created_at=captured_at,
        updated_at=captured_at,
        original_snapshot=CalibrationConfigSnapshot(
            modality="gesture",
            profile="default",
            captured_at=captured_at,
            gesture_config=GestureConfig(),
        ),
        progress=[
            CalibrationTargetProgress(
                target_id="push_click_short",
                target_repetitions=10,
            )
        ],
    )
    repo.save_calibration_session(session)

    service = CalibrationService(
        realtime=realtime_hub,
        config_repository_factory=ConfigRepository,
    )
    service.startup()

    recovered = repo.get_calibration_session("stale-gesture-session")

    assert recovered is not None
    assert recovered.status == "cancelled"
    assert recovered.cancelled_at is not None
    assert recovered.active_target_id is None
    assert service.has_active_session("gesture") is False


def test_calibration_service_completes_applies_and_rolls_back(tmp_path):
    repo = build_calibration_repo(tmp_path)
    baseline = repo.save_gesture_config(GestureConfig(swipe_threshold=0.2, swipe_min_span=0.12))
    service = build_calibration_service(tmp_path)

    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_right"],
            target_repetitions=2,
            profile="demo-user",
        )
    )
    service.capture_gesture_sample(make_swipe_sample("swipe_right", confidence=0.91))
    service.capture_gesture_sample(make_swipe_sample("swipe_right", confidence=0.95))

    completed = service.complete_session(session.session_id)
    assert completed.status == "analysis_ready"
    assert completed.analysis is not None
    assert completed.candidate_snapshot is not None
    assert completed.candidate_snapshot.gesture_config is not None

    applied_session, profile = service.apply_session(session.session_id)
    applied_config = repo.get_gesture_config()
    assert applied_session.status == "applied"
    assert profile.profile == "demo-user"
    assert applied_config.swipe_threshold != baseline.swipe_threshold

    rolled_back_session, snapshot = service.rollback_session(session.session_id)
    restored_config = repo.get_gesture_config()
    assert rolled_back_session.status == "rolled_back"
    assert snapshot.original_snapshot.gesture_config is not None
    assert restored_config.swipe_threshold == baseline.swipe_threshold


def test_calibration_service_analysis_produces_reviewable_gesture_patch(tmp_path):
    service = build_calibration_service(tmp_path)

    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_right"],
            target_repetitions=2,
            profile="demo-user",
        )
    )
    service.capture_gesture_sample(make_swipe_sample("swipe_right", confidence=0.91))
    service.capture_gesture_sample(make_swipe_sample("swipe_right", confidence=0.95))

    completed = service.complete_session(session.session_id)

    assert completed.analysis is not None
    assert completed.analysis.gesture_config_patch is not None
    assert completed.analysis.gesture_config_patch.operations
    assert any(
        operation.parameter == "swipe_threshold"
        for operation in completed.analysis.gesture_config_patch.operations
    )
    assert completed.candidate_snapshot is not None
    assert completed.candidate_snapshot.gesture_config == completed.analysis.candidate_gesture_config


def test_calibration_service_apply_session_uses_analysis_patch(tmp_path):
    repo = build_calibration_repo(tmp_path)
    baseline = repo.save_gesture_config(GestureConfig(swipe_threshold=0.2, swipe_min_span=0.12))
    service = build_calibration_service(tmp_path)

    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_right"],
            target_repetitions=2,
            profile="demo-user",
        )
    )
    service.capture_gesture_sample(make_swipe_sample("swipe_right", confidence=0.91))
    service.capture_gesture_sample(make_swipe_sample("swipe_right", confidence=0.95))

    completed = service.complete_session(session.session_id)
    assert completed.analysis is not None
    assert completed.analysis.gesture_config_patch is not None
    completed.candidate_snapshot = CalibrationConfigSnapshot(
        modality="gesture",
        profile=completed.profile,
        captured_at=completed.candidate_snapshot.captured_at if completed.candidate_snapshot is not None else completed.analysis.generated_at,
        gesture_config=baseline,
    )
    repo.save_calibration_session(completed)

    applied_session, _profile = service.apply_session(session.session_id)
    applied_config = repo.get_gesture_config()

    assert applied_session.status == "applied"
    assert applied_config.swipe_threshold != baseline.swipe_threshold


def test_calibration_service_accepts_misrecognized_gesture_for_active_target(tmp_path):
    service = build_calibration_service(tmp_path)

    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_left"],
            target_repetitions=2,
            profile="default",
        )
    )

    mismatched = make_swipe_sample("swipe_right", confidence=0.88)
    updated = service.capture_gesture_sample(mismatched)

    assert updated is not None
    assert updated.progress[0].collected_samples == 1
    assert updated.progress[0].rejected_samples == 0
    assert updated.progress[0].last_feedback == "Sample akzeptiert. 1/2 fuer swipe_left, erkannt wurde swipe_right."
    assert updated.samples[0].target_id == session.active_target_id
    assert updated.samples[0].gesture_payload is not None
    assert updated.samples[0].gesture_payload.gesture == "swipe_right"


def test_calibration_service_allows_multi_target_sessions_and_rotates_targets(tmp_path):
    service = build_calibration_service(tmp_path)

    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_left", "swipe_right"],
            target_repetitions=1,
            profile="default",
        )
    )

    assert session.active_target_id in {"swipe_left", "swipe_right"}

    first_target = session.active_target_id
    updated = service.capture_gesture_sample(make_swipe_sample("swipe_right"))

    assert updated is not None
    assert next(progress for progress in updated.progress if progress.target_id == first_target).completed is True
    assert updated.active_target_id in ({"swipe_left", "swipe_right"} - {first_target})


def test_calibration_service_guided_take_accepts_pending_review_sample(tmp_path):
    service = build_calibration_service(tmp_path)

    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_left"],
            target_repetitions=1,
            profile="default",
        )
    )

    prepared = service.prepare_take(session.session_id)
    assert prepared.active_take is not None
    started = service.start_take_recording(session.session_id)
    assert started.active_take is not None
    assert started.active_take.status == "recording"

    stopped = service.finish_take_recording(
        session.session_id,
        make_swipe_sample("swipe_left", confidence=0.0),
        CalibrationAdvisoryRecognition(
            recognized_target_id=None,
            confidence=None,
            tracking_source="mock-runtime",
        ),
    )

    assert stopped.pending_take is not None
    assert stopped.active_take is None

    accepted = service.accept_pending_take(session.session_id)

    assert accepted.pending_take is None
    assert accepted.progress[0].collected_samples == 1
    assert accepted.progress[0].completed is True
    assert accepted.samples[0].target_id == "swipe_left"


def test_calibration_service_rejects_complete_with_pending_take(tmp_path):
    service = build_calibration_service(tmp_path)

    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_left"],
            target_repetitions=1,
            profile="default",
        )
    )

    service.prepare_take(session.session_id)
    service.start_take_recording(session.session_id)
    service.finish_take_recording(session.session_id, make_swipe_sample("swipe_left"))

    with pytest.raises(Exception) as exc_info:
        service.complete_session(session.session_id)

    assert "Review" in str(exc_info.value)


@pytest.mark.asyncio
async def test_calibration_api_session_lifecycle(client, override_calibration_dependency, override_gesture_dependency):
    _ = override_calibration_dependency
    gesture_runtime = override_gesture_dependency

    definitions_response = await client.get("/api/v1/calibration/definitions")
    assert definitions_response.status_code == 200
    assert any(target["id"] == "swipe_right" for target in definitions_response.json()["targets"])

    start_response = await client.post(
        "/api/v1/calibration/sessions",
        json={
            "modality": "gesture",
            "selected_targets": ["swipe_right"],
            "target_repetitions": 1,
            "profile": "demo-user",
            "camera_index": 1,
        },
    )
    assert start_response.status_code == 200
    session_id = start_response.json()["session"]["session_id"]
    assert gesture_runtime.running is True
    assert gesture_runtime.camera_index == 1

    prepare_take_response = await client.post(f"/api/v1/calibration/sessions/{session_id}/takes/prepare")
    assert prepare_take_response.status_code == 200

    start_take_response = await client.post(f"/api/v1/calibration/sessions/{session_id}/takes/start")
    assert start_take_response.status_code == 200
    assert gesture_runtime.active_take is not None

    stop_take_response = await client.post(f"/api/v1/calibration/sessions/{session_id}/takes/stop")
    assert stop_take_response.status_code == 200
    assert stop_take_response.json()["session"]["pending_take"] is not None

    accept_take_response = await client.post(f"/api/v1/calibration/sessions/{session_id}/takes/accept")
    assert accept_take_response.status_code == 200

    session_response = await client.get(f"/api/v1/calibration/sessions/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["session"]["progress"][0]["collected_samples"] == 1

    complete_response = await client.post(f"/api/v1/calibration/sessions/{session_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["session"]["status"] == "analysis_ready"

    apply_response = await client.post(f"/api/v1/calibration/sessions/{session_id}/apply")
    assert apply_response.status_code == 200
    assert apply_response.json()["session"]["status"] == "applied"

    rollback_response = await client.post(f"/api/v1/calibration/sessions/{session_id}/rollback")
    assert rollback_response.status_code == 200
    assert rollback_response.json()["session"]["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_gesture_config_write_blocked_during_active_calibration(client, override_calibration_dependency):
    service = override_calibration_dependency
    service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_right"],
            target_repetitions=1,
            profile="default",
        )
    )

    response = await client.put(
        "/api/v1/config/gestures",
        json={"swipe_threshold": 0.18},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_calibration_session_can_be_cancelled(client, override_calibration_dependency):
    service = override_calibration_dependency
    session = service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_right"],
            target_repetitions=1,
            profile="default",
        )
    )

    response = await client.post(f"/api/v1/calibration/sessions/{session.session_id}/cancel")
    assert response.status_code == 200
    assert response.json()["session"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_shared_websocket_receives_calibration_events(tmp_path):
    realtime_hub.bind_loop(asyncio.get_running_loop())
    service = build_calibration_service(tmp_path, realtime=realtime_hub)
    websocket = FakeWebSocket()
    task = asyncio.create_task(websocket_endpoint(websocket))
    await asyncio.sleep(0)

    service.start_session(
        CalibrationSessionCreateRequest(
            modality="gesture",
            selected_targets=["swipe_right"],
            target_repetitions=1,
            profile="demo-user",
        )
    )
    service.capture_gesture_sample(make_swipe_sample("swipe_right"))

    await asyncio.sleep(0.1)
    websocket.queue_disconnect()
    await asyncio.wait_for(task, timeout=1.0)

    event_types = [message["eventType"] for message in websocket.messages]
    assert websocket.accepted is True
    assert "CalibrationSessionStarted" in event_types
    assert "CalibrationTargetArmed" in event_types
    assert "CalibrationSampleAccepted" in event_types