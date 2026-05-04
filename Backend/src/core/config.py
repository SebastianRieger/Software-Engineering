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
    GESTURE_SWIPE_THRESHOLD: float = 0.1
    GESTURE_DOWN_THRESHOLD: float = 0.12
    GESTURE_UP_THRESHOLD: float = 0.14
    GESTURE_SWIPE_MIN_SPAN: float = 0.055
    GESTURE_CIRCLE_SWEEP_MIN: float = 3.25
    GESTURE_CIRCLE_RADIUS_CV_MAX: float = 0.6
    GESTURE_CIRCLE_MIN_RADIUS: float = 0.01
    GESTURE_MIN_DETECTION_POINTS: int = 6
    GESTURE_MIN_CONFIDENCE: float = 0.55
    GESTURE_HAND_SIZE_REFERENCE: float = 0.16
    GESTURE_HAND_SIZE_SCALE_MIN: float = 0.6
    GESTURE_HAND_SIZE_SCALE_MAX: float = 1.8
    GESTURE_PUSH_DEPTH_THRESHOLD: float = 0.024
    GESTURE_PUSH_RELEASE_THRESHOLD: float = 0.015
    GESTURE_PUSH_POSE_EXTENSION_RATIO: float = 1.05
    GESTURE_CENTER_TOLERANCE: float = 0.35
    GESTURE_LONG_CLICK_SECONDS: float = 0.5
    GESTURE_PUSH_REQUIRED_FOLDED_FINGERS: int = 2
    GESTURE_PUSH_FOLDED_DISTANCE_RATIO: float = 1.12
    GESTURE_PUSH_RELAXED_CENTER_TOLERANCE_MULTIPLIER: float = 1.18
    GESTURE_PUSH_RELAXED_CENTER_TOLERANCE_MAX: float = 0.5
    GESTURE_PUSH_DEPTH_ASSIST_MIN_THRESHOLD: float = 0.025
    GESTURE_PUSH_DEPTH_ASSIST_THRESHOLD_RATIO: float = 0.85
    GESTURE_CLICK_POSE_CENTER_TOLERANCE_MULTIPLIER: float = 1.35
    GESTURE_CLICK_POSE_EXTENSION_RATIO_MULTIPLIER: float = 0.92
    GESTURE_CLICK_POSE_EXTENSION_RATIO_FLOOR: float = 1.02
    GESTURE_PUSH_TRANSIENT_POSE_GAP_MAX_SECONDS: float = 0.16
    GESTURE_PUSH_TRANSIENT_POSE_GAP_LONG_RATIO: float = 0.35
    GESTURE_PUSH_SHORT_CLICK_MIN_DURATION: float = 0.08
    GESTURE_PUSH_LONG_RELEASE_MAX_GAP_SECONDS: float = 0.25
    GESTURE_ZOOM_DISTANCE_DELTA_THRESHOLD: float = 0.16
    GESTURE_ZOOM_START_NEAR_DISTANCE: float = 0.22
    GESTURE_ZOOM_START_FAR_DISTANCE: float = 0.42
    GESTURE_TWO_HAND_MIN_FRAMES: int = 3
    GESTURE_RUNTIME_CIRCLE_POSE_MAX_OPENNESS: float = 0.52
    GESTURE_RUNTIME_SWIPE_BLOCK_MAX_OPENNESS: float = 0.30
    GESTURE_RUNTIME_CIRCLE_HOLD_RADIUS_CV_RATIO: float = 0.95
    GESTURE_RUNTIME_CIRCLE_HOLD_SWEEP_RATIO: float = 0.7
    GESTURE_RUNTIME_CIRCLE_HOLD_MIN_ASPECT_RATIO: float = 0.28
    GESTURE_RUNTIME_UPSTROKE_START_Y_MIN: float = 0.46
    GESTURE_RUNTIME_UPSTROKE_END_Y_MAX: float = 0.42
    GESTURE_RUNTIME_VERTICAL_DISPLACEMENT_MIN: float = 0.08
    GESTURE_RUNTIME_DOWNSTROKE_START_Y_MAX: float = 0.56
    GESTURE_RUNTIME_DOWNSTROKE_END_Y_MIN: float = 0.58
    GESTURE_PRIMITIVE_HAND_CENTERED_THRESHOLD: float = 0.5
    GESTURE_PRIMITIVE_STABLE_HOLD_THRESHOLD: float = 0.62
    GESTURE_PRIMITIVE_INDEX_PRIMARY_THRESHOLD: float = 0.62
    GESTURE_PRIMITIVE_ALL_FINGERS_OPEN_THRESHOLD: float = 0.6
    GESTURE_PRIMITIVE_FIST_LIKE_THRESHOLD: float = 0.6
    GESTURE_PRIMITIVE_PUSH_FORWARD_THRESHOLD: float = 0.55
    GESTURE_PRIMITIVE_PALM_VISIBLE_SCORE: float = 0.78
    GESTURE_PRIMITIVE_PALM_VISIBLE_THRESHOLD: float = 0.5
    GESTURE_PRIMITIVE_SWIPE_JITTER_DAMPING: float = 0.5
    GESTURE_PRIMITIVE_CIRCLE_MOTION_THRESHOLD: float = 0.58
    GESTURE_PRIMITIVE_TWO_HAND_THRESHOLD: float = 0.55
    GESTURE_RESOLVER_PUSH_CENTERED_SCORE_FLOOR: float = 0.6
    GESTURE_RESOLVER_TRACKING_QUALITY_TRAJECTORY_WEIGHT: float = 0.45
    GESTURE_RESOLVER_TRACKING_QUALITY_POSE_WEIGHT: float = 0.35
    GESTURE_RESOLVER_TRACKING_QUALITY_HAND_WEIGHT: float = 0.20
    GESTURE_RESOLVER_CANDIDATE_CONFIDENCE_WEIGHT: float = 0.55
    GESTURE_RESOLVER_CANDIDATE_PRIMITIVE_WEIGHT: float = 0.35
    GESTURE_RESOLVER_CANDIDATE_PHASE_WEIGHT: float = 0.10
    GESTURE_RESOLVER_REQUIRED_PRIMITIVE_MIN_SCORE: float = 0.45
    GESTURE_CANDIDATE_HORIZONTAL_DOMINANCE_RATIO: float = 1.5
    GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_SPAN_RATIO: float = 2.0
    GESTURE_CANDIDATE_HORIZONTAL_MAX_OFF_AXIS_MOTION_RATIO: float = 0.75
    GESTURE_CANDIDATE_VERTICAL_DOMINANCE_RATIO: float = 1.2
    GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_SPAN_RATIO: float = 1.2
    GESTURE_CANDIDATE_VERTICAL_MAX_OFF_AXIS_MOTION_RATIO: float = 0.3
    GESTURE_CANDIDATE_CIRCLE_MIN_ASPECT_RATIO: float = 0.2
    GESTURE_PHASE_HOLD_MAX_PEAK_SPEED: float = 0.08
    GESTURE_PHASE_HOLD_MIN_STABILITY: float = 0.68
    GESTURE_PHASE_PREPARING_MAX_SECONDS: float = 0.14
    GESTURE_PHASE_RELEASE_MAX_RECENT_SPEED: float = 0.025
    GESTURE_PHASE_RELEASE_SPEED_RATIO: float = 0.35
    GESTURE_PHASE_COMMIT_DISTANCE_THRESHOLD: float = 0.02
    GESTURE_PENDING_TIMEOUT_SECONDS: float = 0.3
    GESTURE_PENDING_FINALIZE_SECONDS: float = 0.12
    GESTURE_PENDING_LONG_FINALIZE_SECONDS: float = 0.16
    GESTURE_POST_FIRE_GRACE_SECONDS: float = 0.2
    GESTURE_OFFLINE_SWIPE_MIN_CYCLE_POINTS: int = 4
    GESTURE_OFFLINE_SWIPE_MOTION_STEP_THRESHOLD: float = 0.02
    GESTURE_OFFLINE_SWIPE_EDGE_SPEED_THRESHOLD: float = 0.025
    GESTURE_OFFLINE_SWIPE_ACTIVE_GAP_SECONDS: float = 0.45
    GESTURE_OFFLINE_SWIPE_AXIS_RATIO_THRESHOLD: float = 1.2
    GESTURE_OFFLINE_SWIPE_EDGE_GAP_RATIO: float = 0.5
    GESTURE_OFFLINE_SWIPE_EDGE_GAP_MAX_SECONDS: float = 0.22
    GESTURE_OFFLINE_PUSH_MIN_CYCLE_POINTS: int = 4
    GESTURE_OFFLINE_PUSH_ACTIVE_GAP_SECONDS: float = 0.45
    GESTURE_OFFLINE_PUSH_MIN_POSE_VALID_RATIO: float = 0.6
    GESTURE_OFFLINE_PUSH_INACTIVE_GRACE_SECONDS: float = 0.18
    GESTURE_READ_RETRY_ATTEMPTS: int = 2
    GESTURE_READ_RETRY_DELAY_SECONDS: float = 0.03
    GESTURE_STOP_JOIN_TIMEOUT_SECONDS: float = 2.0
    GESTURE_IDLE_SLEEP_SECONDS: float = 0.02
    VOICE_ENABLED: bool = True
    VOICE_DEVICE_INDEX: int = -1
    VOICE_MODEL_PATH: str = ""
    VOICE_SAMPLE_RATE: int = 16000
    VOICE_BLOCK_SIZE: int = 2048
    VOICE_QUEUE_MAX_CHUNKS: int = 12
    VOICE_ENERGY_THRESHOLD: float = 200.0
    VOICE_COMMAND_COOLDOWN_SECONDS: float = 1.5
    VOICE_PARTIAL_RESULTS_ENABLED: bool = True
    VOICE_STOP_JOIN_TIMEOUT_SECONDS: float = 2.0
    VOICE_GRID_CELL_COUNT: int = 16
    VOICE_COMMANDS: List[str] = [
        "licht an",
        "licht aus",
        "naechstes widget",
        "vorheriges widget",
    ]
    VOICE_SIGNAL_SYNONYMS: dict[str, List[str]] = {
        "voice.move_focus_left": ["links", "nach links"],
        "voice.move_focus_right": ["rechts", "nach rechts"],
        "voice.move_focus_up": ["oben", "hoch", "nach oben"],
        "voice.move_focus_down": ["unten", "runter", "nach unten"],
        "voice.open_shop": ["shop", "shop auf", "laden", "auswahl"],
        "voice.close_shop": ["shop zu", "shop schliessen", "auswahl schliessen"],
        "voice.confirm_selection": ["bestaetigen", "platzieren", "fertig"],
        "voice.cancel_selection": ["abbrechen", "zurueck"],
        "voice.enter_arrange_mode": ["verschieben", "anordnen", "bearbeiten"],
        "voice.exit_arrange_mode": ["anordnung beenden", "verschieben fertig", "bearbeiten fertig"],
        "voice.resize_expand": ["groesser", "vergroessern"],
        "voice.resize_shrink": ["kleiner", "verkleinern"],
    }
    VOICE_WIDGET_ALIASES: dict[str, List[str]] = {
        "weather": ["wetter"],
        "clock": ["uhr", "zeit"],
        "template": ["hardware"],
    }
    MUSICAL_AUDIO_ENABLED: bool = False
    MUSICAL_AUDIO_DEVICE_INDEX: int = -1
    MUSICAL_AUDIO_SAMPLE_RATE: int = 16000
    MUSICAL_AUDIO_BLOCK_SIZE: int = 1024
    MUSICAL_AUDIO_QUEUE_MAX_CHUNKS: int = 12
    MUSICAL_AUDIO_SILENCE_THRESHOLD: float = 0.015
    MUSICAL_AUDIO_PITCH_CONFIDENCE_THRESHOLD: float = 0.65
    MUSICAL_AUDIO_COMMAND_COOLDOWN_SECONDS: float = 1.2
    MUSICAL_AUDIO_MIN_PATTERN_NOTES: int = 3
    MUSICAL_AUDIO_MAX_PATTERN_WINDOW_SECONDS: float = 4.0
    MUSICAL_AUDIO_STOP_JOIN_TIMEOUT_SECONDS: float = 2.0

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
