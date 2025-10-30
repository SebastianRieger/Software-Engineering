from fastapi.testclient import TestClient
import pytest

def test_set_led_color(client, mock_led_service):
    """
    Test LED color setting endpoint
    """
    test_color = [1.0, 0.5, 0.0]  # Orange
    response = client.post("/api/v1/led/color", json=test_color)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "LED color set"
    assert data["rgb"] == test_color

def test_set_led_brightness(client, mock_led_service):
    """
    Test LED brightness setting endpoint
    """
    test_brightness = 0.75
    response = client.post("/api/v1/led/brightness", json=test_brightness)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "LED brightness set"
    assert data["brightness"] == test_brightness

def test_invalid_color_values(client):
    """
    Test LED endpoint handles invalid color values
    """
    invalid_color = [2.0, -1.0, 0.5]  # Values outside 0-1 range
    response = client.post("/api/v1/led/color", json=invalid_color)
    assert response.status_code == 422  # Validation error