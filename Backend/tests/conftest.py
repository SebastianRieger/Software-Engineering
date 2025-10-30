import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from main import app

@pytest.fixture
def client():
    """
    Test client fixture for FastAPI application
    """
    return TestClient(app)

@pytest.fixture
def mock_weather_service():
    """
    Mock weather service for testing
    """
    class MockWeatherService:
        async def get_current_weather(self, city: str):
            return {
                "temperature": 20.0,
                "humidity": 65,
                "condition": "Clear",
                "city": city
            }
    return MockWeatherService()

@pytest.fixture
def mock_led_service():
    """
    Mock LED service for testing without hardware
    """
    class MockLEDService:
        def __init__(self):
            self.state = {
                "red": 0,
                "green": 0,
                "blue": 0,
                "brightness": 1.0
            }
        
        def set_color(self, rgb):
            r, g, b = rgb
            self.state["red"] = r
            self.state["green"] = g
            self.state["blue"] = b
            return True
        
        def set_brightness(self, value):
            self.state["brightness"] = value
            return True
    
    return MockLEDService()