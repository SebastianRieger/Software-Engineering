from pydantic import BaseModel


class WeatherResponse(BaseModel):
    location: str
    timestamp: str
    temperature_c: float
    humidity: int
    wind_speed: float
    condition: str

    class Config:
        schema_extra = {
            "example": {
                "location": "Berlin",
                "timestamp": "2025-10-28T12:00:00Z",
                "temperature_c": 18.5,
                "humidity": 56,
                "wind_speed": 3.2,
                "condition": "Partly Cloudy",
            }
        }
