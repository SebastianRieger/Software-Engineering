import pytest


@pytest.mark.asyncio
async def test_get_current_weather(client, override_weather_dependency):
    response = await client.get("/api/v1/weather/current?lat=52.52&lon=13.405")
    assert response.status_code == 200
    data = response.json()
    assert data["temperature"] == 20.0
    assert data["humidity"] == 65
    assert data["condition"] == "Clear"
    assert data["location_name"] == "Berlin"
    assert data["coordinates"] == {"lat": 52.52, "lon": 13.405}
    assert data["source"] == "live"


@pytest.mark.asyncio
async def test_get_current_weather_by_city(client, override_weather_dependency):
    response = await client.get("/api/v1/weather/current?city=Stuttgart")
    assert response.status_code == 200
    data = response.json()
    assert data["location_name"] == "Stuttgart"
    assert data["coordinates"] == {"lat": 48.7758, "lon": 9.1829}
    assert data["source"] == "live"


@pytest.mark.asyncio
async def test_geocode_city(client, override_weather_dependency):
    response = await client.get("/api/v1/weather/geocode?city=Stuttgart")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Stuttgart"
    assert data["result"]["name"] == "Stuttgart"
    assert data["result"]["coordinates"] == {"lat": 48.7758, "lon": 9.1829}


@pytest.mark.asyncio
async def test_get_weather_forecast(client, override_weather_dependency):
    response = await client.get("/api/v1/weather/forecast?lat=52.52&lon=13.405&days=2")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 2
    assert len(data["forecast"]) == 2
    assert data["forecast"][0]["condition"] == "Clouds"


@pytest.mark.asyncio
async def test_weather_query_validation(client):
    response = await client.get("/api/v1/weather/forecast?days=9")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_weather_rejects_city_and_coordinates_together(client, override_weather_dependency):
    response = await client.get("/api/v1/weather/current?city=Stuttgart&lat=52.52&lon=13.405")
    assert response.status_code == 422
