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
            signals=[
                VoiceSignalDefinition(raw_input="voice.open_shop", phrases=["shop auf"])
            ],
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


def _make_service_with_defaults() -> tuple[CapturingRealtimeHub, VoiceService]:
    """Creates a VoiceService using the actual default config from settings."""
    hub = CapturingRealtimeHub()
    service = VoiceService(
        realtime=hub,
        config_repository_factory=lambda: StaticVoiceConfigRepository(
            voice_config=VoiceConfig(),
            input_action_config=InputActionConfig(),
        ),
    )
    service.reload_config()
    return hub, service


# ---------------------------------------------------------------------------
# HTTP API tests
# ---------------------------------------------------------------------------


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
async def test_start_voice_returns_clear_status_error(
    client, override_voice_dependency
):
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


# ---------------------------------------------------------------------------
# Event-pipeline tests (existing)
# ---------------------------------------------------------------------------


def test_voice_service_publishes_raw_input_and_ui_action_for_mapped_command():
    hub = CapturingRealtimeHub()
    service = VoiceService(
        realtime=hub,
        config_repository_factory=lambda: StaticVoiceConfigRepository(),
    )

    service.reload_config()
    service._handle_transcript("shop auf", partial=False)

    event_types = [message["eventType"] for message in hub.messages]
    assert event_types == [
        "VoiceCommandDetected",
        "RawInputDetected",
        "CommandMatchEvaluated",
        "UIActionRequested",
    ]
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
    assert hub.messages[2]["payload"]["action_args"] == {
        "cell_index": 4,
        "mode": "grid",
    }
    assert hub.messages[3]["payload"]["action"] == "focus_grid_cell"
    assert hub.messages[3]["payload"]["action_args"] == {
        "cell_index": 4,
        "mode": "grid",
    }


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
    assert hub.messages[2]["payload"]["action_args"] == {
        "cell_index": 3,
        "mode": "grid",
    }
    assert hub.messages[3]["payload"]["action"] == "resize_expand"
    assert hub.messages[3]["payload"]["action_args"] == {
        "cell_index": 3,
        "mode": "grid",
    }


# ---------------------------------------------------------------------------
# Default config sanity
# ---------------------------------------------------------------------------


def test_default_voice_commands_is_empty():
    from core.config import settings

    assert settings.VOICE_COMMANDS == []


def test_default_voice_partial_results_disabled():
    from core.config import settings

    assert settings.VOICE_PARTIAL_RESULTS_ENABLED is False


# ---------------------------------------------------------------------------
# Parametrized: all canonical signal phrases trigger the correct UIAction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase,expected_raw_input,expected_action",
    [
        ("links", "voice.move_focus_left", "move_focus_left"),
        ("nach links", "voice.move_focus_left", "move_focus_left"),
        ("rechts", "voice.move_focus_right", "move_focus_right"),
        ("nach rechts", "voice.move_focus_right", "move_focus_right"),
        ("oben", "voice.move_focus_up", "move_focus_up"),
        ("nach oben", "voice.move_focus_up", "move_focus_up"),
        ("hoch", "voice.move_focus_up", "move_focus_up"),
        ("unten", "voice.move_focus_down", "move_focus_down"),
        ("nach unten", "voice.move_focus_down", "move_focus_down"),
        ("runter", "voice.move_focus_down", "move_focus_down"),
        ("shop auf", "voice.open_shop", "open_shop"),
        ("shop oeffnen", "voice.open_shop", "open_shop"),
        ("shop zu", "voice.close_shop", "close_shop"),
        ("shop schliessen", "voice.close_shop", "close_shop"),
        ("bestaetigen", "voice.confirm_selection", "confirm_selection"),
        ("okay", "voice.confirm_selection", "confirm_selection"),
        ("abbrechen", "voice.cancel_selection", "cancel_selection"),
        ("zurueck", "voice.cancel_selection", "cancel_selection"),
        ("bearbeiten", "voice.enter_arrange_mode", "enter_arrange_mode"),
        ("anordnen", "voice.enter_arrange_mode", "enter_arrange_mode"),
        ("beenden", "voice.exit_arrange_mode", "exit_arrange_mode"),
        ("anordnung beenden", "voice.exit_arrange_mode", "exit_arrange_mode"),
        ("groesser", "voice.resize_expand", "resize_expand"),
        ("vergroessern", "voice.resize_expand", "resize_expand"),
        ("kleiner", "voice.resize_shrink", "resize_shrink"),
        ("verkleinern", "voice.resize_shrink", "resize_shrink"),
    ],
)
def test_signal_phrase_triggers_correct_ui_action(
    phrase: str, expected_raw_input: str, expected_action: str
) -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript(phrase, partial=False)

    event_types = [m["eventType"] for m in hub.messages]
    assert (
        "VoiceCommandDetected" in event_types
    ), f"No VoiceCommandDetected for '{phrase}'"
    assert "UIActionRequested" in event_types, f"No UIActionRequested for '{phrase}'"

    voice_event = next(
        m for m in hub.messages if m["eventType"] == "VoiceCommandDetected"
    )
    assert voice_event["payload"]["raw_input"] == expected_raw_input, (
        f"phrase='{phrase}': expected raw_input='{expected_raw_input}', "
        f"got '{voice_event['payload']['raw_input']}'"
    )

    ui_event = next(m for m in hub.messages if m["eventType"] == "UIActionRequested")
    assert ui_event["payload"]["action"] == expected_action, (
        f"phrase='{phrase}': expected action='{expected_action}', "
        f"got '{ui_event['payload']['action']}'"
    )


# ---------------------------------------------------------------------------
# Umlaut normalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "umlaut_phrase,expected_raw_input",
    [
        ("größer", "voice.resize_expand"),
        ("Größer", "voice.resize_expand"),
        ("BEENDEN", "voice.exit_arrange_mode"),
        ("Bestätigen", "voice.confirm_selection"),
        ("Zurück", "voice.cancel_selection"),
    ],
)
def test_umlaut_normalization_triggers_correct_signal(
    umlaut_phrase: str, expected_raw_input: str
) -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript(umlaut_phrase, partial=False)

    voice_events = [m for m in hub.messages if m["eventType"] == "VoiceCommandDetected"]
    assert voice_events, f"No VoiceCommandDetected for '{umlaut_phrase}'"
    assert voice_events[0]["payload"]["raw_input"] == expected_raw_input


# ---------------------------------------------------------------------------
# Grid-cell focus
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase,expected_cell_index",
    [
        ("feld drei", 3),
        ("feld 5", 5),
        ("zelle 1", 1),
        ("zelle 12", 12),
        ("zwei", 2),
    ],
)
def test_grid_cell_focus(phrase: str, expected_cell_index: int) -> None:
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
    service._handle_transcript(phrase, partial=False)

    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, f"No UIActionRequested for '{phrase}'"
    assert ui_events[0]["payload"]["action"] == "focus_grid_cell"
    assert ui_events[0]["payload"]["action_args"]["cell_index"] == expected_cell_index


# ---------------------------------------------------------------------------
# Targeted resize with cell reference
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase,expected_action,expected_cell_index",
    [
        ("feld drei groesser", "resize_expand", 3),
        ("feld 5 kleiner", "resize_shrink", 5),
        ("zelle 2 vergroessern", "resize_expand", 2),
    ],
)
def test_targeted_resize_with_cell_reference(
    phrase: str, expected_action: str, expected_cell_index: int
) -> None:
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
                    ),
                    InputActionMapping(
                        input_source="voice",
                        raw_input="voice.resize_shrink",
                        action="resize_shrink",
                    ),
                ]
            ),
        ),
    )
    service.reload_config()
    service._handle_transcript(phrase, partial=False)

    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, f"No UIActionRequested for '{phrase}'"
    assert ui_events[0]["payload"]["action"] == expected_action
    assert ui_events[0]["payload"]["action_args"]["cell_index"] == expected_cell_index


# ---------------------------------------------------------------------------
# Cooldown prevents double-fire
# ---------------------------------------------------------------------------


def test_command_cooldown_prevents_double_fire() -> None:
    hub, service = _make_service_with_defaults()

    service._handle_transcript("links", partial=False)
    service._handle_transcript("links", partial=False)

    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert len(ui_events) == 1, "Cooldown should suppress second identical command"


# ---------------------------------------------------------------------------
# Unknown / removed phrases produce no UIActionRequested
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unknown_phrase",
    [
        "licht an",
        "licht aus",
        "naechstes widget",
        "vorheriges widget",
        "shop",
        "laden",
        "auswahl",
        "platzieren",
        "fertig",
        "hello",
    ],
)
def test_unknown_phrases_produce_no_ui_action(unknown_phrase: str) -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript(unknown_phrase, partial=False)

    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert not ui_events, (
        f"Phrase '{unknown_phrase}' should not trigger UIActionRequested, "
        f"but got: {ui_events}"
    )


# ---------------------------------------------------------------------------
# Regression: exit_arrange_mode signal must never toggle edit mode back on
# ---------------------------------------------------------------------------


def test_exit_arrange_mode_signal_maps_to_exit_arrange_mode() -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript("beenden", partial=False)

    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, "Expected UIActionRequested for 'beenden'"
    assert (
        ui_events[0]["payload"]["action"] == "exit_arrange_mode"
    ), f"Expected 'exit_arrange_mode', got '{ui_events[0]['payload']['action']}'"


def test_anordnung_beenden_maps_to_exit_arrange_mode() -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript("anordnung beenden", partial=False)

    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, "Expected UIActionRequested for 'anordnung beenden'"
    assert ui_events[0]["payload"]["action"] == "exit_arrange_mode"


# ---------------------------------------------------------------------------
# Resampling helper
# ---------------------------------------------------------------------------


def test_resample_audio_reduces_chunk_size_3to1() -> None:
    # 48000 Hz → 16000 Hz is a 3:1 ratio; output should be ~1/3 of input samples
    chunk = bytes(4800 * 2)  # 4800 int16 samples at 48000 Hz
    result = VoiceService._resample_audio(chunk, 48000, 16000)
    # scipy polyphase: exact 1/3 for integer ratio; allow ±4 samples for filter padding
    assert abs(len(result) // 2 - 1600) <= 4


def test_resample_audio_noop_when_rates_equal() -> None:
    chunk = bytes(100)
    result = VoiceService._resample_audio(chunk, 16000, 16000)
    assert result is chunk


def test_resample_audio_output_is_plausible_int16() -> None:
    import numpy as np

    # Sine wave at 48000 Hz, resample to 16000 Hz; verify output is valid int16
    t = np.linspace(0, 0.1, 4800, endpoint=False)
    sine = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    chunk = sine.tobytes()
    result = VoiceService._resample_audio(chunk, 48000, 16000)
    output = np.frombuffer(result, dtype=np.int16)
    assert abs(len(output) - 1600) <= 4
    assert output.max() <= 32767 and output.min() >= -32768


# ---------------------------------------------------------------------------
# _probe_device_sample_rate
# ---------------------------------------------------------------------------


def test_probe_device_sample_rate_returns_native(monkeypatch) -> None:
    import sounddevice as sd

    monkeypatch.setattr(
        sd, "query_devices", lambda idx, kind: {"default_samplerate": 48000.0}
    )
    _, service = _make_service_with_defaults()
    assert service._probe_device_sample_rate(0) == 48000


def test_probe_device_sample_rate_fallback_on_exception(monkeypatch) -> None:
    import sounddevice as sd

    def raise_exc(idx, kind):
        raise RuntimeError("no device")

    monkeypatch.setattr(sd, "query_devices", raise_exc)
    _, service = _make_service_with_defaults()
    assert service._probe_device_sample_rate(0) == 48000


def test_probe_device_sample_rate_fallback_when_zero(monkeypatch) -> None:
    import sounddevice as sd

    monkeypatch.setattr(
        sd, "query_devices", lambda idx, kind: {"default_samplerate": 0}
    )
    _, service = _make_service_with_defaults()
    assert service._probe_device_sample_rate(0) == 48000


# ---------------------------------------------------------------------------
# _build_vosk_vocabulary
# ---------------------------------------------------------------------------


def test_build_vosk_vocabulary_contains_unk_sentinel() -> None:
    import json

    _, service = _make_service_with_defaults()
    vocab = json.loads(service._build_vosk_vocabulary(VoiceConfig()))
    assert "[unk]" in vocab


def test_build_vosk_vocabulary_contains_signal_phrase_words() -> None:
    import json

    _, service = _make_service_with_defaults()
    vocab = json.loads(service._build_vosk_vocabulary(VoiceConfig()))
    assert "links" in vocab
    assert "rechts" in vocab
    assert "shop" in vocab


def test_build_vosk_vocabulary_contains_german_umlaut_forms() -> None:
    import json

    _, service = _make_service_with_defaults()
    vocab = json.loads(service._build_vosk_vocabulary(VoiceConfig()))
    # "groesser" → "größer"
    assert "größer" in vocab
    # "schliessen" → "schließen"
    assert "schließen" in vocab
    # "bestaetigen" → "bestätigen"
    assert "bestätigen" in vocab
    # "zurueck" → "zurück"
    assert "zurück" in vocab


def test_build_vosk_vocabulary_contains_grid_words() -> None:
    import json

    _, service = _make_service_with_defaults()
    vocab = json.loads(service._build_vosk_vocabulary(VoiceConfig()))
    assert "feld" in vocab
    assert "zelle" in vocab
    assert "drei" in vocab
    assert "eins" in vocab


def test_build_vosk_vocabulary_is_valid_json_list() -> None:
    import json

    _, service = _make_service_with_defaults()
    raw = service._build_vosk_vocabulary(VoiceConfig())
    vocab = json.loads(raw)
    assert isinstance(vocab, list)
    assert len(vocab) > 20


# ---------------------------------------------------------------------------
# _strip_unk
# ---------------------------------------------------------------------------


def test_strip_unk_removes_leading_token() -> None:
    assert VoiceService._strip_unk("unk links") == "links"


def test_strip_unk_removes_inline_token() -> None:
    assert VoiceService._strip_unk("nach unk links") == "nach links"


def test_strip_unk_all_unk_returns_empty() -> None:
    assert VoiceService._strip_unk("unk unk unk") == ""


def test_strip_unk_no_unk_passes_through() -> None:
    assert VoiceService._strip_unk("links") == "links"


def test_strip_unk_empty_string() -> None:
    assert VoiceService._strip_unk("") == ""


# ---------------------------------------------------------------------------
# Containment matching (Bug 2 fix)
# ---------------------------------------------------------------------------


def test_signal_exact_match_still_works() -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript("links", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, "Expected UIActionRequested for 'links'"
    assert ui_events[0]["payload"]["action"] == "move_focus_left"


def test_signal_matches_with_leading_unk_token() -> None:
    hub, service = _make_service_with_defaults()
    # "[unk] links" is what Vosk would produce when noise precedes the word
    service._handle_transcript("unk links", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, "Expected UIActionRequested for 'unk links'"
    assert ui_events[0]["payload"]["action"] == "move_focus_left"


def test_multi_word_signal_matches_with_unk_noise() -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript("unk shop auf", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, "Expected UIActionRequested for 'unk shop auf'"
    assert ui_events[0]["payload"]["action"] == "open_shop"


def test_longer_phrase_preferred_over_shorter_contained_phrase() -> None:
    # Ensure "nach links" matches rather than just "links"
    hub, service = _make_service_with_defaults()
    service._handle_transcript("nach links", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert ui_events, "Expected UIActionRequested for 'nach links'"
    assert ui_events[0]["payload"]["action"] == "move_focus_left"


def test_pure_unk_transcript_produces_no_command() -> None:
    hub, service = _make_service_with_defaults()
    service._handle_transcript("unk unk unk", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert not ui_events, "Noise-only transcript must not produce commands"


def test_containment_blocked_when_transcript_too_long() -> None:
    # "links" (1-word phrase) inside a 5-word transcript: 5 > 1*3=3 → must not match
    hub, service = _make_service_with_defaults()
    service._handle_transcript("fälle bag celle sex links", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert not ui_events, "Short phrase must not match inside a long noise transcript"


def test_single_word_phrase_not_contained_in_longer_transcript() -> None:
    # "links" (1 word) inside "ja links" (2 words): must NOT match via containment.
    # Single-word phrases require exact match to avoid false positives mid-sentence.
    hub, service = _make_service_with_defaults()
    service._handle_transcript("ja links", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert not ui_events, "1-word phrase must not match via containment"


def test_okay_does_not_trigger_inside_sentence() -> None:
    # "das ist okay" must not trigger confirm_selection
    hub, service = _make_service_with_defaults()
    service._handle_transcript("das ist okay", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert not ui_events, "'okay' inside a sentence must not trigger confirm_selection"


def test_beenden_does_not_trigger_inside_sentence() -> None:
    # "sitzung beenden" must not trigger exit_arrange_mode
    hub, service = _make_service_with_defaults()
    service._handle_transcript("sitzung beenden", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert (
        not ui_events
    ), "'beenden' inside a sentence must not trigger toggle_edit_mode"


def test_multi_word_phrase_containment_still_works() -> None:
    # "shop auf" (2 words) inside "bitte shop auf" (3 words): 3 ≤ 2*3=6 → must match
    hub, service = _make_service_with_defaults()
    service._handle_transcript("bitte shop auf", partial=False)
    ui_events = [m for m in hub.messages if m["eventType"] == "UIActionRequested"]
    assert (
        ui_events
    ), "2-word phrase must still match via containment in a 3-word transcript"
    assert ui_events[0]["payload"]["action"] == "open_shop"


# ---------------------------------------------------------------------------
# list_input_devices ALSA filter (Bug 3 fix)
# ---------------------------------------------------------------------------


def test_list_input_devices_filters_alsa_hw_entries(monkeypatch) -> None:
    import sounddevice as sd

    fake_devices = [
        {"name": "default", "max_input_channels": 1, "default_samplerate": 44100},
        {
            "name": "HD-Audio Generic: Mic (hw:0,0)",
            "max_input_channels": 2,
            "default_samplerate": 44100,
        },
        {
            "name": "PC-LM1E Camera Analog Stereo",
            "max_input_channels": 1,
            "default_samplerate": 48000,
        },
        {
            "name": "Webcam Audio (hw:1,0)",
            "max_input_channels": 1,
            "default_samplerate": 48000,
        },
    ]

    class FakeDefault:
        device = (0, 0)

    monkeypatch.setattr(sd, "query_devices", lambda: fake_devices)
    monkeypatch.setattr(sd, "default", FakeDefault())

    _, service = _make_service_with_defaults()
    result = service.list_input_devices()

    names = [d["name"] for d in result]
    assert "default" in names
    assert "PC-LM1E Camera Analog Stereo" in names
    assert (
        "HD-Audio Generic: Mic (hw:0,0)" not in names
    ), "Raw ALSA entry must be filtered"
    assert "Webcam Audio (hw:1,0)" not in names, "Raw ALSA entry must be filtered"
