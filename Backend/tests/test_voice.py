import pytest


@pytest.mark.asyncio
async def test_get_voice_status(client, override_voice_dependency):
    _ = override_voice_dependency
    response = await client.get("/api/v1/voice/status")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "skeleton"
    assert data["available"] is False


@pytest.mark.asyncio
async def test_start_voice_returns_clear_status_error(client, override_voice_dependency):
    _ = override_voice_dependency
    response = await client.post("/api/v1/voice/start", json={"device_index": 0})
    assert response.status_code == 503
    assert "Mikrofonpfad" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stop_voice(client, override_voice_dependency):
    _ = override_voice_dependency
    response = await client.post("/api/v1/voice/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert data["message"] == "Voice stopped"