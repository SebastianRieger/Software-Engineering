from datetime import datetime, timezone

from concurrent.futures import Future

from schemas.commands import CommandModalitySettings, CommandProfile
from schemas.interactions import InputActionConfig, InputActionMapping
from services.interactions import InputOrchestrator


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