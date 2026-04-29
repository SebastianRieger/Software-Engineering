from concurrent.futures import Future

import pytest

from schemas.interactions import InputActionConfig, InputActionMapping
from schemas.voice import VoiceConfig
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
        self.voice_config = voice_config or VoiceConfig(commands=["shop auf"])
        self.input_action_config = input_action_config or InputActionConfig(
            mappings=[
                InputActionMapping(
                    input_source="voice",
                    raw_input="voice.shop_auf",
                    action="toggle_shop",
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
    assert hub.messages[0]["payload"]["raw_input"] == "voice.shop_auf"
    assert hub.messages[1]["payload"]["input_source"] == "voice"
    assert hub.messages[1]["payload"]["raw_input"] == "voice.shop_auf"
    assert hub.messages[2]["payload"]["outcome"] == "accepted"
    assert hub.messages[3]["payload"]["action"] == "toggle_shop"
    assert hub.messages[3]["payload"]["input_source"] == "voice"
    assert hub.messages[3]["payload"]["raw_input"] == "voice.shop_auf"