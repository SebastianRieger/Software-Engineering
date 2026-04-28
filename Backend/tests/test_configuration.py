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


@pytest.mark.asyncio
async def test_get_default_input_action_config(client):
    response = await client.get("/api/v1/config/gesture-actions")
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

    save_response = await client.put("/api/v1/config/gesture-actions", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["updated_at"] is not None
    assert saved["config"]["mappings"][1]["input_source"] == "voice"

    load_response = await client.get("/api/v1/config/gesture-actions")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["config"]["mappings"][0]["raw_input"] == "circle"
    assert loaded["config"]["mappings"][1]["metadata"]["phrase"] == "shop auf"
