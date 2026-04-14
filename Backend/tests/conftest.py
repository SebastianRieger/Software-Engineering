import pytest
import pytest_asyncio
import sys
from pathlib import Path
import httpx

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from api.data_endpoints import get_weather_service
from api.device_endpoints import get_led_service, get_voice_service
from api.system_endpoints import get_config_repository, get_gesture_service
from core.config import settings
from core.database import init_db
from main import app
from repositories.config import ConfigRepository
from services.gestures import GestureServiceError
from services.voice import VoiceServiceError


@pytest_asyncio.fixture
async def client(tmp_path):
    settings.DATABASE_URL = f"sqlite:///{tmp_path / 'test.db'}"
    init_db()
    app.dependency_overrides.clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_weather_service():
    class MockWeatherService:
        async def get_current_weather(self, lat: float, lon: float):
            return {
                "temperature": 20.0,
                "humidity": 65,
                "condition": "Clear",
                "wind_speed": 3.5,
                "timestamp": "2026-04-07T10:00:00+00:00",
                "location_name": "Berlin",
                "coordinates": {"lat": lat, "lon": lon},
                "source": "live",
            }

        async def get_forecast(self, days: int, lat: float, lon: float):
            return {
                "location_name": "Berlin",
                "coordinates": {"lat": lat, "lon": lon},
                "days": days,
                "generated_at": "2026-04-07T10:00:00+00:00",
                "source": "live",
                "forecast": [
                    {
                        "date": "2026-04-07",
                        "min_temp": 10.0,
                        "max_temp": 18.0,
                        "condition": "Clouds",
                    },
                    {
                        "date": "2026-04-08",
                        "min_temp": 11.0,
                        "max_temp": 19.0,
                        "condition": "Rain",
                    },
                ][:days],
            }

    return MockWeatherService()


@pytest.fixture
def mock_led_service():
    class MockLEDService:
        def __init__(self):
            self.state = {
                "red": 0.0,
                "green": 0.0,
                "blue": 0.0,
                "brightness": 1.0,
                "available": True,
                "mode": "mock",
                "last_error": None,
            }

        def get_status(self):
            return {
                "message": "LED status",
                **self.state,
            }

        def set_color(self, rgb):
            r, g, b = rgb
            self.state["red"] = r
            self.state["green"] = g
            self.state["blue"] = b
            return {
                "message": "LED color set",
                **self.state,
            }

        def set_brightness(self, value):
            self.state["brightness"] = value
            return {
                "message": "LED brightness set",
                **self.state,
            }

        def shutdown(self):
            return None

    return MockLEDService()


@pytest.fixture
def mock_voice_service():
    class MockVoiceService:
        def __init__(self):
            self.state = {
                "message": "Voice status",
                "available": False,
                "running": False,
                "mode": "skeleton",
                "provider": "vosk",
                "device_index": None,
                "last_command": None,
                "last_command_at": None,
                "last_error": "Mikrofonpfad ist vorbereitet, aber noch nicht implementiert.",
            }

        def get_status(self):
            return dict(self.state)

        def start(self, device_index: int = 0):
            self.state["device_index"] = device_index
            raise VoiceServiceError("Mikrofonpfad ist vorbereitet, aber noch nicht implementiert.", status_code=503)

        def stop(self):
            self.state["running"] = False
            self.state["device_index"] = None
            return {
                **self.state,
                "message": "Voice stopped",
            }

        def shutdown(self):
            return None

    return MockVoiceService()


@pytest.fixture
def config_repository():
    return ConfigRepository()


@pytest.fixture
def mock_gesture_service():
    class MockGestureService:
        def __init__(self, available: bool = True):
            self.available = available
            self.running = False
            self.camera_index = None
            self.last_gesture = None
            self.last_gesture_at = None
            self.frame = None

        def get_status(self):
            return {
                "available": self.available,
                "running": self.running,
                "camera_index": self.camera_index,
                "last_gesture": self.last_gesture,
                "last_gesture_at": self.last_gesture_at,
                "debug_frame_available": self.frame is not None,
            }

        def start(self, camera_index: int = 0):
            if not self.available:
                raise GestureServiceError(
                    "Gestenerkennung ist in dieser Umgebung nicht verfuegbar.",
                    status_code=503,
                )
            self.running = True
            self.camera_index = camera_index
            return self.get_status()

        def stop(self):
            self.running = False
            self.camera_index = None
            return self.get_status()

        def get_frame(self):
            return self.frame

        def process_video(self, video_path: str):
            _ = video_path
            return {
                "gestures": ["circle"],
                "frames_processed": 42,
                "trajectory_points": 21,
                "confidence": 0.91,
                "tracking_source": "palm_center",
            }

    return MockGestureService()


@pytest.fixture
def unavailable_gesture_service():
    class UnavailableGestureService:
        def get_status(self):
            return {
                "available": False,
                "running": False,
                "camera_index": None,
                "last_gesture": None,
                "last_gesture_at": None,
                "debug_frame_available": False,
            }

        def start(self, camera_index: int = 0):
            raise GestureServiceError(
                "Gestenerkennung ist in dieser Umgebung nicht verfuegbar.",
                status_code=503,
            )

        def stop(self):
            return self.get_status()

        def get_frame(self):
            return None

        def process_video(self, video_path: str):
            raise GestureServiceError("Gestenerkennung ist deaktiviert.", status_code=503)

    return UnavailableGestureService()


@pytest.fixture
def override_weather_dependency(mock_weather_service):
    async def _override_weather_service():
        return mock_weather_service

    app.dependency_overrides[get_weather_service] = _override_weather_service
    yield
    app.dependency_overrides.pop(get_weather_service, None)


@pytest.fixture
def override_config_dependency(config_repository):
    async def _override_config_repository():
        return config_repository

    app.dependency_overrides[get_config_repository] = _override_config_repository
    yield
    app.dependency_overrides.pop(get_config_repository, None)


@pytest.fixture
def override_gesture_dependency(mock_gesture_service):
    async def _override_gesture_service():
        return mock_gesture_service

    app.dependency_overrides[get_gesture_service] = _override_gesture_service
    yield mock_gesture_service
    app.dependency_overrides.pop(get_gesture_service, None)


@pytest.fixture
def override_led_dependency(mock_led_service):
    async def _override_led_service():
        return mock_led_service

    app.dependency_overrides[get_led_service] = _override_led_service
    yield mock_led_service
    app.dependency_overrides.pop(get_led_service, None)


@pytest.fixture
def override_voice_dependency(mock_voice_service):
    async def _override_voice_service():
        return mock_voice_service

    app.dependency_overrides[get_voice_service] = _override_voice_service
    yield mock_voice_service
    app.dependency_overrides.pop(get_voice_service, None)


@pytest.fixture
def override_unavailable_gesture_dependency(unavailable_gesture_service):
    async def _override_gesture_service():
        return unavailable_gesture_service

    app.dependency_overrides[get_gesture_service] = _override_gesture_service
    yield unavailable_gesture_service
    app.dependency_overrides.pop(get_gesture_service, None)

