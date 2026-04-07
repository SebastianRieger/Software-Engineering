from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
    )

    PROJECT_NAME: str = "Nimrag Smart Mirror"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS configuration
    CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Frontend development
        "http://localhost:8080",  # Vue.js development
        "http://localhost:5173",  # Vite development
    ]

    # JWT Settings
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database settings
    DATABASE_URL: str = "sqlite:///./nimrag.db"

    # External API settings
    WEATHER_API_KEY: str = ""
    WEATHER_TIMEOUT_SECONDS: float = 5.0
    WEATHER_CACHE_TTL_SECONDS: int = 600
    FORECAST_CACHE_TTL_SECONDS: int = 1800
    DEFAULT_LAT: float = 48.7758
    DEFAULT_LON: float = 9.1829
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GESTURES_DEV_ENDPOINT_ENABLED: bool = False
    GESTURE_SMOOTHING_ALPHA: float = 0.6
    GESTURE_MAX_TRAJECTORY_POINTS: int = 64
    GESTURE_COOLDOWN_SECONDS: float = 1.0
    GESTURE_SWIPE_THRESHOLD: float = 0.12
    GESTURE_DOWN_THRESHOLD: float = 0.12
    GESTURE_CIRCLE_SWEEP_MIN: float = 4.5
    GESTURE_CIRCLE_RADIUS_CV_MAX: float = 0.5
    GESTURE_IDLE_SLEEP_SECONDS: float = 0.02

    # MQTT settings
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""

    LOG_LEVEL: str = "INFO"

    @property
    def sqlite_path(self) -> Path:
        if self.DATABASE_URL.startswith("sqlite:///"):
            raw_path = self.DATABASE_URL.removeprefix("sqlite:///")
            path = Path(raw_path)
            if not path.is_absolute():
                path = BASE_DIR / path
            return path.resolve()

        return (BASE_DIR / "nimrag.db").resolve()


settings = Settings()
