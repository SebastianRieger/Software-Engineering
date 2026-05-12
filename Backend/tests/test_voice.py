from concurrent.futures import Future

import pytest

from schemas.interactions import InputActionConfig, InputActionMapping
from schemas.voice import VoiceConfig, VoiceSignalDefinition
from services.voice import VoiceService


class CapturingRealtimeHub:
    def __init__(self):
        self.messages = []

    def publish_from_thread(self, message):
        self.messages.append(message)
        future = Future()
        future.set_result(None)
        return future


class StaticVoiceConfigRepository:
    def __init__(
        self,
        voice_config: VoiceConfig | None = None,
        input_action_config: InputActionConfig | None = None,
    ):
        self.voice_config = voice_config or VoiceConfig(
            commands=[],
            signals=[VoiceSignalDefinition(raw_input="voice.open_shop", phrases=["shop auf"])],
        )
        self.input_action_config = input_action_config or InputActionConfig(
            mappings=[
                InputActionMapping(
                    input_source="voice",
                    raw_input="voice.open_shop",
                    action="open_shop",
                )
            ]
        )

    def get_voice_config(self):
        return self.voice_config

    def get_input_action_config(self):
        return self.input_action_config


@pytest.mark.asyncio
async def test_get_voice_status(client, override_voice_dependency):
    _ = override_voice_dependency
    response = await client.get("/api/v1/voice/status")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "unavailable"
    assert data["available"] is False
    assert data["sample_rate"] == 16000


@pytest.mark.asyncio
async def test_get_voice_devices(client, override_voice_dependency):
    _ = override_voice_dependency
    response = await client.get("/api/v1/voice/devices")
    assert response.status_code == 200
    data = response.json()
    assert len(data["devices"]) == 2
    assert data["devices"][0]["is_default"] is True


@pytest.mark.asyncio
async def test_start_voice_returns_clear_status_error(client, override_voice_dependency):
    _ = override_voice_dependency
    response = await client.post("/api/v1/voice/start", json={"device_index": 0})
    assert response.status_code == 503
    assert "VOICE_MODEL_PATH" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stop_voice(client, override_voice_dependency):
    _ = override_voice_dependency
    response = await client.post("/api/v1/voice/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert data["message"] == "Voice stopped"


def test_voice_service_publishes_raw_input_and_ui_action_for_mapped_command():
    hub = CapturingRealtimeHub()
    service = VoiceService(
        realtime=hub,
        config_repository_factory=lambda: StaticVoiceConfigRepository(),
    )

    service.reload_config()
    service._handle_transcript("shop auf", partial=False)

    event_types = [message["eventType"] for message in hub.messages]
    assert event_types == ["VoiceCommandDetected", "RawInputDetected", "CommandMatchEvaluated", "UIActionRequested"]
    assert hub.messages[0]["payload"]["raw_input"] == "voice.open_shop"
    assert hub.messages[1]["payload"]["input_source"] == "voice"
    assert hub.messages[1]["payload"]["raw_input"] == "voice.open_shop"
    assert hub.messages[2]["payload"]["outcome"] == "accepted"
    assert hub.messages[3]["payload"]["action"] == "open_shop"
    assert hub.messages[3]["payload"]["input_source"] == "voice"
    assert hub.messages[3]["payload"]["raw_input"] == "voice.open_shop"


def test_voice_service_parses_grid_cell_focus_command_with_structured_action_args():
    hub = CapturingRealtimeHub()
    service = VoiceService(
        realtime=hub,
        config_repository_factory=lambda: StaticVoiceConfigRepository(
            voice_config=VoiceConfig(commands=[]),
            input_action_config=InputActionConfig(
                mappings=[
                    InputActionMapping(
                        input_source="voice",
                        raw_input="voice.focus_grid_cell",
                        action="focus_grid_cell",
                    )
                ]
            ),
        ),
    )

    service.reload_config()
    service._handle_transcript("feld vier", partial=False)

    assert hub.messages[0]["payload"]["raw_input"] == "voice.focus_grid_cell"
    assert hub.messages[2]["payload"]["action_args"] == {"cell_index": 4, "mode": "grid"}
    assert hub.messages[3]["payload"]["action"] == "focus_grid_cell"
    assert hub.messages[3]["payload"]["action_args"] == {"cell_index": 4, "mode": "grid"}


def test_voice_service_parses_widget_type_command_with_structured_action_args():
    hub = CapturingRealtimeHub()
    service = VoiceService(
        realtime=hub,
        config_repository_factory=lambda: StaticVoiceConfigRepository(
            voice_config=VoiceConfig(commands=[]),
            input_action_config=InputActionConfig(
                mappings=[
                    InputActionMapping(
                        input_source="voice",
                        raw_input="voice.focus_widget_type",
                        action="focus_widget_type",
                    )
                ]
            ),
        ),
    )

    service.reload_config()
    service._handle_transcript("wetter", partial=False)

    assert hub.messages[0]["payload"]["raw_input"] == "voice.focus_widget_type"
    assert hub.messages[2]["payload"]["action_args"] == {"widget_type": "weather"}
    assert hub.messages[3]["payload"]["action"] == "focus_widget_type"
    assert hub.messages[3]["payload"]["action_args"] == {"widget_type": "weather"}


def test_voice_service_parses_targeted_resize_command_with_cell_reference():
    hub = CapturingRealtimeHub()
    service = VoiceService(
        realtime=hub,
        config_repository_factory=lambda: StaticVoiceConfigRepository(
            voice_config=VoiceConfig(commands=[]),
            input_action_config=InputActionConfig(
                mappings=[
                    InputActionMapping(
                        input_source="voice",
                        raw_input="voice.resize_expand",
                        action="resize_expand",
                    )
                ]
            ),
        ),
    )

    service.reload_config()
    service._handle_transcript("feld drei groesser", partial=False)

    assert hub.messages[0]["payload"]["raw_input"] == "voice.resize_expand"
    assert hub.messages[2]["payload"]["action_args"] == {"cell_index": 3, "mode": "grid"}
    assert hub.messages[3]["payload"]["action"] == "resize_expand"
    assert hub.messages[3]["payload"]["action_args"] == {"cell_index": 3, "mode": "grid"}