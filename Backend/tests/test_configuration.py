import pytest


@pytest.mark.asyncio
async def test_get_default_layout(client, override_config_dependency):
    response = await client.get("/api/v1/config/layout")
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] == "default"
    assert data["config"]["widgets"] == []


@pytest.mark.asyncio
async def test_save_and_reload_layout(client, override_config_dependency):
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
