import pytest


pytestmark = pytest.mark.usefixtures("override_config_dependency")


@pytest.mark.asyncio
async def test_get_default_layout(client):
    response = await client.get("/api/v1/config/layout")
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] == "default"
    assert data["config"]["widgets"] == []


@pytest.mark.asyncio
async def test_save_and_reload_layout(client):
    payload = {
        "version": 1,
        "widgets": [
            {
                "widget_id": "weather-main",
                "widget_type": "weather",
                "cell_id": 1,
                "title": "Wetter",
                "settings": {"units": "metric"},
            }
        ],
    }

    save_response = await client.put("/api/v1/config/layout", json=payload)
    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["config"]["widgets"][0]["widget_id"] == "weather-main"
    assert saved["config"]["updated_at"] is not None

    load_response = await client.get("/api/v1/config/layout")
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["config"]["widgets"][0]["widget_type"] == "weather"


@pytest.mark.asyncio
async def test_layout_profiles_are_isolated(client):
    payload = {
        "version": 1,
        "widgets": [
            {
                "widget_id": "clock-main",
                "widget_type": "clock",
                "cell_id": 2,
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
