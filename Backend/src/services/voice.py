from array import array
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import queue
import re
import threading
import time
from typing import Any

from core.config import settings
from core.realtime import RealtimeHub, realtime_hub
from repositories.config import ConfigRepository
from schemas.voice import VoiceConfig
from services.input.orchestrator import InputOrchestrator, input_orchestrator

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional runtime dependency
    sd = None

try:
    from vosk import KaldiRecognizer, Model
except ImportError:  # pragma: no cover - optional runtime dependency
    KaldiRecognizer = None
    Model = None


logger = logging.getLogger(__name__)
PORTAUDIO_ERROR = getattr(sd, "PortAudioError", OSError) if sd is not None else OSError

GERMAN_NUMBER_WORDS = {
    1: ["eins"],
    2: ["zwei"],
    3: ["drei"],
    4: ["vier"],
    5: ["fuenf", "funf"],
    6: ["sechs"],
    7: ["sieben"],
    8: ["acht"],
    9: ["neun"],
    10: ["zehn"],
    11: ["elf"],
    12: ["zwoelf", "zwolf"],
    13: ["dreizehn"],
    14: ["vierzehn"],
    15: ["fuenfzehn", "funfzehn"],
    16: ["sechzehn"],
}


@dataclass(frozen=True)
class VoiceCommandMatch:
    command: str
    raw_input: str
    action_args: dict[str, Any]


class VoiceServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class VoiceService:
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
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=1)
        self._active_config = VoiceConfig()
        self._running = False
        self._device_index: int | None = None
        self._device_name: str | None = None
        self._recognizer = None
        self._model = None
        self._chunks_processed = 0
        self._chunks_dropped = 0
        self._last_audio_level = 0.0
        self._last_transcript: str | None = None
        self._last_command: str | None = None
        self._last_command_at: datetime | None = None
        self._last_command_time_by_name: dict[str, float] = {}
        self._last_error: str | None = self._build_unavailable_message()

    def startup(self) -> None:
        self.reload_config()
        with self._lock:
            if self.is_available() and self._active_config.enabled:
                self._last_error = None
            else:
                self._last_error = self._build_unavailable_message()

    def reload_config(self) -> VoiceConfig:
        try:
            config = self.config_repository_factory().get_voice_config()
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("Could not reload voice config, using defaults: %s", exc)
            config = VoiceConfig()

        self.input_orchestrator.reload_config()

        with self._lock:
            self._active_config = config
        return config

    def is_available(self) -> bool:
        if sd is None or Model is None or KaldiRecognizer is None:
            return False

        model_path = settings.VOICE_MODEL_PATH.strip()
        if not model_path:
            return False

        return Path(model_path).expanduser().exists()

    def get_status(self) -> dict[str, object]:
        with self._lock:
            available = self.is_available()
            mode = "direct-mic" if available else "unavailable"
            last_error = self._last_error
            if last_error is None and (not available or not self._active_config.enabled):
                last_error = self._build_unavailable_message()
            return {
                "message": "Voice status",
                "available": available,
                "enabled": self._active_config.enabled,
                "running": self._running,
                "mode": mode,
                "provider": "vosk",
                "device_index": self._device_index,
                "device_name": self._device_name,
                "sample_rate": self._active_config.sample_rate,
                "block_size": self._active_config.block_size,
                "queue_max_chunks": self._active_config.queue_max_chunks,
                "commands": list(self._active_config.commands) or [
                    phrase
                    for signal in self._active_config.signals
                    for phrase in signal.phrases
                ],
                "partial_results_enabled": self._active_config.partial_results_enabled,
                "command_cooldown_seconds": self._active_config.command_cooldown_seconds,
                "chunks_processed": self._chunks_processed,
                "chunks_dropped": self._chunks_dropped,
                "last_audio_level": self._last_audio_level,
                "last_transcript": self._last_transcript,
                "last_command": self._last_command,
                "last_command_at": self._last_command_at,
                "last_error": last_error,
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
                        float(device["default_samplerate"])
                        if device.get("default_samplerate") is not None
                        else None
                    ),
                    "is_default": isinstance(default_input, int) and default_input == index,
                }
            )

        return result

    def start(self, device_index: int = -1) -> dict[str, object]:
        config = self.reload_config()

        with self._lock:
            if self._running:
                return self.get_status()

        if not config.enabled:
            with self._lock:
                self._last_error = "Voice service ist per Konfiguration deaktiviert."
            raise VoiceServiceError("Voice service ist per Konfiguration deaktiviert.", status_code=503)

        if not self.is_available():
            message = self._build_unavailable_message()
            with self._lock:
                self._last_error = message
            raise VoiceServiceError(message, status_code=503)

        requested_device_index = device_index if device_index >= 0 else config.device_index
        resolved_device_index, resolved_device_name = self._resolve_input_device(requested_device_index)
        model_path = Path(settings.VOICE_MODEL_PATH).expanduser()

        try:
            model = Model(str(model_path))
            recognizer = KaldiRecognizer(model, config.sample_rate)
        except Exception as exc:  # pragma: no cover - depends on runtime model files
            logger.exception("Voice recognizer initialization failed")
            with self._lock:
                self._last_error = str(exc)
            raise VoiceServiceError(f"Voice recognizer konnte nicht initialisiert werden: {exc}", status_code=503) from exc

        with self._lock:
            self._audio_queue = queue.Queue(maxsize=config.queue_max_chunks)
            self._stop_event.clear()
            self._running = True
            self._device_index = resolved_device_index
            self._device_name = resolved_device_name
            self._recognizer = recognizer
            self._model = model
            self._chunks_processed = 0
            self._chunks_dropped = 0
            self._last_audio_level = 0.0
            self._last_transcript = None
            self._last_command_time_by_name.clear()
            self._last_error = None
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

        return self.get_status()

    def stop(self) -> dict[str, object]:
        thread = None
        with self._lock:
            self._running = False
            self._stop_event.set()
            thread = self._thread
            self._thread = None

        if thread is not None:
            thread.join(timeout=settings.VOICE_STOP_JOIN_TIMEOUT_SECONDS)
            if thread.is_alive():
                logger.warning(
                    "Voice thread did not stop within %.2f seconds.",
                    settings.VOICE_STOP_JOIN_TIMEOUT_SECONDS,
                )

        with self._lock:
            self._device_index = None
            self._device_name = None
            self._recognizer = None
            self._model = None
            status = self.get_status()

        return {
            **status,
            "message": "Voice stopped",
        }

    def note_command(self, command: str, transcript: str | None = None) -> None:
        with self._lock:
            self._last_command = command
            self._last_command_at = datetime.now(timezone.utc)
            if transcript is not None:
                self._last_transcript = transcript

    def shutdown(self) -> None:
        self.stop()

    def _run_loop(self) -> None:
        with self._lock:
            config = self._active_config
            device_index = self._device_index

        try:
            with sd.RawInputStream(
                samplerate=config.sample_rate,
                blocksize=config.block_size,
                device=device_index,
                channels=1,
                dtype="int16",
                callback=self._audio_callback,
            ):
                while not self._stop_event.is_set():
                    try:
                        chunk = self._audio_queue.get(timeout=0.25)
                    except queue.Empty:
                        continue

                    self._process_audio_chunk(chunk)
        except (PORTAUDIO_ERROR, RuntimeError, ValueError) as exc:  # pragma: no cover - depends on audio hardware
            logger.exception("Voice capture loop failed")
            with self._lock:
                self._last_error = str(exc)
                self._running = False
        finally:
            with self._lock:
                self._running = False

    def _audio_callback(self, indata, frames, time_info, status) -> None:  # pragma: no cover - callback from audio backend
        del frames, time_info

        if status:
            logger.warning("Voice stream status: %s", status)

        chunk = bytes(indata)
        audio_level = self._compute_audio_level(chunk)
        with self._lock:
            self._last_audio_level = audio_level
            threshold = self._active_config.energy_threshold

        if threshold > 0 and audio_level < threshold:
            return

        self._enqueue_audio_chunk(chunk)

    def _enqueue_audio_chunk(self, chunk: bytes) -> None:
        try:
            self._audio_queue.put_nowait(chunk)
        except queue.Full:
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                pass

            with self._lock:
                self._chunks_dropped += 1

            try:
                self._audio_queue.put_nowait(chunk)
            except queue.Full:
                with self._lock:
                    self._chunks_dropped += 1

    def _process_audio_chunk(self, chunk: bytes) -> None:
        with self._lock:
            recognizer = self._recognizer
            partial_results_enabled = self._active_config.partial_results_enabled

        if recognizer is None:
            return

        try:
            is_final = recognizer.AcceptWaveform(chunk)
            payload = recognizer.Result() if is_final else recognizer.PartialResult()
        except (AttributeError, RuntimeError, TypeError, ValueError) as exc:  # pragma: no cover - depends on recognizer runtime
            logger.exception("Voice recognizer failed")
            with self._lock:
                self._last_error = str(exc)
            return

        transcript = self._extract_transcript(payload, is_final=is_final)
        with self._lock:
            self._chunks_processed += 1
            if transcript:
                self._last_transcript = transcript

        if not transcript:
            return

        if is_final or partial_results_enabled:
            self._handle_transcript(transcript, partial=not is_final)

    def _handle_transcript(self, transcript: str, partial: bool) -> None:
        match = self._match_command(transcript)
        if match is None:
            return

        now = time.monotonic()
        timestamp = datetime.now(timezone.utc)
        with self._lock:
            cooldown = self._active_config.command_cooldown_seconds
            last_seen = self._last_command_time_by_name.get(match.command)
            if last_seen is not None and now - last_seen < cooldown:
                return

            self._last_command_time_by_name[match.command] = now
            self._last_command = match.command
            self._last_command_at = timestamp
            device_index = self._device_index

        event = {
            "eventType": "VoiceCommandDetected",
            "payload": {
                "command": match.command,
                "raw_input": match.raw_input,
                "timestamp": timestamp.isoformat(),
                "source": "microphone",
                "transcript": transcript,
                "partial": partial,
                "device_index": device_index,
            },
        }
        self.realtime.publish_from_thread(event)
        metadata = {
            "command": match.command,
            "transcript": transcript,
            "partial": partial,
            "device_index": device_index,
        }
        self.input_orchestrator.publish_raw_input_detected(
            input_source="voice",
            raw_input=match.raw_input,
            timestamp=timestamp,
            metadata=metadata,
        )
        self.input_orchestrator.publish_ui_action_requested(
            input_source="voice",
            raw_input=match.raw_input,
            timestamp=timestamp,
            action_args=match.action_args,
            metadata=metadata,
        )

    def _match_command(self, transcript: str) -> VoiceCommandMatch | None:
        normalized_transcript = self._normalize_text(transcript)
        if not normalized_transcript:
            return None

        with self._lock:
            config = self._active_config.model_copy(deep=True)

        targeted_resize_match = self._match_targeted_resize(normalized_transcript, config)
        if targeted_resize_match is not None:
            return targeted_resize_match

        focus_cell_match = self._match_focus_grid_cell(normalized_transcript, config)
        if focus_cell_match is not None:
            return focus_cell_match

        widget_type_match = self._match_focus_widget_type(normalized_transcript, config)
        if widget_type_match is not None:
            return widget_type_match

        signal_match = self._match_defined_signal(normalized_transcript, config)
        if signal_match is not None:
            return signal_match

        legacy_command = self._match_legacy_command(normalized_transcript, config.commands)
        if legacy_command is None:
            return None

        return VoiceCommandMatch(
            command=legacy_command,
            raw_input=self._normalize_command_identifier(legacy_command),
            action_args={},
        )

    def _match_defined_signal(self, normalized_transcript: str, config: VoiceConfig) -> VoiceCommandMatch | None:
        for signal in config.signals:
            for phrase in signal.phrases:
                if normalized_transcript != self._normalize_text(phrase):
                    continue

                return VoiceCommandMatch(
                    command=signal.raw_input,
                    raw_input=signal.raw_input,
                    action_args=signal.action_args.model_dump(exclude_none=True),
                )

        return None

    def _match_focus_grid_cell(self, normalized_transcript: str, config: VoiceConfig) -> VoiceCommandMatch | None:
        cell_index = self._extract_cell_index(normalized_transcript, config.grid_cell_count)
        if cell_index is None:
            return None

        return VoiceCommandMatch(
            command=f"voice.focus_grid_cell[{cell_index}]",
            raw_input="voice.focus_grid_cell",
            action_args={"cell_index": cell_index, "mode": "grid"},
        )

    def _match_focus_widget_type(self, normalized_transcript: str, config: VoiceConfig) -> VoiceCommandMatch | None:
        normalized_alias_map = {
            self._normalize_text(alias): widget_type
            for widget_type, aliases in config.widget_aliases.items()
            for alias in aliases
        }
        widget_type = normalized_alias_map.get(normalized_transcript)
        if widget_type is None:
            return None

        return VoiceCommandMatch(
            command=f"voice.focus_widget_type[{widget_type}]",
            raw_input="voice.focus_widget_type",
            action_args={"widget_type": widget_type},
        )

    def _match_targeted_resize(self, normalized_transcript: str, config: VoiceConfig) -> VoiceCommandMatch | None:
        for raw_input in ("voice.resize_expand", "voice.resize_shrink"):
            resize_phrases = [
                self._normalize_text(phrase)
                for signal in config.signals
                if signal.raw_input == raw_input
                for phrase in signal.phrases
            ]
            for resize_phrase in resize_phrases:
                for prefix in ("feld ", "zelle "):
                    if not normalized_transcript.startswith(prefix):
                        continue
                    if not normalized_transcript.endswith(f" {resize_phrase}"):
                        continue

                    number_phrase = normalized_transcript[len(prefix): -len(f" {resize_phrase}")].strip()
                    cell_index = self._parse_number_phrase(number_phrase, config.grid_cell_count)
                    if cell_index is None:
                        continue

                    return VoiceCommandMatch(
                        command=f"{raw_input}[{cell_index}]",
                        raw_input=raw_input,
                        action_args={"cell_index": cell_index, "mode": "grid"},
                    )

        return None

    @classmethod
    def _match_legacy_command(cls, normalized_transcript: str, commands: list[str]) -> str | None:
        if not normalized_transcript:
            return None

        for command in sorted(commands, key=len, reverse=True):
            normalized_command = cls._normalize_text(command)
            if not normalized_command:
                continue
            if normalized_transcript == normalized_command or normalized_command in normalized_transcript:
                return command

        return None

    def _resolve_input_device(self, requested_index: int) -> tuple[int, str]:
        if sd is None:
            raise VoiceServiceError("sounddevice ist nicht installiert.", status_code=503)

        if requested_index >= 0:
            try:
                device = sd.query_devices(requested_index, "input")
            except Exception as exc:  # pragma: no cover - hardware dependent
                raise VoiceServiceError(f"Eingabegeraet {requested_index} konnte nicht gelesen werden: {exc}", status_code=503) from exc

            return requested_index, str(device["name"])

        try:
            devices = sd.query_devices()
        except (PORTAUDIO_ERROR, RuntimeError) as exc:  # pragma: no cover - hardware dependent
            raise VoiceServiceError(f"Eingabegeraete konnten nicht gelesen werden: {exc}", status_code=503) from exc

        try:
            default_input = sd.default.device[0]
        except (AttributeError, PORTAUDIO_ERROR, RuntimeError):  # pragma: no cover - backend dependent
            default_input = None

        candidate_indices: list[int] = []
        if isinstance(default_input, int) and default_input >= 0:
            candidate_indices.append(default_input)

        for index, device in enumerate(devices):
            if int(device.get("max_input_channels", 0)) <= 0:
                continue
            if index not in candidate_indices:
                candidate_indices.append(index)

        if not candidate_indices:
            raise VoiceServiceError("Kein Audio-Eingabegeraet verfuegbar.", status_code=503)

        index = candidate_indices[0]
        return index, str(devices[index]["name"])

    @classmethod
    def _extract_cell_index(cls, normalized_transcript: str, grid_cell_count: int) -> int | None:
        if normalized_transcript.startswith("feld "):
            return cls._parse_number_phrase(normalized_transcript.removeprefix("feld ").strip(), grid_cell_count)
        if normalized_transcript.startswith("zelle "):
            return cls._parse_number_phrase(normalized_transcript.removeprefix("zelle ").strip(), grid_cell_count)
        if " " in normalized_transcript:
            return None
        return cls._parse_number_phrase(normalized_transcript, grid_cell_count)

    @classmethod
    def _parse_number_phrase(cls, number_phrase: str, grid_cell_count: int) -> int | None:
        if not number_phrase:
            return None

        if number_phrase.isdigit():
            value = int(number_phrase)
            return value if 1 <= value <= grid_cell_count else None

        normalized = cls._normalize_text(number_phrase)
        for value, aliases in GERMAN_NUMBER_WORDS.items():
            if value > grid_cell_count:
                continue
            if normalized in aliases:
                return value

        return None

    def _build_unavailable_message(self) -> str:
        with self._lock:
            enabled = self._active_config.enabled

        if not enabled:
            return "Voice service ist per Konfiguration deaktiviert."
        if sd is None:
            return "sounddevice ist nicht installiert."
        if Model is None or KaldiRecognizer is None:
            return "Vosk ist nicht verfuegbar."
        if not settings.VOICE_MODEL_PATH.strip():
            return "VOICE_MODEL_PATH ist nicht konfiguriert."
        if not Path(settings.VOICE_MODEL_PATH).expanduser().exists():
            return "Vosk-Modellpfad wurde nicht gefunden."
        return "Voice service ist nicht verfuegbar."

    @staticmethod
    def _compute_audio_level(chunk: bytes) -> float:
        samples = array("h")
        samples.frombytes(chunk)
        if not samples:
            return 0.0

        square_sum = sum(sample * sample for sample in samples)
        return (square_sum / len(samples)) ** 0.5

    @staticmethod
    def _extract_transcript(payload: str, is_final: bool) -> str | None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        key = "text" if is_final else "partial"
        value = data.get(key)
        if not isinstance(value, str):
            return None

        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.lower()
        normalized = (
            normalized.replace("ae", "ae")
            .replace("oe", "oe")
            .replace("ue", "ue")
            .replace("ss", "ss")
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        return " ".join(normalized.split())

    @classmethod
    def _normalize_command_identifier(cls, command: str) -> str:
        normalized_command = cls._normalize_text(command)
        if not normalized_command:
            return "voice.unknown"
        return f"voice.{normalized_command.replace(' ', '_')}"


voice_service = VoiceService(input_orchestrator_service=input_orchestrator)