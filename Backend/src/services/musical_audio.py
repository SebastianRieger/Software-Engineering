from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import math
import operator
import queue
import threading
import time
from typing import Any, Callable, cast

import numpy as np

from core.realtime import RealtimeHub, realtime_hub
from repositories.config import ConfigRepository
from schemas.commands import CommandProfile
from schemas.musical_audio import (
    MusicalAudioConfig,
    MusicalAudioNoteEvent,
    MusicalAudioStatusCode,
    MusicalAudioTrainingArtifact,
)
from services.input.orchestrator import InputOrchestrator, input_orchestrator

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional runtime dependency
    sd = None

try:
    import aubio
except ImportError:  # pragma: no cover - optional runtime dependency
    aubio = None

try:
    from dtaidistance import dtw
except ImportError:  # pragma: no cover - optional runtime dependency
    dtw = None


logger = logging.getLogger(__name__)
PORTAUDIO_ERROR = getattr(sd, "PortAudioError", OSError) if sd is not None else OSError


@dataclass
class _DetectedPitchEvent:
    semitone: float
    timestamp: float
    confidence: float | None


@dataclass
class _PreflightResult:
    config: MusicalAudioConfig
    device_index: int
    device_name: str
    pitch_detector: Any
    onset_detector: Any


class MusicalAudioServiceError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: MusicalAudioStatusCode = "runtime_start_failed",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class MusicalAudioService:
    def __init__(
        self,
        realtime: RealtimeHub | None = None,
        config_repository_factory: type[ConfigRepository] | None = None,
        input_orchestrator_service: InputOrchestrator | None = None,
    ) -> None:
        self.realtime = realtime or realtime_hub
        self.config_repository_factory = config_repository_factory or ConfigRepository
        self.input_orchestrator = input_orchestrator_service or InputOrchestrator(
            realtime=self.realtime,
            config_repository_factory=self.config_repository_factory,
        )
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=1)
        self._active_config = MusicalAudioConfig()
        self._active_profile_id = "default"
        self._artifacts: list[MusicalAudioTrainingArtifact] = []
        self._running = False
        self._device_index: int | None = None
        self._device_name: str | None = None
        self._validated_device_index: int | None = None
        self._validated_sample_rate: int | None = None
        self._pitch_detector = None
        self._onset_detector = None
        self._sequence_events: list[_DetectedPitchEvent] = []
        self._last_pitch_hz: float | None = None
        self._last_match: str | None = None
        self._last_match_score: float | None = None
        self._last_event_at: datetime | None = None
        self._last_activity_at = 0.0
        self._last_error: str | None = self._build_unavailable_message()
        self._last_error_code: MusicalAudioStatusCode | None = "unavailable"

    def startup(self) -> None:
        self.reload_config()

    def reload_config(self) -> MusicalAudioConfig:
        repository = self.config_repository_factory()
        try:
            config = repository.get_musical_audio_config()
            active_profile_getter = getattr(repository, "get_active_command_profile", None)
            active_profile = (
                cast(CommandProfile | None, active_profile_getter())
                if callable(active_profile_getter)
                else None
            )
            profile_id = active_profile.profile_id if active_profile is not None else "default"
            artifacts = repository.list_musical_audio_training_artifacts(profile_id=profile_id)
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            logger.warning("Could not reload musical audio config, using defaults: %s", exc)
            config = MusicalAudioConfig()
            artifacts = []

        self.input_orchestrator.reload_config()
        filtered_artifacts = [artifact for artifact in artifacts if artifact.enabled]
        if config.active_artifact_id:
            filtered_artifacts = [
                artifact for artifact in filtered_artifacts if artifact.artifact_id == config.active_artifact_id
            ]

        with self._lock:
            self._active_config = config
            self._active_profile_id = profile_id
            self._artifacts = filtered_artifacts
            if not self.is_available():
                self._last_error = self._build_unavailable_message()
                self._last_error_code = "unavailable"
            else:
                if self._last_error_code == "unavailable":
                    self._last_error = None
                    self._last_error_code = None
        return config

    def is_available(self) -> bool:
        return sd is not None and aubio is not None and dtw is not None

    def get_status(self) -> dict[str, object]:
        with self._lock:
            status_code = self._derive_status_code_locked()
            return {
                "message": "Musical audio status",
                "available": self.is_available(),
                "enabled": self._active_config.enabled,
                "running": self._running,
                "status_code": status_code,
                "mode": "direct-mic" if self.is_available() else "unavailable",
                "provider": self._provider_name(),
                "active_profile_id": self._active_profile_id,
                "device_index": self._device_index,
                "device_name": self._device_name,
                "sample_rate": self._active_config.sample_rate,
                "block_size": self._active_config.block_size,
                "queue_max_chunks": self._active_config.queue_max_chunks,
                "active_artifact_id": self._active_config.active_artifact_id,
                "artifacts_loaded": len(self._artifacts),
                "validated_device_index": self._validated_device_index,
                "validated_sample_rate": self._validated_sample_rate,
                "last_pitch_hz": self._last_pitch_hz,
                "last_match": self._last_match,
                "last_match_score": self._last_match_score,
                "last_event_at": self._last_event_at,
                "last_error": self._last_error,
                "last_error_code": self._last_error_code,
            }

    def list_input_devices(self) -> list[dict[str, object]]:
        if sd is None:
            return []

        try:
            devices = sd.query_devices()
        except (PORTAUDIO_ERROR, RuntimeError):
            return []

        try:
            default_input = sd.default.device[0]
        except (AttributeError, PORTAUDIO_ERROR, RuntimeError):  # pragma: no cover - backend dependent
            default_input = None

        result: list[dict[str, object]] = []
        for index, device in enumerate(devices):
            max_input_channels = int(device.get("max_input_channels", 0))
            if max_input_channels <= 0:
                continue

            result.append(
                {
                    "index": index,
                    "name": str(device.get("name", f"Input {index}")),
                    "max_input_channels": max_input_channels,
                    "default_samplerate": (
                        float(device["default_samplerate"]) if device.get("default_samplerate") is not None else None
                    ),
                    "is_default": isinstance(default_input, int) and default_input == index,
                }
            )

        return result

    def start(self, device_index: int = -1) -> dict[str, object]:
        self.reload_config()

        with self._lock:
            if self._running:
                return self.get_status()

        try:
            preflight = self._preflight_start(device_index)
        except MusicalAudioServiceError as exc:
            with self._lock:
                self._last_error = str(exc)
                self._last_error_code = exc.error_code
                self._validated_device_index = None
                self._validated_sample_rate = None
            raise

        with self._lock:
            self._active_config = preflight.config
            self._audio_queue = queue.Queue(maxsize=preflight.config.queue_max_chunks)
            self._stop_event.clear()
            self._running = True
            self._device_index = preflight.device_index
            self._device_name = preflight.device_name
            self._validated_device_index = preflight.device_index
            self._validated_sample_rate = preflight.config.sample_rate
            self._pitch_detector = preflight.pitch_detector
            self._onset_detector = preflight.onset_detector
            self._sequence_events = []
            self._last_pitch_hz = None
            self._last_match = None
            self._last_match_score = None
            self._last_event_at = None
            self._last_activity_at = 0.0
            self._last_error = None
            self._last_error_code = None
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

        return self.get_status()

    def stop(self) -> dict[str, object]:
        with self._lock:
            self._running = False
            self._stop_event.set()
            thread = self._thread
            self._thread = None

        if thread is not None:
            thread.join(timeout=2.0)

        with self._lock:
            self._device_index = None
            self._device_name = None
            self._pitch_detector = None
            self._onset_detector = None
            self._sequence_events = []
            if self._last_error_code in {"runtime_start_failed", "permission_blocked"}:
                self._last_error = None
                self._last_error_code = None
            status = self.get_status()

        return {**status, "message": "Musical audio stopped"}

    def shutdown(self) -> None:
        self.stop()

    def process_note_events(self, note_events: list[MusicalAudioNoteEvent]) -> bool:
        matched_artifact, score = self._match_note_events(note_events)
        if matched_artifact is None:
            return False

        timestamp = datetime.now(timezone.utc)
        metadata = {
            "artifact_id": matched_artifact.artifact_id,
            "match_score": score,
            "note_count": len(note_events),
            "source_hint": matched_artifact.source_hint,
        }
        self.input_orchestrator.publish_raw_input_detected(
            input_source="musical_audio",
            raw_input=matched_artifact.raw_input,
            timestamp=timestamp,
            metadata=metadata,
        )
        accepted = self.input_orchestrator.publish_ui_action_requested(
            input_source="musical_audio",
            raw_input=matched_artifact.raw_input,
            timestamp=timestamp,
            metadata=metadata,
        )

        with self._lock:
            self._last_match = matched_artifact.raw_input
            self._last_match_score = score
            self._last_event_at = timestamp

        return accepted

    def _run_loop(self) -> None:
        with self._lock:
            config = self._active_config
            device_index = self._device_index

        sounddevice_module = sd
        if sounddevice_module is None:
            with self._lock:
                self._last_error = self._build_unavailable_message()
                self._running = False
            return

        try:
            with sounddevice_module.InputStream(
                samplerate=config.sample_rate,
                blocksize=config.block_size,
                device=device_index,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            ):
                while not self._stop_event.is_set():
                    try:
                        chunk = self._audio_queue.get(timeout=0.25)
                    except queue.Empty:
                        self._flush_if_idle(time.monotonic(), force=False)
                        continue

                    self._process_audio_chunk(chunk)
        except (PORTAUDIO_ERROR, RuntimeError, ValueError) as exc:  # pragma: no cover - depends on audio hardware
            logger.exception("Musical audio capture loop failed")
            with self._lock:
                self._last_error = self._format_runtime_error(exc)
                self._last_error_code = self._runtime_error_code(exc)
                self._running = False
        finally:
            with self._lock:
                self._running = False

    def _preflight_start(self, device_index: int) -> _PreflightResult:
        with self._lock:
            config = self._active_config
            artifacts = list(self._artifacts)

        if not config.enabled:
            raise MusicalAudioServiceError(
                "Musical-Audio-Service ist per Konfiguration deaktiviert.",
                status_code=503,
                error_code="configuration_disabled",
            )

        if not self.is_available():
            raise MusicalAudioServiceError(
                self._build_unavailable_message(),
                status_code=503,
                error_code="unavailable",
            )

        if not config.active_artifact_id:
            raise MusicalAudioServiceError(
                "Kein aktives Musical-Audio-Artefakt konfiguriert.",
                status_code=409,
                error_code="no_active_artifact",
            )

        if not artifacts:
            raise MusicalAudioServiceError(
                f"Aktives Musical-Audio-Artefakt '{config.active_artifact_id}' wurde nicht gefunden oder ist deaktiviert.",
                status_code=409,
                error_code="no_active_artifact",
            )

        resolved_device = self._resolve_input_device(device_index if device_index >= 0 else config.device_index)
        resolved_device_index, resolved_device_name = self._device_identity(resolved_device)
        resolved_sample_rate = self._resolve_sample_rate(config=config, device=resolved_device)
        runtime_config = config.model_copy(
            update={
                "device_index": resolved_device_index,
                "sample_rate": resolved_sample_rate,
            }
        )
        pitch_detector, onset_detector = self._build_processors(runtime_config)
        return _PreflightResult(
            config=runtime_config,
            device_index=resolved_device_index,
            device_name=resolved_device_name,
            pitch_detector=pitch_detector,
            onset_detector=onset_detector,
        )

    def _audio_callback(self, indata, frames, time_info, status) -> None:  # pragma: no cover - callback from audio backend
        del frames, time_info
        if status:
            logger.warning("Musical audio stream status: %s", status)

        chunk = np.array(indata[:, 0], dtype=np.float32, copy=True)
        try:
            self._audio_queue.put_nowait(chunk)
        except queue.Full:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._audio_queue.put_nowait(chunk)
            except queue.Full:
                return

    def _process_audio_chunk(self, chunk: np.ndarray) -> None:
        now = time.monotonic()
        with self._lock:
            config = self._active_config
            pitch_detector = self._pitch_detector
            onset_detector = self._onset_detector

        if pitch_detector is None or onset_detector is None:
            return

        level = float(np.sqrt(np.mean(np.square(chunk)))) if chunk.size else 0.0
        if level < config.silence_threshold:
            self._flush_if_idle(now, force=False)
            return

        if pitch_detector is not None and onset_detector is not None:
            pitch_hz = float(pitch_detector(chunk)[0]) if chunk.size else 0.0
            confidence = float(pitch_detector.get_confidence()) if hasattr(pitch_detector, "get_confidence") else None
            onset_detected = bool(onset_detector(chunk)) if chunk.size else False
        else:
            pitch_hz, confidence = self._estimate_pitch_hz(chunk, config.sample_rate)
            onset_detected = False

        with self._lock:
            self._last_pitch_hz = pitch_hz if pitch_hz > 0 else None

        if pitch_hz <= 0 or (confidence is not None and confidence < config.pitch_confidence_threshold):
            self._flush_if_idle(now, force=False)
            return

        semitone = self._hz_to_semitone(pitch_hz)
        self._register_pitch_event(semitone=semitone, confidence=confidence, timestamp=now, onset_detected=onset_detected)
        self._flush_if_idle(now, force=False)

    def _register_pitch_event(
        self,
        *,
        semitone: float,
        confidence: float | None,
        timestamp: float,
        onset_detected: bool,
    ) -> None:
        with self._lock:
            self._last_activity_at = timestamp
            if not self._sequence_events:
                self._sequence_events.append(_DetectedPitchEvent(semitone=semitone, timestamp=timestamp, confidence=confidence))
                return

            last_event = self._sequence_events[-1]
            if onset_detected or abs(semitone - last_event.semitone) >= 0.75:
                if timestamp - last_event.timestamp >= 0.08:
                    self._sequence_events.append(
                        _DetectedPitchEvent(semitone=semitone, timestamp=timestamp, confidence=confidence)
                    )

    def _flush_if_idle(self, now: float, force: bool) -> None:
        with self._lock:
            config = self._active_config
            if not self._sequence_events:
                return
            first_timestamp = self._sequence_events[0].timestamp
            last_activity = self._last_activity_at or self._sequence_events[-1].timestamp
            should_flush = force or (now - last_activity >= 0.45) or (now - first_timestamp >= config.max_pattern_window_seconds)
            if not should_flush:
                return
            detected_events = self._sequence_events
            self._sequence_events = []

        note_events = self._normalize_detected_events(detected_events)
        if len(note_events) < config.min_pattern_notes:
            return

        self.process_note_events(note_events)

    def _normalize_detected_events(self, detected_events: list[_DetectedPitchEvent]) -> list[MusicalAudioNoteEvent]:
        if not detected_events:
            return []

        base_pitch = detected_events[0].semitone
        base_time = detected_events[0].timestamp
        normalized: list[MusicalAudioNoteEvent] = []
        for index, event in enumerate(detected_events):
            next_event = detected_events[index + 1] if index + 1 < len(detected_events) else None
            duration = (next_event.timestamp - event.timestamp) if next_event is not None else None
            normalized.append(
                MusicalAudioNoteEvent(
                    relative_pitch_semitones=round(event.semitone - base_pitch, 4),
                    relative_time_seconds=round(event.timestamp - base_time, 4),
                    duration_seconds=round(duration, 4) if duration is not None else None,
                    confidence=event.confidence,
                )
            )
        return normalized

    def _match_note_events(
        self,
        note_events: list[MusicalAudioNoteEvent],
    ) -> tuple[MusicalAudioTrainingArtifact | None, float | None]:
        with self._lock:
            artifacts = list(self._artifacts)

        if not artifacts:
            return None, None

        candidate_pitch = np.asarray([note.relative_pitch_semitones for note in note_events], dtype=np.double)
        candidate_timing = np.asarray([note.relative_time_seconds for note in note_events], dtype=np.double)
        best_artifact: MusicalAudioTrainingArtifact | None = None
        best_score: float | None = None

        for artifact in artifacts:
            if not artifact.enabled or len(artifact.notes) == 0:
                continue

            artifact_pitch = np.asarray([note.relative_pitch_semitones for note in artifact.notes], dtype=np.double)
            artifact_timing = np.asarray([note.relative_time_seconds for note in artifact.notes], dtype=np.double)
            pitch_distance = self._sequence_distance(candidate_pitch, artifact_pitch)
            timing_distance = 0.0
            if len(candidate_timing) > 1 and len(artifact_timing) > 1:
                timing_distance = self._sequence_distance(candidate_timing, artifact_timing)
            combined_score = pitch_distance + (timing_distance * 0.5)

            if best_score is None or combined_score < best_score:
                best_score = combined_score
                best_artifact = artifact

        if best_artifact is None or best_score is None:
            return None, None
        if best_score > best_artifact.match_threshold:
            return None, best_score
        return best_artifact, best_score

    def _resolve_input_device(self, requested_device_index: int) -> dict[str, object]:
        devices = self.list_input_devices()
        if not devices:
            raise MusicalAudioServiceError(
                "Keine Audioeingabegeraete verfuegbar.",
                status_code=503,
                error_code="device_missing",
            )

        if requested_device_index >= 0:
            for device in devices:
                if device["index"] == requested_device_index:
                    return device
            raise MusicalAudioServiceError(
                f"Eingabegeraet {requested_device_index} wurde nicht gefunden.",
                status_code=404,
                error_code="device_missing",
            )

        default_device = next((device for device in devices if device.get("is_default")), None)
        if default_device is not None:
            return default_device

        return devices[0]

    @staticmethod
    def _device_identity(device: dict[str, object]) -> tuple[int, str]:
        index = device.get("index")
        if not isinstance(index, int):
            raise MusicalAudioServiceError(
                "Audioeingabegeraet hat keinen gueltigen Index.",
                status_code=503,
                error_code="device_missing",
            )
        return index, str(device.get("name", f"Input {index}"))

    def _resolve_sample_rate(self, *, config: MusicalAudioConfig, device: dict[str, object]) -> int:
        resolved_device_index, resolved_device_name = self._device_identity(device)
        candidate_rates: list[int] = [config.sample_rate]
        default_samplerate = device.get("default_samplerate")
        if isinstance(default_samplerate, (float, int)):
            fallback_rate = int(round(float(default_samplerate)))
            if fallback_rate > 0 and fallback_rate not in candidate_rates:
                candidate_rates.append(fallback_rate)

        last_exception: MusicalAudioServiceError | None = None
        for sample_rate in candidate_rates:
            try:
                self._validate_input_settings(
                    device_index=resolved_device_index,
                    device_name=resolved_device_name,
                    sample_rate=sample_rate,
                )
                return sample_rate
            except MusicalAudioServiceError as exc:
                if exc.error_code == "permission_blocked":
                    raise
                last_exception = exc

        if last_exception is not None:
            raise last_exception

        raise MusicalAudioServiceError(
            f"Fuer Eingabegeraet '{resolved_device_name}' konnte keine gueltige Sample-Rate bestimmt werden.",
            status_code=422,
            error_code="invalid_sample_rate",
        )

    def _validate_input_settings(self, *, device_index: int, device_name: str, sample_rate: int) -> None:
        sounddevice_module = sd
        if sounddevice_module is None:
            raise MusicalAudioServiceError(
                self._build_unavailable_message(),
                status_code=503,
                error_code="unavailable",
            )

        checker = getattr(sounddevice_module, "check_input_settings", None)
        if not callable(checker):
            return

        try:
            checker(
                device=device_index,
                channels=1,
                samplerate=sample_rate,
                dtype="float32",
            )
        except (PORTAUDIO_ERROR, RuntimeError, ValueError) as exc:
            if self._is_permission_error(exc):
                raise MusicalAudioServiceError(
                    f"Zugriff auf Eingabegeraet '{device_name}' wurde verweigert.",
                    status_code=403,
                    error_code="permission_blocked",
                ) from exc

            raise MusicalAudioServiceError(
                f"Sample-Rate {sample_rate} Hz wird von Eingabegeraet '{device_name}' nicht unterstuetzt.",
                status_code=422,
                error_code="invalid_sample_rate",
            ) from exc

    @staticmethod
    def _build_processors(config: MusicalAudioConfig):
        if aubio is None:
            raise MusicalAudioServiceError(
                "Musical-Audio-Service benoetigt aubio fuer Pitch- und Onset-Erkennung.",
                status_code=503,
                error_code="unavailable",
            )

        pitch_factory = getattr(aubio, "pitch", None)
        onset_factory = getattr(aubio, "onset", None)
        if not callable(pitch_factory) or not callable(onset_factory):
            raise MusicalAudioServiceError(
                "aubio ist installiert, stellt aber pitch/onset nicht bereit.",
                status_code=503,
                error_code="unavailable",
            )

        pitch_factory_callable = cast(Callable[..., Any], pitch_factory)
        onset_factory_callable = cast(Callable[..., Any], onset_factory)
        win_size = max(config.block_size * 2, 1024)
        pitch_detector = operator.call(
            pitch_factory_callable,
            "yinfft",
            win_size,
            config.block_size,
            config.sample_rate,
        )
        pitch_detector.set_unit("Hz")
        pitch_detector.set_silence(-40)
        onset_detector = operator.call(
            onset_factory_callable,
            "default",
            win_size,
            config.block_size,
            config.sample_rate,
        )
        return pitch_detector, onset_detector

    @staticmethod
    def _hz_to_semitone(pitch_hz: float) -> float:
        return 69.0 + (12.0 * math.log2(pitch_hz / 440.0))

    @staticmethod
    def _sequence_distance(left: np.ndarray, right: np.ndarray) -> float:
        if dtw is None:
            raise MusicalAudioServiceError(
                "Musical-Audio-Service benoetigt dtaidistance fuer DTW-Matching.",
                status_code=503,
                error_code="unavailable",
            )
        return float(dtw.distance_fast(left, right, use_pruning=True))

    def _derive_status_code_locked(self) -> MusicalAudioStatusCode:
        if not self.is_available():
            return "unavailable"
        if not self._active_config.enabled:
            return "configuration_disabled"
        if self._running:
            return "runtime_running_no_matchable_artifacts" if not self._artifacts else "running"
        if self._last_error_code in {
            "device_missing",
            "invalid_sample_rate",
            "permission_blocked",
            "runtime_start_failed",
            "no_active_artifact",
        }:
            return self._last_error_code
        if not self._active_config.active_artifact_id or not self._artifacts:
            return "no_active_artifact"
        return "ready"

    @staticmethod
    def _is_permission_error(exc: BaseException) -> bool:
        message = str(exc).lower()
        return any(keyword in message for keyword in ("permission", "forbidden", "access denied", "not permitted"))

    def _runtime_error_code(self, exc: BaseException) -> MusicalAudioStatusCode:
        if self._is_permission_error(exc):
            return "permission_blocked"
        return "runtime_start_failed"

    def _format_runtime_error(self, exc: BaseException) -> str:
        if self._is_permission_error(exc):
            return "Zugriff auf das konfigurierte Audioeingabegeraet wurde verweigert."
        return str(exc)

    @staticmethod
    def _estimate_pitch_hz(chunk: np.ndarray, sample_rate: int) -> tuple[float, float | None]:
        if chunk.size < 32:
            return 0.0, None

        centered = chunk - float(np.mean(chunk))
        energy = float(np.sqrt(np.mean(np.square(centered))))
        if energy <= 1e-5:
            return 0.0, None

        correlation = np.correlate(centered, centered, mode='full')[chunk.size - 1:]
        min_lag = max(1, int(sample_rate / 1200))
        max_lag = min(len(correlation) - 1, int(sample_rate / 80))
        if max_lag <= min_lag:
            return 0.0, None

        window = correlation[min_lag:max_lag]
        if window.size == 0:
            return 0.0, None

        lag_offset = int(np.argmax(window))
        lag = min_lag + lag_offset
        peak = float(window[lag_offset]) if lag_offset < window.size else 0.0
        base = float(correlation[0]) if correlation.size else 0.0
        confidence = (peak / base) if base > 0 else None
        if lag <= 0 or peak <= 0:
            return 0.0, confidence

        return float(sample_rate / lag), confidence

    def _provider_name(self) -> str:
        if aubio is not None and dtw is not None:
            return 'aubio+dtaidistance'
        return 'unavailable'

    def _build_unavailable_message(self) -> str:
        missing: list[str] = []
        if sd is None:
            missing.append("sounddevice")
        if aubio is None:
            missing.append("aubio")
        if dtw is None:
            missing.append("dtaidistance")
        if missing:
            return f"Musical-Audio-Service ist nicht verfuegbar. Fehlende Abhaengigkeiten: {', '.join(missing)}"
        return "Musical-Audio-Service ist nicht verfuegbar."


musical_audio_service = MusicalAudioService(input_orchestrator_service=input_orchestrator)