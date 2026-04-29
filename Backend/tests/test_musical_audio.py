from concurrent.futures import Future
from types import SimpleNamespace

import pytest

from schemas.commands import CommandModalitySettings, CommandProfile
from schemas.interactions import InputActionConfig, InputActionMapping
from schemas.musical_audio import MusicalAudioConfig, MusicalAudioNoteEvent, MusicalAudioTrainingArtifact
from services import musical_audio as musical_audio_module
from services.musical_audio import MusicalAudioService, MusicalAudioServiceError


class CapturingRealtimeHub:
    def __init__(self):
        self.messages = []

    def publish_from_thread(self, message):
        self.messages.append(message)
        future = Future()
        future.set_result(None)
        return future


class StaticMusicalAudioRepository:
    def __init__(self):
        self.musical_audio_config = MusicalAudioConfig(enabled=True, active_artifact_id="whistle-main")
        self.artifacts = [
            MusicalAudioTrainingArtifact(
                artifact_id="whistle-main",
                raw_input="melody.whistle_main",
                display_name="Main whistle",
                notes=[
                    MusicalAudioNoteEvent(relative_pitch_semitones=0.0, relative_time_seconds=0.0),
                    MusicalAudioNoteEvent(relative_pitch_semitones=2.0, relative_time_seconds=0.3),
                    MusicalAudioNoteEvent(relative_pitch_semitones=4.0, relative_time_seconds=0.6),
                ],
                match_threshold=0.6,
                sample_count=14,
            )
        ]
        self.command_profile = CommandProfile(
            input_action_config=InputActionConfig(
                mappings=[
                    InputActionMapping(
                        input_source="musical_audio",
                        raw_input="melody.whistle_main",
                        action="toggle_shop",
                    )
                ]
            ),
            modality_settings={
                "gesture": CommandModalitySettings(enabled=True),
                "voice": CommandModalitySettings(enabled=True),
                "musical_audio": CommandModalitySettings(enabled=True),
                "keyboard": CommandModalitySettings(enabled=True),
                "dev": CommandModalitySettings(enabled=True),
            },
        )

    def get_musical_audio_config(self):
        return self.musical_audio_config

    def list_musical_audio_training_artifacts(self, profile_id: str = "default"):
        _ = profile_id
        return self.artifacts

    def get_input_action_config(self):
        return self.command_profile.input_action_config

    def get_active_command_profile(self):
        return self.command_profile


class ConfigurableMusicalAudioRepository(StaticMusicalAudioRepository):
    def __init__(
        self,
        *,
        enabled: bool = True,
        active_artifact_id: str | None = "whistle-main",
        device_index: int | None = 1,
        sample_rate: int = 16000,
    ):
        super().__init__()
        self.musical_audio_config = self.musical_audio_config.model_copy(
            update={
                "enabled": enabled,
                "active_artifact_id": active_artifact_id,
                "device_index": device_index if device_index is not None else -1,
                "sample_rate": sample_rate,
            }
        )
        self.command_profile = self.command_profile.model_copy(
            update={
                "modality_settings": {
                    **self.command_profile.modality_settings,
                    "musical_audio": self.command_profile.modality_settings["musical_audio"].model_copy(
                        update={
                            "enabled": enabled,
                            "active_training_artifact_id": active_artifact_id,
                        }
                    ),
                },
                "device_preferences": self.command_profile.device_preferences.model_copy(
                    update={"musical_audio_device_index": device_index}
                ),
            }
        )


class FakePitchDetector:
    def set_unit(self, _value):
        return None

    def set_silence(self, _value):
        return None

    def __call__(self, _chunk):
        return [440.0]

    def get_confidence(self):
        return 0.9


class FakeOnsetDetector:
    def __call__(self, _chunk):
        return 0.0


class FakeInputStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        _ = exc_type, exc, tb
        return False


class FakeSoundDevice:
    PortAudioError = RuntimeError

    def __init__(self, *, valid_rates: dict[int, set[int]] | None = None):
        self.default = SimpleNamespace(device=(1, None))
        self.checked: list[tuple[int, int, int, str]] = []
        self.stream_calls: list[dict[str, object]] = []
        self.valid_rates = valid_rates or {1: {48000}}

    def query_devices(self):
        return [
            {"name": "Output only", "max_input_channels": 0, "default_samplerate": 48000.0},
            {"name": "Mock Runtime Mic", "max_input_channels": 1, "default_samplerate": 48000.0},
        ]

    def check_input_settings(self, *, device, channels, samplerate, dtype):
        self.checked.append((device, channels, samplerate, dtype))
        if samplerate not in self.valid_rates.get(device, set()):
            raise RuntimeError("Invalid sample rate")

    def InputStream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return FakeInputStream(**kwargs)


class FakeAubio:
    @staticmethod
    def pitch(*_args, **_kwargs):
        return FakePitchDetector()

    @staticmethod
    def onset(*_args, **_kwargs):
        return FakeOnsetDetector()


class FakeDtw:
    @staticmethod
    def distance_fast(_left, _right, use_pruning=True):
        _ = use_pruning
        return 0.0


@pytest.mark.asyncio
async def test_get_musical_audio_status(client, override_musical_audio_dependency):
    _ = override_musical_audio_dependency
    response = await client.get("/api/v1/musical-audio/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == "unavailable"
    assert data["mode"] == "unavailable"
    assert data["provider"] == "aubio+dtaidistance"


@pytest.mark.asyncio
async def test_get_musical_audio_devices(client, override_musical_audio_dependency):
    _ = override_musical_audio_dependency
    response = await client.get("/api/v1/musical-audio/devices")
    assert response.status_code == 200
    data = response.json()
    assert len(data["devices"]) == 1
    assert data["devices"][0]["is_default"] is True


@pytest.mark.asyncio
async def test_start_musical_audio_returns_clear_status_error(client, override_musical_audio_dependency):
    _ = override_musical_audio_dependency
    response = await client.post("/api/v1/musical-audio/start", json={"device_index": 1})
    assert response.status_code == 503
    assert "Musical-Audio-Service" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stop_musical_audio(client, override_musical_audio_dependency):
    _ = override_musical_audio_dependency
    response = await client.post("/api/v1/musical-audio/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Musical audio stopped"
    assert data["running"] is False


def test_musical_audio_service_matches_note_events_and_publishes_semantic_action():
    hub = CapturingRealtimeHub()
    service = MusicalAudioService(
        realtime=hub,
        config_repository_factory=StaticMusicalAudioRepository,
    )
    service.reload_config()

    accepted = service.process_note_events(
        [
            MusicalAudioNoteEvent(relative_pitch_semitones=0.0, relative_time_seconds=0.0, confidence=0.95),
            MusicalAudioNoteEvent(relative_pitch_semitones=2.0, relative_time_seconds=0.31, confidence=0.93),
            MusicalAudioNoteEvent(relative_pitch_semitones=4.0, relative_time_seconds=0.62, confidence=0.91),
        ]
    )

    assert accepted is True
    event_types = [message["eventType"] for message in hub.messages]
    assert event_types == ["RawInputDetected", "CommandMatchEvaluated", "UIActionRequested"]
    assert hub.messages[0]["payload"]["input_source"] == "musical_audio"
    assert hub.messages[1]["payload"]["outcome"] == "accepted"
    assert hub.messages[2]["payload"]["action"] == "toggle_shop"
    assert hub.messages[2]["payload"]["raw_input"] == "melody.whistle_main"


def test_musical_audio_service_start_requires_active_artifact(monkeypatch):
    fake_sd = FakeSoundDevice(valid_rates={1: {16000}})
    monkeypatch.setattr(musical_audio_module, "sd", fake_sd)
    monkeypatch.setattr(musical_audio_module, "aubio", FakeAubio())
    monkeypatch.setattr(musical_audio_module, "dtw", FakeDtw())
    monkeypatch.setattr(musical_audio_module, "PORTAUDIO_ERROR", RuntimeError)

    service = MusicalAudioService(
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: ConfigurableMusicalAudioRepository(active_artifact_id=None),
    )
    service.reload_config()

    with pytest.raises(MusicalAudioServiceError) as exc_info:
        service.start(device_index=1)

    assert exc_info.value.error_code == "no_active_artifact"
    status = service.get_status()
    assert status["status_code"] == "no_active_artifact"
    assert status["last_error_code"] == "no_active_artifact"


def test_musical_audio_service_start_falls_back_to_supported_sample_rate(monkeypatch):
    fake_sd = FakeSoundDevice(valid_rates={1: {48000}})
    monkeypatch.setattr(musical_audio_module, "sd", fake_sd)
    monkeypatch.setattr(musical_audio_module, "aubio", FakeAubio())
    monkeypatch.setattr(musical_audio_module, "dtw", FakeDtw())
    monkeypatch.setattr(musical_audio_module, "PORTAUDIO_ERROR", RuntimeError)

    service = MusicalAudioService(
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: ConfigurableMusicalAudioRepository(sample_rate=16000),
    )

    status = service.start(device_index=1)

    assert status["running"] is True
    assert status["sample_rate"] == 48000
    assert status["validated_device_index"] == 1
    assert status["validated_sample_rate"] == 48000
    assert fake_sd.checked == [
        (1, 1, 16000, "float32"),
        (1, 1, 48000, "float32"),
    ]

    stopped = service.stop()
    assert stopped["running"] is False
    assert stopped["status_code"] == "ready"


def test_musical_audio_service_start_reports_invalid_device(monkeypatch):
    fake_sd = FakeSoundDevice(valid_rates={1: {16000}})
    monkeypatch.setattr(musical_audio_module, "sd", fake_sd)
    monkeypatch.setattr(musical_audio_module, "aubio", FakeAubio())
    monkeypatch.setattr(musical_audio_module, "dtw", FakeDtw())
    monkeypatch.setattr(musical_audio_module, "PORTAUDIO_ERROR", RuntimeError)

    service = MusicalAudioService(
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: ConfigurableMusicalAudioRepository(),
    )

    with pytest.raises(MusicalAudioServiceError) as exc_info:
        service.start(device_index=99)

    assert exc_info.value.error_code == "device_missing"
    assert service.get_status()["status_code"] == "device_missing"


def test_musical_audio_service_start_reports_invalid_sample_rate_without_fallback(monkeypatch):
    fake_sd = FakeSoundDevice(valid_rates={1: set()})
    monkeypatch.setattr(musical_audio_module, "sd", fake_sd)
    monkeypatch.setattr(musical_audio_module, "aubio", FakeAubio())
    monkeypatch.setattr(musical_audio_module, "dtw", FakeDtw())
    monkeypatch.setattr(musical_audio_module, "PORTAUDIO_ERROR", RuntimeError)

    service = MusicalAudioService(
        realtime=CapturingRealtimeHub(),
        config_repository_factory=lambda: ConfigurableMusicalAudioRepository(sample_rate=22050),
    )

    with pytest.raises(MusicalAudioServiceError) as exc_info:
        service.start(device_index=1)

    assert exc_info.value.error_code == "invalid_sample_rate"
    status = service.get_status()
    assert status["status_code"] == "invalid_sample_rate"
    assert status["last_error_code"] == "invalid_sample_rate"