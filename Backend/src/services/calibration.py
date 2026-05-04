from __future__ import annotations

import threading
import uuid
import random
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from typing import Any

from core.realtime import RealtimeHub, realtime_hub
from repositories.config import ConfigRepository
from schemas.calibration import (
    CalibrationAdvisoryRecognition,
    CalibrationAnalysisResult,
    CalibrationAppliedSnapshot,
    CalibrationCollectedSample,
    CalibrationConfigPatch,
    CalibrationConfigPatchOperation,
    CalibrationConfigSnapshot,
    CalibrationDefinitionsResponse,
    CalibrationEventPayload,
    CalibrationMetricSummary,
    CalibrationModality,
    CalibrationModalityDefinition,
    CalibrationProfile,
    CalibrationRecommendation,
    CalibrationSessionCreateRequest,
    CalibrationSessionRecord,
    CalibrationTakeRecord,
    CalibrationTargetAnalysis,
    CalibrationTargetDefinition,
    CalibrationTargetProgress,
)
from schemas.gestures import GestureConfig


class CalibrationServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * fraction
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    lower_weight = upper_index - position
    upper_weight = position - lower_index
    return ordered[lower_index] * lower_weight + ordered[upper_index] * upper_weight


def _metric_summary(name: str, values: list[float]) -> CalibrationMetricSummary:
    return CalibrationMetricSummary(
        name=name,
        min_value=min(values) if values else None,
        max_value=max(values) if values else None,
        mean_value=mean(values) if values else None,
        median_value=median(values) if values else None,
        p10_value=_percentile(values, 0.10),
        p90_value=_percentile(values, 0.90),
        sample_count=len(values),
    )


def _build_gesture_config_patch(
    *,
    base_config: GestureConfig,
    candidate_config: GestureConfig,
    target_analyses: list[CalibrationTargetAnalysis],
) -> CalibrationConfigPatch | None:
    recommendation_metadata: dict[str, dict[str, list[str]]] = {}
    for analysis in target_analyses:
        for recommendation in analysis.recommendations:
            metadata = recommendation_metadata.setdefault(
                recommendation.parameter,
                {"source_targets": [], "rationales": []},
            )
            if analysis.target_id not in metadata["source_targets"]:
                metadata["source_targets"].append(analysis.target_id)
            if recommendation.rationale and recommendation.rationale not in metadata["rationales"]:
                metadata["rationales"].append(recommendation.rationale)

    base_values = base_config.model_dump()
    candidate_values = candidate_config.model_dump()
    operations: list[CalibrationConfigPatchOperation] = []
    for parameter in sorted(candidate_values):
        current_value = base_values.get(parameter)
        new_value = candidate_values.get(parameter)
        if current_value == new_value:
            continue
        metadata = recommendation_metadata.get(parameter, {"source_targets": [], "rationales": []})
        operations.append(
            CalibrationConfigPatchOperation(
                parameter=parameter,
                path=f"gesture_config.{parameter}",
                current_value=current_value,
                new_value=new_value,
                rationale=" ".join(metadata["rationales"]) if metadata["rationales"] else None,
                source_targets=metadata["source_targets"],
            )
        )

    if not operations:
        return None

    return CalibrationConfigPatch(
        modality="gesture",
        operations=operations,
        summary=f"{len(operations)} Gesten-Parameter wurden aus der Kalibrierung abgeleitet.",
    )


def _apply_gesture_config_patch(
    base_config: GestureConfig,
    patch: CalibrationConfigPatch | None,
) -> GestureConfig:
    patched_config = base_config.model_copy(deep=True)
    if patch is None:
        return patched_config

    for operation in patch.operations:
        if not hasattr(patched_config, operation.parameter):
            continue
        setattr(patched_config, operation.parameter, operation.new_value)
    return patched_config


class CalibrationService:
    _gesture_target_definitions = [
        CalibrationTargetDefinition(
            id="swipe_left",
            modality="gesture",
            display_name="Swipe Left",
            description="Kalibriert horizontale Wischgesten nach links.",
        ),
        CalibrationTargetDefinition(
            id="swipe_right",
            modality="gesture",
            display_name="Swipe Right",
            description="Kalibriert horizontale Wischgesten nach rechts.",
        ),
        CalibrationTargetDefinition(
            id="swipe_up",
            modality="gesture",
            display_name="Swipe Up",
            description="Kalibriert vertikale Wischgesten nach oben.",
        ),
        CalibrationTargetDefinition(
            id="swipe_down",
            modality="gesture",
            display_name="Swipe Down",
            description="Kalibriert vertikale Wischgesten nach unten.",
        ),
        CalibrationTargetDefinition(
            id="circle",
            modality="gesture",
            display_name="Circle",
            description="Kalibriert Kreisgesten ueber Sweep und Radius-Stabilitaet.",
        ),
        CalibrationTargetDefinition(
            id="push_click_short",
            modality="gesture",
            display_name="Push Click Short",
            description="Kalibriert kurze Push-Klick-Gesten fuer schnelle Bestaetigungen.",
        ),
        CalibrationTargetDefinition(
            id="push_click_long",
            modality="gesture",
            display_name="Push Click Long",
            description="Kalibriert lange Push-Klick-Gesten fuer Halteaktionen.",
        ),
        CalibrationTargetDefinition(
            id="zoom_out_hands",
            modality="gesture",
            display_name="Zoom Out Hands",
            description="Kalibriert Zwei-Hand-Zoom nach innen.",
        ),
        CalibrationTargetDefinition(
            id="zoom_in_hands",
            modality="gesture",
            display_name="Zoom In Hands",
            description="Kalibriert Zwei-Hand-Zoom nach aussen.",
        ),
    ]

    def __init__(
        self,
        realtime: RealtimeHub | None = None,
        config_repository_factory: Callable[[], ConfigRepository] | None = None,
    ) -> None:
        self.realtime = realtime or realtime_hub
        self.config_repository_factory = config_repository_factory or ConfigRepository
        self._lock = threading.RLock()
        self._active_sessions_by_modality: dict[CalibrationModality, str | None] = {
            "gesture": None,
            "voice": None,
        }

    def startup(self) -> None:
        repository = self.config_repository_factory()
        gesture_sessions = repository.list_calibration_sessions(modality="gesture")
        for session in gesture_sessions:
            if session.status != "collecting":
                continue
            session.status = "cancelled"
            session.cancelled_at = _utc_now()
            session.active_target_id = None
            session.notes.append(
                "Kalibrierung beim Service-Start als stale collecting session beendet."
            )
            repository.save_calibration_session(session)
        with self._lock:
            self._active_sessions_by_modality["gesture"] = None

    def shutdown(self) -> None:
        return None

    def get_definitions(self) -> CalibrationDefinitionsResponse:
        return CalibrationDefinitionsResponse(
            modalities=[
                CalibrationModalityDefinition(
                    modality="gesture",
                    display_name="Gestures",
                    supported=True,
                ),
                CalibrationModalityDefinition(
                    modality="voice",
                    display_name="Voice",
                    supported=False,
                ),
            ],
            targets=list(self._gesture_target_definitions),
        )

    def has_active_session(self, modality: CalibrationModality = "gesture") -> bool:
        with self._lock:
            return self._active_sessions_by_modality.get(modality) is not None

    def get_active_session(self, modality: CalibrationModality = "gesture") -> CalibrationSessionRecord | None:
        with self._lock:
            session_id = self._active_sessions_by_modality.get(modality)
        if session_id is None:
            return None

        session = self.config_repository_factory().get_calibration_session(session_id)
        if session is None or session.status != "collecting":
            with self._lock:
                self._active_sessions_by_modality[modality] = None
            return None
        return session

    def get_session(self, session_id: str) -> CalibrationSessionRecord:
        session = self.config_repository_factory().get_calibration_session(session_id)
        if session is None:
            raise CalibrationServiceError("Kalibrierungssitzung nicht gefunden.", status_code=404)
        return session

    def start_session(self, request: CalibrationSessionCreateRequest) -> CalibrationSessionRecord:
        if request.modality != "gesture":
            raise CalibrationServiceError("Nur Gesten-Kalibrierung ist derzeit verfuegbar.", status_code=422)

        target_ids = {definition.id for definition in self._gesture_target_definitions}
        invalid_targets = [target for target in request.selected_targets if target not in target_ids]
        if invalid_targets:
            raise CalibrationServiceError(
                f"Unbekannte Kalibrierungsziele: {', '.join(invalid_targets)}.",
                status_code=422,
            )

        with self._lock:
            if self._active_sessions_by_modality.get("gesture") is not None:
                raise CalibrationServiceError(
                    "Es laeuft bereits eine aktive Gesten-Kalibrierung.",
                    status_code=409,
                )

        repository = self.config_repository_factory()
        now = _utc_now()
        session = CalibrationSessionRecord(
            session_id=str(uuid.uuid4()),
            modality=request.modality,
            profile=request.profile,
            status="collecting",
            target_repetitions=request.target_repetitions,
            selected_targets=list(request.selected_targets),
            active_target_id=self._select_next_target_id(request.selected_targets),
            created_at=now,
            updated_at=now,
            original_snapshot=CalibrationConfigSnapshot(
                modality="gesture",
                profile=request.profile,
                captured_at=now,
                gesture_config=repository.get_gesture_config(),
            ),
            progress=[
                CalibrationTargetProgress(
                    target_id=target_id,
                    target_repetitions=request.target_repetitions,
                )
                for target_id in request.selected_targets
            ],
            active_take=None,
            pending_take=None,
        )
        repository.save_calibration_session(session)

        with self._lock:
            self._active_sessions_by_modality[request.modality] = session.session_id

        self._publish_event(
            "CalibrationSessionStarted",
            session,
            target_id=session.active_target_id,
            message="Kalibrierung gestartet.",
        )
        if session.active_target_id is not None:
            self._publish_event(
                "CalibrationTargetArmed",
                session,
                target_id=session.active_target_id,
                message="Naechstes Ziel bereit.",
            )
        return session

    def prepare_take(self, session_id: str, countdown_seconds: int = 3) -> CalibrationSessionRecord:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        if session.status != "collecting":
            raise CalibrationServiceError("Sitzung sammelt keine Samples mehr.", status_code=409)
        if session.pending_take is not None:
            raise CalibrationServiceError("Es wartet noch ein Take auf Review.", status_code=409)
        if session.active_take is not None:
            raise CalibrationServiceError("Es ist bereits ein Take vorbereitet oder aktiv.", status_code=409)

        open_target_ids = [progress.target_id for progress in session.progress if not progress.completed]
        if not open_target_ids:
            raise CalibrationServiceError("Alle Ziele sind bereits vollstaendig. Bitte Analyse erzeugen.", status_code=409)

        target_id = session.active_target_id if session.active_target_id in open_target_ids else self._select_next_target_id(open_target_ids)
        if target_id is None:
            raise CalibrationServiceError("Kein weiteres Kalibrierungsziel verfuegbar.", status_code=409)

        now = _utc_now()
        session.active_target_id = target_id
        session.active_take = CalibrationTakeRecord(
            take_id=str(uuid.uuid4()),
            target_id=target_id,
            status="prepared",
            prepared_at=now,
            countdown_seconds=countdown_seconds,
            ready_at=now + timedelta(seconds=countdown_seconds),
            trimmed_tail_ms=750,
        )
        repository.save_calibration_session(session)
        self._publish_event(
            "CalibrationTakePrepared",
            session,
            target_id=target_id,
            take_id=session.active_take.take_id,
            message="Take vorbereitet. Countdown kann starten.",
        )
        return session

    def start_take_recording(self, session_id: str) -> CalibrationSessionRecord:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        if session.status != "collecting":
            raise CalibrationServiceError("Sitzung sammelt keine Samples mehr.", status_code=409)
        if session.pending_take is not None:
            raise CalibrationServiceError("Es wartet noch ein Take auf Review.", status_code=409)
        if session.active_take is None or session.active_take.status != "prepared":
            raise CalibrationServiceError("Es ist kein vorbereiteter Take vorhanden.", status_code=409)

        session.active_take = session.active_take.model_copy(
            update={
                "status": "recording",
                "recording_started_at": _utc_now(),
            }
        )
        repository.save_calibration_session(session)
        self._publish_event(
            "CalibrationRecordingStarted",
            session,
            target_id=session.active_take.target_id,
            take_id=session.active_take.take_id,
            message="Recording gestartet.",
        )
        return session

    def finish_take_recording(
        self,
        session_id: str,
        sample: CalibrationCollectedSample,
        advisory_recognition: CalibrationAdvisoryRecognition | None = None,
    ) -> CalibrationSessionRecord:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        if session.status != "collecting":
            raise CalibrationServiceError("Sitzung sammelt keine Samples mehr.", status_code=409)
        if session.active_take is None or session.active_take.status != "recording":
            raise CalibrationServiceError("Es laeuft aktuell kein Recording-Take.", status_code=409)

        stopped_take = session.active_take.model_copy(
            update={
                "status": "pending_review",
                "recording_stopped_at": _utc_now(),
                "sample": sample,
                "advisory_recognition": advisory_recognition,
            }
        )
        session.active_take = None
        session.pending_take = stopped_take
        repository.save_calibration_session(session)
        self._publish_event(
            "CalibrationRecordingStopped",
            session,
            target_id=stopped_take.target_id,
            take_id=stopped_take.take_id,
            message="Recording gestoppt. Review erforderlich.",
            confidence=advisory_recognition.confidence if advisory_recognition is not None else None,
            metadata=(
                {
                    "recognized_target": advisory_recognition.recognized_target_id,
                    "tracking_source": advisory_recognition.tracking_source,
                }
                if advisory_recognition is not None
                else {}
            ),
        )
        return session

    def accept_pending_take(self, session_id: str) -> CalibrationSessionRecord:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        pending_take = session.pending_take
        if pending_take is None or pending_take.sample is None:
            raise CalibrationServiceError("Es liegt kein reviewbarer Take vor.", status_code=409)

        session.pending_take = None
        repository.save_calibration_session(session)
        return self._accept_source_of_truth_sample(
            session,
            pending_take.sample,
            recognized_target_id=(
                pending_take.advisory_recognition.recognized_target_id
                if pending_take.advisory_recognition is not None
                else None
            ),
            event_type="CalibrationTakeAccepted",
            event_message_prefix="Take akzeptiert.",
            extra_metadata={"take_id": pending_take.take_id},
        )

    def discard_pending_take(self, session_id: str) -> CalibrationSessionRecord:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        pending_take = session.pending_take
        if pending_take is None:
            raise CalibrationServiceError("Es liegt kein reviewbarer Take vor.", status_code=409)

        session.pending_take = None
        open_target_ids = [progress.target_id for progress in session.progress if not progress.completed]
        session.active_target_id = pending_take.target_id if pending_take.target_id in open_target_ids else self._select_next_target_id(open_target_ids)
        repository.save_calibration_session(session)
        self._publish_event(
            "CalibrationTakeDiscarded",
            session,
            target_id=pending_take.target_id,
            take_id=pending_take.take_id,
            message="Take verworfen.",
        )
        if session.active_target_id is not None:
            self._publish_event(
                "CalibrationTargetArmed",
                session,
                target_id=session.active_target_id,
                message="Ziel erneut bereit.",
            )
        return session

    def capture_gesture_sample(self, sample: CalibrationCollectedSample) -> CalibrationSessionRecord | None:
        session = self.get_active_session("gesture")
        if session is None:
            return None
        return self._accept_source_of_truth_sample(
            session,
            sample,
            recognized_target_id=sample.target_id,
            event_type="CalibrationSampleAccepted",
            event_message_prefix="Sample akzeptiert.",
        )

    def complete_session(self, session_id: str) -> CalibrationSessionRecord:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        if session.status != "collecting":
            raise CalibrationServiceError("Sitzung sammelt keine Samples mehr.", status_code=409)
        if session.active_take is not None:
            raise CalibrationServiceError("Es ist noch ein Take vorbereitet oder im Recording.", status_code=409)
        if session.pending_take is not None:
            raise CalibrationServiceError("Es wartet noch ein Take auf Review.", status_code=409)

        incomplete_targets = [progress.target_id for progress in session.progress if not progress.completed]
        if incomplete_targets:
            raise CalibrationServiceError(
                f"Kalibrierung noch nicht vollstaendig. Offen: {', '.join(incomplete_targets)}.",
                status_code=409,
            )

        analysis = self._analyze_session(session)
        now = _utc_now()
        session.status = "analysis_ready"
        session.completed_at = now
        session.analysis_ready_at = now
        session.analysis = analysis
        session.candidate_snapshot = CalibrationConfigSnapshot(
            modality=session.modality,
            profile=session.profile,
            captured_at=now,
            gesture_config=analysis.candidate_gesture_config,
            voice_config=analysis.candidate_voice_config,
        )
        session.active_target_id = None
        repository.save_calibration_session(session)

        with self._lock:
            if self._active_sessions_by_modality.get(session.modality) == session.session_id:
                self._active_sessions_by_modality[session.modality] = None

        self._publish_event(
            "CalibrationAnalysisReady",
            session,
            message="Kalibrierungsanalyse abgeschlossen.",
        )
        return session

    def apply_session(self, session_id: str) -> tuple[CalibrationSessionRecord, CalibrationProfile]:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        if session.status != "analysis_ready" or session.candidate_snapshot is None:
            raise CalibrationServiceError("Kalibrierungsprofil ist noch nicht anwendbar.", status_code=409)

        gesture_patch = session.analysis.gesture_config_patch if session.analysis is not None else None
        candidate_gesture_config = _apply_gesture_config_patch(
            session.original_snapshot.gesture_config or GestureConfig(),
            gesture_patch,
        )
        if session.modality != "gesture" or candidate_gesture_config is None:
            raise CalibrationServiceError("Es liegt kein anwendbares Gestenprofil vor.", status_code=409)

        session.candidate_snapshot.gesture_config = candidate_gesture_config

        snapshot = repository.save_last_applied_calibration_snapshot(
            CalibrationAppliedSnapshot(
                modality=session.modality,
                profile=session.profile,
                source_session_id=session.session_id,
                captured_at=_utc_now(),
                original_snapshot=session.original_snapshot,
                applied_snapshot=session.candidate_snapshot,
            )
        )
        repository.save_gesture_config(candidate_gesture_config)
        profile = repository.save_calibration_profile(
            CalibrationProfile(
                modality=session.modality,
                profile=session.profile,
                source_session_id=session.session_id,
                saved_at=_utc_now(),
                gesture_config=candidate_gesture_config,
                voice_config=session.candidate_snapshot.voice_config,
                analysis=session.analysis,
            )
        )

        session.status = "applied"
        session.applied_at = _utc_now()
        session.applied_snapshot = snapshot.applied_snapshot
        repository.save_calibration_session(session)
        self._publish_event(
            "CalibrationProfileApplied",
            session,
            message="Kalibrierungsprofil angewendet.",
        )
        return session, profile

    def rollback_session(self, session_id: str) -> tuple[CalibrationSessionRecord, CalibrationAppliedSnapshot]:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        snapshot = repository.get_last_applied_calibration_snapshot(session.modality, session.profile)
        if snapshot is None or snapshot.source_session_id != session.session_id:
            raise CalibrationServiceError("Kein passender Kalibrierungs-Snapshot fuer Rollback gefunden.", status_code=404)

        if snapshot.original_snapshot.gesture_config is None:
            raise CalibrationServiceError("Rollback-Snapshot enthaelt keine Gestenkonfiguration.", status_code=409)

        repository.save_gesture_config(snapshot.original_snapshot.gesture_config)
        session.status = "rolled_back"
        session.rolled_back_at = _utc_now()
        repository.save_calibration_session(session)
        self._publish_event(
            "CalibrationProfileRolledBack",
            session,
            message="Kalibrierungsprofil zurueckgesetzt.",
        )
        return session, snapshot

    def cancel_session(self, session_id: str) -> CalibrationSessionRecord:
        repository = self.config_repository_factory()
        session = self.get_session(session_id)
        if session.status not in {"collecting", "analysis_ready"}:
            raise CalibrationServiceError("Diese Sitzung kann nicht mehr verworfen werden.", status_code=409)

        session.status = "cancelled"
        session.cancelled_at = _utc_now()
        session.active_target_id = None
        session.active_take = None
        session.pending_take = None
        repository.save_calibration_session(session)
        with self._lock:
            if self._active_sessions_by_modality.get(session.modality) == session.session_id:
                self._active_sessions_by_modality[session.modality] = None
        return session

    def _accept_source_of_truth_sample(
        self,
        session: CalibrationSessionRecord,
        sample: CalibrationCollectedSample,
        *,
        recognized_target_id: str | None,
        event_type: str,
        event_message_prefix: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> CalibrationSessionRecord:
        current_progress = self._get_current_progress(session)
        if current_progress is None:
            current_progress = next(
                (progress for progress in session.progress if progress.target_id == sample.target_id and not progress.completed),
                None,
            )
        if current_progress is None:
            return session

        accepted_sample = sample.model_copy(update={"target_id": current_progress.target_id})
        session.samples.append(accepted_sample)
        current_progress.collected_samples += 1
        if recognized_target_id is not None and recognized_target_id != current_progress.target_id:
            current_progress.last_feedback = (
                f"{event_message_prefix} {current_progress.collected_samples}/{current_progress.target_repetitions} "
                f"fuer {current_progress.target_id}, erkannt wurde {recognized_target_id}."
            )
        else:
            current_progress.last_feedback = (
                f"{event_message_prefix} {current_progress.collected_samples}/{current_progress.target_repetitions} "
                f"fuer {current_progress.target_id}."
            )

        self._refresh_session_quality(session)
        repository = self.config_repository_factory()
        repository.save_calibration_session(session)
        event_metadata = {
            "hand": accepted_sample.gesture_payload.hand if accepted_sample.gesture_payload is not None else None,
            "recognized_target": recognized_target_id,
            "source_of_truth_target": current_progress.target_id,
        }
        if extra_metadata:
            event_metadata.update(extra_metadata)
        self._publish_event(
            event_type,
            session,
            target_id=current_progress.target_id,
            sample_id=accepted_sample.sample_id,
            message=current_progress.last_feedback,
            confidence=(accepted_sample.gesture_payload.confidence if accepted_sample.gesture_payload is not None else None),
            metadata=event_metadata,
        )

        previous_target_id = session.active_target_id
        if current_progress.collected_samples >= current_progress.target_repetitions:
            current_progress.completed = True
            self._publish_event(
                "CalibrationTargetCompleted",
                session,
                target_id=current_progress.target_id,
                message=f"Ziel {current_progress.target_id} abgeschlossen.",
            )

        remaining_target_ids = [progress.target_id for progress in session.progress if not progress.completed]
        session.active_target_id = self._select_next_target_id(remaining_target_ids)
        repository.save_calibration_session(session)
        if session.active_target_id is not None and session.active_target_id != previous_target_id:
            self._publish_event(
                "CalibrationTargetArmed",
                session,
                target_id=session.active_target_id,
                message="Naechstes Ziel bereit.",
            )
        return session

    def _refresh_session_quality(self, session: CalibrationSessionRecord) -> CalibrationSessionRecord:
        samples_by_target: dict[str, list[CalibrationCollectedSample]] = {}
        for sample in session.samples:
            samples_by_target.setdefault(sample.target_id, []).append(sample)

        for progress in session.progress:
            target_samples = samples_by_target.get(progress.target_id, [])
            confidences = [
                sample.gesture_payload.confidence
                for sample in target_samples
                if sample.gesture_payload is not None
            ]
            progress.quality_metrics = {
                "completion_ratio": progress.collected_samples / max(progress.target_repetitions, 1),
                "mean_confidence": mean(confidences) if confidences else 0.0,
                "rejection_ratio": progress.rejected_samples / max(progress.rejected_samples + progress.collected_samples, 1),
            }
        return session

    def _get_current_progress(self, session: CalibrationSessionRecord) -> CalibrationTargetProgress | None:
        if session.active_target_id is not None:
            progress = next(
                (
                    progress
                    for progress in session.progress
                    if progress.target_id == session.active_target_id and not progress.completed
                ),
                None,
            )
            if progress is not None:
                return progress
        return next((progress for progress in session.progress if not progress.completed), None)

    def _select_next_target_id(self, target_ids: list[str]) -> str | None:
        if not target_ids:
            return None
        return random.choice(target_ids)

    def _analyze_session(self, session: CalibrationSessionRecord) -> CalibrationAnalysisResult:
        if session.modality != "gesture":
            raise CalibrationServiceError("Nur Gesten-Kalibrierung ist derzeit implementiert.", status_code=422)

        base_config = session.original_snapshot.gesture_config or GestureConfig()
        candidate_config = base_config.model_copy(deep=True)
        target_analyses: list[CalibrationTargetAnalysis] = []

        swipe_analyses = self._analyze_swipes(session.samples, candidate_config)
        if swipe_analyses:
            target_analyses.extend(swipe_analyses)

        circle_analysis = self._analyze_circle(session.samples, candidate_config)
        if circle_analysis is not None:
            target_analyses.append(circle_analysis)

        push_analyses = self._analyze_push(session.samples, candidate_config)
        if push_analyses:
            target_analyses.extend(push_analyses)

        zoom_analyses = self._analyze_zoom(session.samples, candidate_config)
        if zoom_analyses:
            target_analyses.extend(zoom_analyses)

        gesture_config_patch = _build_gesture_config_patch(
            base_config=base_config,
            candidate_config=candidate_config,
            target_analyses=target_analyses,
        )
        patched_candidate_config = _apply_gesture_config_patch(base_config, gesture_config_patch)

        return CalibrationAnalysisResult(
            modality="gesture",
            generated_at=_utc_now(),
            targets=target_analyses,
            candidate_gesture_config=patched_candidate_config,
            summary=f"Empfehlungen fuer {len(target_analyses)} Kalibrierungsziele berechnet.",
            gesture_config_patch=gesture_config_patch,
        )

    def _analyze_swipes(
        self,
        samples: list[CalibrationCollectedSample],
        candidate_config: GestureConfig,
    ) -> list[CalibrationTargetAnalysis]:
        analyses: list[CalibrationTargetAnalysis] = []
        grouped = {
            "swipe_left": [sample for sample in samples if sample.target_id == "swipe_left" and sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None],
            "swipe_right": [sample for sample in samples if sample.target_id == "swipe_right" and sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None],
            "swipe_up": [sample for sample in samples if sample.target_id == "swipe_up" and sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None],
            "swipe_down": [sample for sample in samples if sample.target_id == "swipe_down" and sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None],
        }

        horizontal_samples = grouped["swipe_left"] + grouped["swipe_right"]
        horizontal_strengths = [abs(sample.gesture_payload.trajectory.dx_total) for sample in horizontal_samples if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
        horizontal_spans = [sample.gesture_payload.trajectory.span_x for sample in horizontal_samples if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
        original_swipe_threshold = candidate_config.swipe_threshold
        original_swipe_min_span = candidate_config.swipe_min_span
        original_down_threshold = candidate_config.down_threshold
        original_up_threshold = candidate_config.up_threshold
        if horizontal_strengths:
            suggested_threshold = _clamp((_percentile(horizontal_strengths, 0.10) or candidate_config.swipe_threshold) * 0.85, 0.05, 0.45)
            suggested_span = _clamp((_percentile(horizontal_spans, 0.10) or candidate_config.swipe_min_span) * 0.85, 0.03, 0.45)
            candidate_config.swipe_threshold = suggested_threshold
            candidate_config.swipe_min_span = suggested_span

        for target_id in ("swipe_left", "swipe_right", "swipe_up", "swipe_down"):
            target_samples = grouped[target_id]
            if not target_samples:
                continue

            spans = [
                sample.gesture_payload.trajectory.span_x if target_id in {"swipe_left", "swipe_right"} else sample.gesture_payload.trajectory.span_y
                for sample in target_samples
                if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None
            ]
            durations = [
                sample.gesture_payload.duration_seconds
                for sample in target_samples
                if sample.gesture_payload is not None and sample.gesture_payload.duration_seconds is not None
            ]
            confidences = [
                sample.gesture_payload.confidence
                for sample in target_samples
                if sample.gesture_payload is not None
            ]
            dominance = []
            for sample in target_samples:
                if sample.gesture_payload is None or sample.gesture_payload.trajectory is None:
                    continue
                trajectory = sample.gesture_payload.trajectory
                if target_id in {"swipe_left", "swipe_right"}:
                    dominance.append(abs(trajectory.dx_total) / max(abs(trajectory.dy_total), 1e-6))
                else:
                    dominance.append(abs(trajectory.dy_total) / max(abs(trajectory.dx_total), 1e-6))

            recommendations: list[CalibrationRecommendation] = []
            if target_id in {"swipe_left", "swipe_right"} and horizontal_strengths:
                recommendations.append(
                    CalibrationRecommendation(
                        parameter="swipe_threshold",
                        current_value=original_swipe_threshold,
                        recommended_value=candidate_config.swipe_threshold,
                        min_bound=0.05,
                        max_bound=0.45,
                        rationale="Horizontaler Bewegungsumfang wurde an die unteren Perzentile der positiven Samples angepasst.",
                    )
                )
            if target_id == "swipe_down":
                down_strengths = [sample.gesture_payload.trajectory.dy_total for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
                if down_strengths:
                    candidate_config.down_threshold = _clamp((_percentile(down_strengths, 0.10) or candidate_config.down_threshold) * 0.85, 0.05, 0.45)
                    recommendations.append(
                        CalibrationRecommendation(
                            parameter="down_threshold",
                            current_value=original_down_threshold,
                            recommended_value=candidate_config.down_threshold,
                            min_bound=0.05,
                            max_bound=0.45,
                            rationale="Schwellwert fuer Down-Swipes wurde auf robuste positive Samples ausgerichtet.",
                        )
                    )
            if target_id == "swipe_up":
                up_strengths = [abs(sample.gesture_payload.trajectory.dy_total) for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
                if up_strengths:
                    candidate_config.up_threshold = _clamp((_percentile(up_strengths, 0.10) or candidate_config.up_threshold) * 0.85, 0.05, 0.45)
                    recommendations.append(
                        CalibrationRecommendation(
                            parameter="up_threshold",
                            current_value=original_up_threshold,
                            recommended_value=candidate_config.up_threshold,
                            min_bound=0.05,
                            max_bound=0.45,
                            rationale="Schwellwert fuer Up-Swipes wurde an positive Samples angepasst.",
                        )
                    )
            if spans and target_id in {"swipe_left", "swipe_right"}:
                recommendations.append(
                    CalibrationRecommendation(
                        parameter="swipe_min_span",
                        current_value=original_swipe_min_span,
                        recommended_value=candidate_config.swipe_min_span,
                        min_bound=0.03,
                        max_bound=0.45,
                        rationale="Minimale Swipe-Spanne wurde auf die untere Spanne korrekter Bewegungen gesetzt.",
                    )
                )

            analyses.append(
                CalibrationTargetAnalysis(
                    target_id=target_id,
                    sample_count=len(target_samples),
                    metrics=[
                        _metric_summary("span", [float(value) for value in spans]),
                        _metric_summary("direction_dominance", [float(value) for value in dominance]),
                        _metric_summary("duration_seconds", [float(value) for value in durations]),
                        _metric_summary("confidence", [float(value) for value in confidences]),
                    ],
                    recommendations=recommendations,
                    artifacts={"orientation": "horizontal" if target_id in {"swipe_left", "swipe_right"} else "vertical"},
                )
            )
        return analyses

    def _analyze_circle(
        self,
        samples: list[CalibrationCollectedSample],
        candidate_config: GestureConfig,
    ) -> CalibrationTargetAnalysis | None:
        circle_samples = [sample for sample in samples if sample.target_id == "circle" and sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
        if not circle_samples:
            return None

        sweeps = [abs(sample.gesture_payload.trajectory.total_sweep or 0.0) for sample in circle_samples if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
        radius_stability = [sample.gesture_payload.trajectory.radius_cv or 0.0 for sample in circle_samples if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
        radii = [sample.gesture_payload.trajectory.radius_mean or 0.0 for sample in circle_samples if sample.gesture_payload is not None and sample.gesture_payload.trajectory is not None]
        confidences = [sample.gesture_payload.confidence for sample in circle_samples if sample.gesture_payload is not None]

        original_sweep = candidate_config.circle_sweep_min
        original_cv = candidate_config.circle_radius_cv_max
        original_radius = candidate_config.circle_min_radius
        candidate_config.circle_sweep_min = _clamp((_percentile(sweeps, 0.10) or candidate_config.circle_sweep_min) * 0.85, 3.2, 8.5)
        candidate_config.circle_radius_cv_max = _clamp((_percentile(radius_stability, 0.90) or candidate_config.circle_radius_cv_max) * 1.1, 0.05, 1.0)
        candidate_config.circle_min_radius = _clamp((_percentile(radii, 0.10) or candidate_config.circle_min_radius) * 0.85, 0.01, 0.35)

        return CalibrationTargetAnalysis(
            target_id="circle",
            sample_count=len(circle_samples),
            metrics=[
                _metric_summary("total_sweep", [float(value) for value in sweeps]),
                _metric_summary("radius_stability", [float(value) for value in radius_stability]),
                _metric_summary("radius_mean", [float(value) for value in radii]),
                _metric_summary("confidence", [float(value) for value in confidences]),
            ],
            recommendations=[
                CalibrationRecommendation(
                    parameter="circle_sweep_min",
                    current_value=original_sweep,
                    recommended_value=candidate_config.circle_sweep_min,
                    min_bound=3.2,
                    max_bound=8.5,
                    rationale="Minimaler Sweep wurde an die kleineren erfolgreichen Kreisbewegungen angepasst.",
                ),
                CalibrationRecommendation(
                    parameter="circle_radius_cv_max",
                    current_value=original_cv,
                    recommended_value=candidate_config.circle_radius_cv_max,
                    min_bound=0.05,
                    max_bound=1.0,
                    rationale="Radius-Stabilitaet bleibt begrenzt, orientiert sich aber an erfolgreichen Kreisbewegungen.",
                ),
                CalibrationRecommendation(
                    parameter="circle_min_radius",
                    current_value=original_radius,
                    recommended_value=candidate_config.circle_min_radius,
                    min_bound=0.01,
                    max_bound=0.35,
                    rationale="Mindest-Radius wurde auf die untere positive Verteilung gesetzt.",
                ),
            ],
            artifacts={"family": "circle"},
        )

    def _analyze_push(
        self,
        samples: list[CalibrationCollectedSample],
        candidate_config: GestureConfig,
    ) -> list[CalibrationTargetAnalysis]:
        analyses: list[CalibrationTargetAnalysis] = []
        for target_id in ("push_click_short", "push_click_long"):
            target_samples = [sample for sample in samples if sample.target_id == target_id and sample.gesture_payload is not None and sample.gesture_payload.push is not None]
            if not target_samples:
                continue

            forward_depths = [sample.gesture_payload.push.forward_depth for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.push is not None]
            release_depths = [sample.gesture_payload.push.release_depth for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.push is not None]
            hold_durations = [sample.gesture_payload.push.hold_duration_seconds for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.push is not None and sample.gesture_payload.push.hold_duration_seconds is not None]
            confidences = [sample.gesture_payload.confidence for sample in target_samples if sample.gesture_payload is not None]
            pose_validity = [1.0 if sample.gesture_payload.push.pose_valid else 0.0 for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.push is not None]
            extension_ratios = [float(sample.gesture_payload.feature_windows.get("index_extension_ratio", 0.0)) for sample in target_samples if sample.gesture_payload is not None]
            center_distances = [float(sample.gesture_payload.feature_windows.get("center_distance", 0.0)) for sample in target_samples if sample.gesture_payload is not None]

            original_push_depth = candidate_config.push_depth_threshold
            original_release = candidate_config.push_release_threshold
            original_extension = candidate_config.push_pose_extension_ratio
            original_center = candidate_config.center_tolerance
            original_long = candidate_config.long_click_seconds

            candidate_config.push_depth_threshold = _clamp((_percentile(forward_depths, 0.10) or candidate_config.push_depth_threshold) * 0.85, 0.02, 0.35)
            candidate_config.push_release_threshold = _clamp(min((_percentile(release_depths, 0.90) or candidate_config.push_release_threshold) * 1.1, candidate_config.push_depth_threshold * 0.8), 0.0, 0.28)
            if extension_ratios:
                candidate_config.push_pose_extension_ratio = _clamp((_percentile(extension_ratios, 0.10) or candidate_config.push_pose_extension_ratio) * 0.95, 1.05, 2.5)
            if center_distances:
                candidate_config.center_tolerance = _clamp((_percentile(center_distances, 0.90) or candidate_config.center_tolerance) * 1.1, 0.04, 0.35)
            if target_id == "push_click_long" and hold_durations:
                candidate_config.long_click_seconds = _clamp((_percentile(hold_durations, 0.10) or candidate_config.long_click_seconds) * 0.9, 0.2, 2.5)

            analyses.append(
                CalibrationTargetAnalysis(
                    target_id=target_id,
                    sample_count=len(target_samples),
                    metrics=[
                        _metric_summary("pose_valid_rate", [float(value) for value in pose_validity]),
                        _metric_summary("forward_depth", [float(value) for value in forward_depths]),
                        _metric_summary("release_depth", [float(value) for value in release_depths]),
                        _metric_summary("hold_duration_seconds", [float(value) for value in hold_durations]),
                        _metric_summary("confidence", [float(value) for value in confidences]),
                    ],
                    recommendations=[
                        CalibrationRecommendation(
                            parameter="push_depth_threshold",
                            current_value=original_push_depth,
                            recommended_value=candidate_config.push_depth_threshold,
                            min_bound=0.02,
                            max_bound=0.35,
                            rationale="Vorwaerts-Tiefe basiert jetzt auf unteren positiven Perzentilen.",
                        ),
                        CalibrationRecommendation(
                            parameter="push_release_threshold",
                            current_value=original_release,
                            recommended_value=candidate_config.push_release_threshold,
                            min_bound=0.0,
                            max_bound=0.28,
                            rationale="Release-Tiefe bleibt unterhalb des Push-Schwellwerts, folgt aber erfolgreichen Samples.",
                        ),
                        CalibrationRecommendation(
                            parameter="push_pose_extension_ratio",
                            current_value=original_extension,
                            recommended_value=candidate_config.push_pose_extension_ratio,
                            min_bound=1.05,
                            max_bound=2.5,
                            rationale="Finger-Streckung wird aus erfolgreichen Push-Posen abgeleitet.",
                        ),
                        CalibrationRecommendation(
                            parameter="center_tolerance",
                            current_value=original_center,
                            recommended_value=candidate_config.center_tolerance,
                            min_bound=0.04,
                            max_bound=0.35,
                            rationale="Zentrierung toleriert reale positive Abweichungen, bleibt aber begrenzt.",
                        ),
                        CalibrationRecommendation(
                            parameter="long_click_seconds",
                            current_value=original_long,
                            recommended_value=candidate_config.long_click_seconds,
                            min_bound=0.2,
                            max_bound=2.5,
                            rationale="Long-Click-Dauer orientiert sich an gemessenen Haltezeiten.",
                        ),
                    ],
                    artifacts={"family": "push"},
                )
            )
        return analyses

    def _analyze_zoom(
        self,
        samples: list[CalibrationCollectedSample],
        candidate_config: GestureConfig,
    ) -> list[CalibrationTargetAnalysis]:
        analyses: list[CalibrationTargetAnalysis] = []
        for target_id in ("zoom_out_hands", "zoom_in_hands"):
            target_samples = [sample for sample in samples if sample.target_id == target_id and sample.gesture_payload is not None and sample.gesture_payload.zoom is not None]
            if not target_samples:
                continue

            start_distances = [sample.gesture_payload.zoom.start_distance for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.zoom is not None]
            deltas = [abs(sample.gesture_payload.zoom.delta_distance) for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.zoom is not None]
            frame_counts = [float(sample.gesture_payload.zoom.frame_count) for sample in target_samples if sample.gesture_payload is not None and sample.gesture_payload.zoom is not None]
            confidences = [sample.gesture_payload.confidence for sample in target_samples if sample.gesture_payload is not None]

            original_delta = candidate_config.zoom_distance_delta_threshold
            original_near = candidate_config.zoom_start_near_distance
            original_far = candidate_config.zoom_start_far_distance
            original_frames = candidate_config.two_hand_min_frames

            candidate_config.zoom_distance_delta_threshold = _clamp((_percentile(deltas, 0.10) or candidate_config.zoom_distance_delta_threshold) * 0.85, 0.03, 0.6)
            if target_id == "zoom_in_hands":
                candidate_config.zoom_start_near_distance = _clamp((_percentile(start_distances, 0.90) or candidate_config.zoom_start_near_distance) * 1.05, 0.05, 0.8)
            if target_id == "zoom_out_hands":
                candidate_config.zoom_start_far_distance = _clamp((_percentile(start_distances, 0.10) or candidate_config.zoom_start_far_distance) * 0.95, 0.12, 1.5)
            candidate_config.two_hand_min_frames = int(_clamp(round((_percentile(frame_counts, 0.10) or float(candidate_config.two_hand_min_frames)) - 1), 2, 32))

            analyses.append(
                CalibrationTargetAnalysis(
                    target_id=target_id,
                    sample_count=len(target_samples),
                    metrics=[
                        _metric_summary("start_distance", [float(value) for value in start_distances]),
                        _metric_summary("delta_distance", [float(value) for value in deltas]),
                        _metric_summary("frame_count", [float(value) for value in frame_counts]),
                        _metric_summary("confidence", [float(value) for value in confidences]),
                    ],
                    recommendations=[
                        CalibrationRecommendation(
                            parameter="zoom_distance_delta_threshold",
                            current_value=original_delta,
                            recommended_value=candidate_config.zoom_distance_delta_threshold,
                            min_bound=0.03,
                            max_bound=0.6,
                            rationale="Minimale Zoom-Distanz folgt den kleineren erfolgreichen Zoom-Bewegungen.",
                        ),
                        CalibrationRecommendation(
                            parameter="zoom_start_near_distance",
                            current_value=original_near,
                            recommended_value=candidate_config.zoom_start_near_distance,
                            min_bound=0.05,
                            max_bound=0.8,
                            rationale="Naher Zoom-Start wird an positive Out-Zoom-Startpunkte angepasst.",
                        ),
                        CalibrationRecommendation(
                            parameter="zoom_start_far_distance",
                            current_value=original_far,
                            recommended_value=candidate_config.zoom_start_far_distance,
                            min_bound=0.12,
                            max_bound=1.5,
                            rationale="Ferner Zoom-Start wird an positive In-Zoom-Startpunkte angepasst.",
                        ),
                        CalibrationRecommendation(
                            parameter="two_hand_min_frames",
                            current_value=float(original_frames),
                            recommended_value=float(candidate_config.two_hand_min_frames),
                            min_bound=2,
                            max_bound=32,
                            rationale="Minimale Frame-Anzahl wird aus stabilen Zoom-Folgen abgeleitet.",
                        ),
                    ],
                    artifacts={"family": "zoom"},
                )
            )
        return analyses

    def _publish_event(
        self,
        event_type: str,
        session: CalibrationSessionRecord,
        target_id: str | None = None,
        take_id: str | None = None,
        sample_id: str | None = None,
        message: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = CalibrationEventPayload(
            session_id=session.session_id,
            modality=session.modality,
            status=session.status,
            target_id=target_id,
            take_id=take_id,
            sample_id=sample_id,
            collected_samples=(next((progress.collected_samples for progress in session.progress if progress.target_id == target_id), None) if target_id is not None else None),
            target_repetitions=(next((progress.target_repetitions for progress in session.progress if progress.target_id == target_id), None) if target_id is not None else None),
            message=message,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.realtime.publish_from_thread({"eventType": event_type, "payload": payload.model_dump(mode="json")})


calibration_service = CalibrationService()


__all__ = [
    "CalibrationService",
    "CalibrationServiceError",
    "calibration_service",
]