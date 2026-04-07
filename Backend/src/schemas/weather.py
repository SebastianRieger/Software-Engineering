from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float
    lon: float


class WeatherCurrentResponse(BaseModel):
    location_name: str | None = None
    coordinates: Coordinates
    temperature: float
    humidity: float = Field(ge=0, le=100)
    condition: str
    wind_speed: float
    timestamp: datetime
    source: Literal["live", "cache"]


class WeatherForecastEntry(BaseModel):
    date: date
    min_temp: float
    max_temp: float
    condition: str


class WeatherForecastResponse(BaseModel):
    location_name: str | None = None
    coordinates: Coordinates
    days: int = Field(ge=1, le=7)
    generated_at: datetime
    forecast: list[WeatherForecastEntry]
    source: Literal["live", "cache"]
