from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    PROJECT_NAME: str = "Nimrag Smart Mirror"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS configuration
    CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Frontend development
        "http://localhost:8080",  # Vue.js development
    ]
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./nimrag.db"
    
    # External API settings
    WEATHER_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # MQTT settings
    MQTT_BROKER: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()