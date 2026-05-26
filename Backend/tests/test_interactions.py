from datetime import datetime, timezone

from concurrent.futures import Future

import pytest

from api.system_endpoints import get_input_orchestrator
from main import app
from schemas.commands import CommandModalitySettings, CommandProfile
from schemas.interactions import InputActionConfig, InputActionMapping
from services.gesture import gesture_service
from services.interactions import InputOrchestrator
from services.input.orchestrator import input_orchestrator
from services.musical_audio import musical_audio_service
from services.voice import voice_service


class CapturingRealtimeHub:
    def __init__(self):
        self.messages = []

    def publish_from_thread(self, message):
        self.messages.append(message)
        future = Future()
        future.set_result(None)
        return future


class StaticInteractionConfigRepository:
    def __init__(self, config: InputActionConfig):
        self.config = config
        self.profile = CommandProfile(
            input_action_config=config,
            modality_settings={
                "gesture": CommandModalitySettings(enabled=True),
                "voice": CommandModalitySettings(enabled=True),
                "musical_audio": CommandModalitySettings(enabled=True),
                "keyboard": CommandModalitySettings(enabled=True),
                "dev": CommandModalitySettings(enabled=True),
            },
        )

    def get_input_action_config(self):
        return self.config

    def get_active_command_profile(self):
        return self.profile


def test_runtime_singletons_share_the_same_input_orchestrator_instance():
    assert gesture_service.input_orchestrator is input_orchestrator
    assert voice_service.input_orchestrator is input_orchestrator
    assert musical_audio_service.input_orchestrator is input_orchestrator


@pytest.fixture
def override_input_orchestrator_dependency():
    hub = CapturingRealtimeHub()
    repository = StaticInteractionConfigRepository(
        InputActionConfig(
            mappings=[
                InputActionMapping(input_source="gesture", raw_input="circle", action="toggle_shop"),
                InputActionMapping(input_source="voice", raw_input="voice.open_shop", action="open_shop"),
                InputActionMapping(
                    input_source="voice",
                    raw_input="voice.focus_grid_cell",
                    action="focus_grid_cell",
                    action_args={"mode": "grid"},
                ),
            ],
            global_cooldown_seconds=0.0,
            repeat_same_action_window_seconds=0.0,
        )
    )
    orchestrator = InputOrchestrator(
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    async def _override_input_orchestrator():
        return orchestrator

    app.dependency_overrides[get_input_orchestrator] = _override_input_orchestrator
    yield orchestrator, hub
    app.dependency_overrides.pop(get_input_orchestrator, None)


def test_input_orchestrator_blocks_lower_priority_action_inside_global_cooldown():
    hub = CapturingRealtimeHub()
    repository = StaticInteractionConfigRepository(
        InputActionConfig(
            mappings=[
                InputActionMapping(input_source="voice", raw_input="voice.shop_auf", action="toggle_shop"),
                InputActionMapping(input_source="gesture", raw_input="swipe_left", action="move_focus_left"),
            ],
            global_cooldown_seconds=30.0,
            repeat_same_action_window_seconds=0.0,
            source_priorities={"voice": 100, "musical_audio": 90, "gesture": 80, "keyboard": 70, "dev": 100},
        )
    )
    orchestrator = InputOrchestrator(
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    orchestrator.reload_config()

    assert orchestrator.publish_ui_action_requested(
        input_source="voice",
        raw_input="voice.shop_auf",
        timestamp=datetime.now(timezone.utc),
    ) is True
    assert orchestrator.publish_ui_action_requested(
        input_source="gesture",
        raw_input="swipe_left",
        timestamp=datetime.now(timezone.utc),
    ) is False
    assert [message["eventType"] for message in hub.messages] == [
        "CommandMatchEvaluated",
        "UIActionRequested",
        "CommandMatchEvaluated",
    ]
    assert hub.messages[0]["payload"]["outcome"] == "accepted"
    assert hub.messages[1]["payload"]["action"] == "toggle_shop"
    assert hub.messages[2]["payload"]["outcome"] == "suppressed"
    assert hub.messages[2]["payload"]["reason"] == "global_cooldown"


def test_input_orchestrator_allows_higher_priority_action_inside_global_cooldown():
    hub = CapturingRealtimeHub()
    repository = StaticInteractionConfigRepository(
        InputActionConfig(
            mappings=[
                InputActionMapping(input_source="gesture", raw_input="swipe_left", action="move_focus_left"),
                InputActionMapping(input_source="voice", raw_input="voice.shop_auf", action="toggle_shop"),
            ],
            global_cooldown_seconds=30.0,
            repeat_same_action_window_seconds=0.0,
            source_priorities={"voice": 100, "musical_audio": 90, "gesture": 80, "keyboard": 70, "dev": 100},
        )
    )
    orchestrator = InputOrchestrator(
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    orchestrator.reload_config()

    assert orchestrator.publish_ui_action_requested(
        input_source="gesture",
        raw_input="swipe_left",
        timestamp=datetime.now(timezone.utc),
    ) is True
    assert orchestrator.publish_ui_action_requested(
        input_source="voice",
        raw_input="voice.shop_auf",
        timestamp=datetime.now(timezone.utc),
    ) is True
    assert [message["eventType"] for message in hub.messages] == [
        "CommandMatchEvaluated",
        "UIActionRequested",
        "CommandMatchEvaluated",
        "UIActionRequested",
    ]
    assert [message["payload"]["action"] for message in hub.messages if message["eventType"] == "UIActionRequested"] == [
        "move_focus_left",
        "toggle_shop",
    ]


def test_input_orchestrator_blocks_disabled_modality_from_active_command_profile():
    hub = CapturingRealtimeHub()
    repository = StaticInteractionConfigRepository(
        InputActionConfig(
            mappings=[
                InputActionMapping(
                    input_source="musical_audio",
                    raw_input="melody.focus_mode",
                    action="toggle_shop",
                )
            ]
        )
    )
    repository.profile = repository.profile.model_copy(
        update={
            "modality_settings": {
                **repository.profile.modality_settings,
                "musical_audio": CommandModalitySettings(enabled=False),
            }
        }
    )
    orchestrator = InputOrchestrator(
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    orchestrator.reload_config()

    assert orchestrator.publish_ui_action_requested(
        input_source="musical_audio",
        raw_input="melody.focus_mode",
        timestamp=datetime.now(timezone.utc),
    ) is False
    assert hub.messages == [
        {
            "eventType": "CommandMatchEvaluated",
            "payload": {
                "input_source": "musical_audio",
                "raw_input": "melody.focus_mode",
                "timestamp": hub.messages[0]["payload"]["timestamp"] if hub.messages else None,
                "outcome": "disabled",
                "action": None,
                "reason": "modality_disabled",
                "action_args": {},
                "metadata": {},
            },
        }
    ]


def test_input_orchestrator_emits_unmapped_decision_for_unknown_raw_input():
    hub = CapturingRealtimeHub()
    repository = StaticInteractionConfigRepository(InputActionConfig(mappings=[]))
    orchestrator = InputOrchestrator(
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    orchestrator.reload_config()

    assert orchestrator.publish_ui_action_requested(
        input_source="voice",
        raw_input="voice.unknown",
        timestamp=datetime.now(timezone.utc),
    ) is False
    assert hub.messages[0]["eventType"] == "CommandMatchEvaluated"
    assert hub.messages[0]["payload"]["outcome"] == "unmapped"
    assert hub.messages[0]["payload"]["reason"] == "no_mapping"


def test_input_orchestrator_merges_structured_action_arguments_into_ui_action_payload():
    hub = CapturingRealtimeHub()
    repository = StaticInteractionConfigRepository(
        InputActionConfig(
            mappings=[
                InputActionMapping(
                    input_source="voice",
                    raw_input="voice.feld",
                    action="focus_grid_cell",
                    action_args={"cell_index": 3, "mode": "grid"},
                )
            ]
        )
    )
    orchestrator = InputOrchestrator(
        realtime=hub,
        config_repository_factory=lambda: repository,
    )

    orchestrator.reload_config()

    assert orchestrator.publish_ui_action_requested(
        input_source="voice",
        raw_input="voice.feld",
        timestamp=datetime.now(timezone.utc),
        action_args={"cell_index": 4},
        metadata={"transcript": "feld vier"},
    ) is True

    command_match_payload = hub.messages[0]["payload"]
    ui_action_payload = hub.messages[1]["payload"]

    assert command_match_payload["action"] == "focus_grid_cell"
    assert command_match_payload["action_args"] == {"cell_index": 4, "mode": "grid"}
    assert ui_action_payload["action"] == "focus_grid_cell"
    assert ui_action_payload["action_args"] == {"cell_index": 4, "mode": "grid"}
    assert ui_action_payload["metadata"] == {"transcript": "feld vier"}


@pytest.mark.asyncio
async def test_dev_simulate_input_endpoint_publishes_backend_events(client, override_input_orchestrator_dependency):
    _, hub = override_input_orchestrator_dependency

    response = await client.post(
        "/api/v1/system/dev/simulate-input",
        json={
            "input_source": "gesture",
            "raw_input": "circle",
            "metadata": {"simulated_by": "terminal"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["emitted_events"] == ["RawInputDetected", "CommandMatchEvaluated", "UIActionRequested"]
    assert [message["eventType"] for message in hub.messages] == [
        "RawInputDetected",
        "CommandMatchEvaluated",
        "UIActionRequested",
    ]
    assert hub.messages[2]["payload"]["action"] == "toggle_shop"
    assert hub.messages[2]["payload"]["metadata"] == {"simulated_by": "terminal"}


@pytest.mark.asyncio
async def test_dev_simulate_input_endpoint_reports_unmapped_inputs(client, override_input_orchestrator_dependency):
    _, hub = override_input_orchestrator_dependency

    response = await client.post(
        "/api/v1/system/dev/simulate-input",
        json={
            "input_source": "voice",
            "raw_input": "voice.unknown",
            "action_args": {"cell_index": 4},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["emitted_events"] == ["RawInputDetected", "CommandMatchEvaluated"]
    assert [message["eventType"] for message in hub.messages] == [
        "RawInputDetected",
        "CommandMatchEvaluated",
    ]
    assert hub.messages[1]["payload"]["outcome"] == "unmapped"
    assert hub.messages[1]["payload"]["reason"] == "no_mapping"