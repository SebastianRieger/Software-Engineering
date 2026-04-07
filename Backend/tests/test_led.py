import pytest


@pytest.mark.asyncio
async def test_set_led_color(client):
    response = await client.post(
        "/api/v1/led/color",
        json={"red": 1.0, "green": 0.5, "blue": 0.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "LED color set"
    assert data["red"] == 1.0
    assert data["green"] == 0.5
    assert data["blue"] == 0.0



@pytest.mark.asyncio
async def test_set_led_brightness(client):
    response = await client.post("/api/v1/led/brightness", json={"brightness": 0.75})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "LED brightness set"
    assert data["brightness"] == 0.75



@pytest.mark.asyncio
async def test_invalid_color_values(client):
    response = await client.post(
        "/api/v1/led/color",
        json={"red": 2.0, "green": -1.0, "blue": 0.5},
    )
    assert response.status_code == 422
