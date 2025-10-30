import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

def test_get_weather(client, mock_weather_service):
    """
    Test weather endpoint returns correct data
    """
    response = client.get("/api/v1/weather?city=Berlin")
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data
    assert "humidity" in data
    assert "condition" in data
    assert data["city"] == "Berlin"

def test_weather_error_handling(client):
    """
    Test weather endpoint handles invalid input
    """
    response = client.get("/api/v1/weather?city=")
    assert response.status_code == 422  # Validation error