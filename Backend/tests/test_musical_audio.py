from concurrent.futures import Future

import pytest

from schemas.commands import CommandModalitySettings, CommandProfile
from schemas.interactions import InputActionConfig, InputActionMapping
from schemas.musical_audio import MusicalAudioConfig, MusicalAudioNoteEvent, MusicalAudioTrainingArtifact
from services.musical_audio import MusicalAudioService


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


@pytest.mark.asyncio
async def test_get_musical_audio_status(client, override_musical_audio_dependency):
    _ = override_musical_audio_dependency
    response = await client.get("/api/v1/musical-audio/status")
    assert response.status_code == 200
    data = response.json()
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