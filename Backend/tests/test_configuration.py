import pytest


pytestmark = pytest.mark.usefixtures("override_config_dependency")


@pytest.mark.asyncio
async def test_get_default_layout(client):
    response = await client.get("/api/v1/config/layout")
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] == "default"
    assert data["config"]["widgets"] == []
    assert data["config"]["version"] == 2


@pytest.mark.asyncio
async def test_save_and_reload_layout(client):
    payload = {
        "version": 2,
        "widgets": [
            {
                "widget_id": "weather-main",
                "widget_type": "weather",
                "row": 1,
                "col": 1,
                "row_span": 2,
                "col_span": 2,
                "title": "Wetter",
                "settings": {"units": "metric"},
            }
        ],
    }

    save_response = await client.put("/api/v1/config/layout", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["widgets"][0]["widget_id"] == "weather-main"
    assert saved["config"]["widgets"][0]["cell_id"] == 1
    assert saved["config"]["widgets"][0]["row_span"] == 2
    assert saved["config"]["updated_at"] is not None

    load_response = await client.get("/api/v1/config/layout")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["config"]["widgets"][0]["widget_type"] == "weather"


@pytest.mark.asyncio
async def test_layout_accepts_legacy_cell_id_and_migrates_to_position(client):
    payload = {
        "version": 1,
        "widgets": [
            {
                "widget_id": "legacy-clock",
                "widget_type": "clock",
                "cell_id": 6,
                "title": "Legacy",
                "settings": {},
            }
        ],
    }

    save_response = await client.put("/api/v1/config/layout", json=payload)
    assert save_response.status_code == 200
    saved_widget = save_response.json()["config"]["widgets"][0]
    assert saved_widget["row"] == 2
    assert saved_widget["col"] == 2
    assert saved_widget["row_span"] == 1
    assert saved_widget["col_span"] == 1


@pytest.mark.asyncio
async def test_layout_profiles_are_isolated(client):
    payload = {
        "version": 2,
        "widgets": [
            {
                "widget_id": "clock-main",
                "widget_type": "clock",
                "row": 1,
                "col": 2,
                "title": "Uhr",
                "settings": {},
            }
        ],
    }

    save_response = await client.put("/api/v1/config/layout?profile=focus", json=payload)
    assert save_response.status_code == 200

    default_response = await client.get("/api/v1/config/layout")
    focus_response = await client.get("/api/v1/config/layout?profile=focus")

    assert default_response.json()["config"]["widgets"] == []
    assert focus_response.json()["config"]["widgets"][0]["widget_id"] == "clock-main"


@pytest.mark.asyncio
async def test_get_default_system_config(client):
    response = await client.get("/api/v1/config/system")
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["units"] == "metric"
    assert data["config"]["latitude"] is not None
    assert data["config"]["longitude"] is not None


@pytest.mark.asyncio
async def test_save_and_reload_system_config(client):
    payload = {
        "location_name": "Karlsruhe",
        "latitude": 49.0069,
        "longitude": 8.4037,
        "units": "metric",
        "theme": "dark",
        "weather_refresh_seconds": 300,
    }

    save_response = await client.put("/api/v1/config/system", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["location_name"] == "Karlsruhe"
    assert saved["config"]["updated_at"] is not None

    load_response = await client.get("/api/v1/config/system")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["config"]["latitude"] == payload["latitude"]
    assert loaded["config"]["weather_refresh_seconds"] == 300


@pytest.mark.asyncio
async def test_get_default_gesture_config(client):
    response = await client.get("/api/v1/config/gestures")
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["smoothing_alpha"] == 0.6
    assert data["config"]["min_detection_points"] == 6
    assert data["config"]["hand_size_reference"] > 0


@pytest.mark.asyncio
async def test_save_and_reload_gesture_config(client):
    payload = {
        "smoothing_alpha": 0.75,
        "max_trajectory_points": 96,
        "cooldown_seconds": 1.5,
        "swipe_threshold": 0.18,
        "down_threshold": 0.16,
        "swipe_min_span": 0.08,
        "circle_sweep_min": 4.8,
        "circle_radius_cv_max": 0.45,
        "circle_min_radius": 0.02,
        "min_detection_points": 8,
        "min_confidence": 0.7,
        "hand_size_reference": 0.15,
        "hand_size_scale_min": 0.7,
        "hand_size_scale_max": 1.6,
    }

    save_response = await client.put("/api/v1/config/gestures", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["smoothing_alpha"] == payload["smoothing_alpha"]
    assert saved["config"]["updated_at"] is not None

    load_response = await client.get("/api/v1/config/gestures")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["config"]["cooldown_seconds"] == payload["cooldown_seconds"]
    assert loaded["config"]["circle_min_radius"] == payload["circle_min_radius"]
    assert loaded["config"]["min_confidence"] == payload["min_confidence"]
    assert loaded["config"]["hand_size_reference"] == payload["hand_size_reference"]


@pytest.mark.asyncio
async def test_get_default_voice_config(client):
    response = await client.get("/api/v1/config/voice")
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["sample_rate"] == 16000
    assert data["config"]["commands"]


@pytest.mark.asyncio
async def test_save_and_reload_voice_config(client):
    payload = {
        "enabled": True,
        "device_index": -1,
        "sample_rate": 16000,
        "block_size": 1024,
        "queue_max_chunks": 8,
        "energy_threshold": 150.0,
        "command_cooldown_seconds": 0.8,
        "partial_results_enabled": False,
        "commands": ["licht an", "licht aus", "spiegel an"],
    }

    save_response = await client.put("/api/v1/config/voice", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["block_size"] == payload["block_size"]
    assert saved["config"]["updated_at"] is not None

    load_response = await client.get("/api/v1/config/voice")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["config"]["queue_max_chunks"] == payload["queue_max_chunks"]
    assert loaded["config"]["partial_results_enabled"] is False
    assert loaded["config"]["commands"] == payload["commands"]

    profiles_response = await client.get("/api/v1/config/command-profiles")
    assert profiles_response.status_code == 200
    profile = profiles_response.json()["config"]["profiles"][0]
    assert profile["device_preferences"]["voice_device_index"] == payload["device_index"]
    assert profile["modality_settings"]["voice"]["enabled"] is True


@pytest.mark.asyncio
async def test_get_default_input_action_config(client):
    response = await client.get("/api/v1/config/input-actions")
    assert response.status_code == 200
    data = response.json()
    assert any(
        mapping["raw_input"] == "circle" and mapping["action"] == "toggle_shop"
        for mapping in data["config"]["mappings"]
    )


@pytest.mark.asyncio
async def test_save_and_reload_input_action_config(client):
    payload = {
        "mappings": [
            {
                "input_source": "gesture",
                "raw_input": "circle",
                "action": "toggle_shop",
                "enabled": True,
                "metadata": {"demo": True},
            },
            {
                "input_source": "voice",
                "raw_input": "voice.open_shop",
                "action": "toggle_shop",
                "enabled": True,
                "metadata": {"phrase": "shop auf"},
            },
        ]
    }

    save_response = await client.put("/api/v1/config/input-actions", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["updated_at"] is not None
    assert saved["config"]["mappings"][1]["input_source"] == "voice"

    load_response = await client.get("/api/v1/config/input-actions")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["config"]["mappings"][0]["raw_input"] == "circle"
    assert loaded["config"]["mappings"][1]["metadata"]["phrase"] == "shop auf"


@pytest.mark.asyncio
async def test_get_default_command_profiles_config(client):
    response = await client.get("/api/v1/config/command-profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["active_profile_id"] == "default"
    assert data["config"]["profiles"][0]["profile_id"] == "default"
    assert data["config"]["profiles"][0]["input_action_config"]["mappings"]


@pytest.mark.asyncio
async def test_save_command_profiles_config_updates_legacy_input_actions(client):
    payload = {
        "active_profile_id": "focus",
        "profiles": [
            {
                "profile_id": "focus",
                "display_name": "Focus",
                "description": "Only curated command inputs",
                "input_action_config": {
                    "mappings": [
                        {
                            "input_source": "musical_audio",
                            "raw_input": "melody.focus_mode",
                            "action": "toggle_shop",
                            "enabled": True,
                            "metadata": {"kind": "whistle"},
                        }
                    ],
                    "global_cooldown_seconds": 0.4,
                    "repeat_same_action_window_seconds": 0.8,
                    "source_priorities": {
                        "voice": 100,
                        "musical_audio": 90,
                        "gesture": 80,
                        "keyboard": 70,
                        "dev": 100,
                    },
                },
                "modality_settings": {
                    "gesture": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                    "voice": {"enabled": False, "active_training_artifact_id": None, "metadata": {}},
                    "musical_audio": {"enabled": True, "active_training_artifact_id": "focus-a" , "metadata": {}},
                    "keyboard": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                    "dev": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                },
                "device_preferences": {
                    "gesture_camera_index": 0,
                    "voice_device_index": 2,
                    "musical_audio_device_index": 3,
                },
            }
        ],
    }

    save_response = await client.put("/api/v1/config/command-profiles", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["profiles"][0]["device_preferences"]["musical_audio_device_index"] == 3

    legacy_response = await client.get("/api/v1/config/input-actions")
    assert legacy_response.status_code == 200
    legacy = legacy_response.json()
    assert legacy["config"]["mappings"][0]["input_source"] == "musical_audio"
    assert legacy["config"]["mappings"][0]["raw_input"] == "melody.focus_mode"

    voice_response = await client.get("/api/v1/config/voice")
    assert voice_response.status_code == 200
    voice_config = voice_response.json()["config"]
    assert voice_config["enabled"] is False
    assert voice_config["device_index"] == 2

    musical_audio_response = await client.get("/api/v1/config/musical-audio")
    assert musical_audio_response.status_code == 200
    musical_audio_config = musical_audio_response.json()["config"]
    assert musical_audio_config["enabled"] is True
    assert musical_audio_config["device_index"] == 3
    assert musical_audio_config["active_artifact_id"] == "focus-a"


@pytest.mark.asyncio
async def test_save_command_profiles_config_reloads_voice_and_musical_audio_runtime(
    client,
    override_voice_dependency,
    override_musical_audio_dependency,
):
    response = await client.put(
        "/api/v1/config/command-profiles",
        json={
            "active_profile_id": "default",
            "profiles": [
                {
                    "profile_id": "default",
                    "display_name": "Default",
                    "input_action_config": {"mappings": []},
                    "modality_settings": {
                        "gesture": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                        "voice": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                        "musical_audio": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                        "keyboard": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                        "dev": {"enabled": True, "active_training_artifact_id": None, "metadata": {}},
                    },
                    "device_preferences": {
                        "gesture_camera_index": 1,
                        "voice_device_index": 2,
                        "musical_audio_device_index": 1,
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    assert override_voice_dependency.reload_count == 1
    assert override_musical_audio_dependency.reload_count == 1


@pytest.mark.asyncio
async def test_get_and_save_musical_audio_config(client):
    response = await client.get("/api/v1/config/musical-audio")
    assert response.status_code == 200
    assert response.json()["config"]["sample_rate"] == 16000

    payload = {
        "enabled": True,
        "device_index": 4,
        "sample_rate": 22050,
        "block_size": 2048,
        "queue_max_chunks": 16,
        "silence_threshold": 0.02,
        "pitch_confidence_threshold": 0.72,
        "command_cooldown_seconds": 0.9,
        "min_pattern_notes": 4,
        "max_pattern_window_seconds": 5.5,
        "active_artifact_id": "whistle-main",
    }

    save_response = await client.put("/api/v1/config/musical-audio", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["device_index"] == 4
    assert saved["config"]["updated_at"] is not None

    reload_response = await client.get("/api/v1/config/musical-audio")
    assert reload_response.status_code == 200
    loaded = reload_response.json()
    assert loaded["config"]["active_artifact_id"] == "whistle-main"


@pytest.mark.asyncio
async def test_save_list_get_and_delete_musical_audio_artifact(client):
    payload = {
        "artifact_id": "whistle-main",
        "profile_id": "default",
        "raw_input": "melody.whistle_main",
        "display_name": "Main whistle",
        "source_hint": "whistle",
        "notes": [
            {
                "relative_pitch_semitones": 0.0,
                "relative_time_seconds": 0.0,
                "duration_seconds": 0.24,
                "confidence": 0.94,
            },
            {
                "relative_pitch_semitones": 2.0,
                "relative_time_seconds": 0.33,
                "duration_seconds": 0.19,
                "confidence": 0.89,
            },
        ],
        "match_threshold": 2.4,
        "minimum_confidence": 0.61,
        "sample_count": 12,
        "enabled": True,
        "metadata": {"trained_from": "unit-test"},
    }

    save_response = await client.put("/api/v1/config/musical-audio/artifacts/whistle-main", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()["artifact"]
    assert saved["created_at"] is not None
    assert saved["updated_at"] is not None

    list_response = await client.get("/api/v1/config/musical-audio/artifacts")
    assert list_response.status_code == 200
    artifacts = list_response.json()["artifacts"]
    assert artifacts[0]["raw_input"] == "melody.whistle_main"

    get_response = await client.get("/api/v1/config/musical-audio/artifacts/whistle-main")
    assert get_response.status_code == 200
    artifact = get_response.json()["artifact"]
    assert artifact["notes"][1]["relative_pitch_semitones"] == 2.0

    delete_response = await client.delete("/api/v1/config/musical-audio/artifacts/whistle-main")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


@pytest.mark.asyncio
async def test_save_input_actions_reloads_musical_audio_runtime(client, override_musical_audio_dependency):
    response = await client.put(
        "/api/v1/config/input-actions",
        json={
            "mappings": [
                {
                    "input_source": "musical_audio",
                    "raw_input": "melody.whistle_main",
                    "action": "toggle_shop",
                    "enabled": True,
                    "metadata": {},
                }
            ]
        },
    )

    assert response.status_code == 200
    assert override_musical_audio_dependency.reload_count == 1


@pytest.mark.asyncio
async def test_save_musical_audio_artifact_reloads_runtime(client, override_musical_audio_dependency):
    payload = {
        "artifact_id": "whistle-main",
        "profile_id": "default",
        "raw_input": "melody.whistle_main",
        "display_name": "Main whistle",
        "source_hint": "whistle",
        "notes": [],
        "match_threshold": 2.0,
        "minimum_confidence": 0.6,
        "sample_count": 1,
        "enabled": True,
        "metadata": {},
    }

    save_response = await client.put("/api/v1/config/musical-audio/artifacts/whistle-main", json=payload)
    assert save_response.status_code == 200
    assert override_musical_audio_dependency.reload_count == 1

    delete_response = await client.delete("/api/v1/config/musical-audio/artifacts/whistle-main")
    assert delete_response.status_code == 200
    assert override_musical_audio_dependency.reload_count == 2


@pytest.mark.asyncio
async def test_legacy_gesture_actions_route_remains_available(client):
    response = await client.get("/api/v1/config/gesture-actions")
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["mappings"]
