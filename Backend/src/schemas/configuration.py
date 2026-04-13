from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from core.config import settings


class WidgetConfig(BaseModel):
    widget_id: str = Field(min_length=1)
    widget_type: str = Field(min_length=1)
    cell_id: int = Field(ge=1, le=16)
    title: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class LayoutConfig(BaseModel):
    version: int = 1
    widgets: list[WidgetConfig] = Field(default_factory=list)
    updated_at: datetime | None = None


class LayoutConfigEnvelope(BaseModel):
    profile: str = "default"
    config: LayoutConfig


class SystemConfig(BaseModel):
    location_name: str | None = None
    latitude: float = Field(default=settings.DEFAULT_LAT, ge=-90, le=90)
    longitude: float = Field(default=settings.DEFAULT_LON, ge=-180, le=180)
    units: Literal["metric", "imperial"] = "metric"
    theme: Literal["dark", "light", "system"] = "dark"
    weather_refresh_seconds: int = Field(default=900, ge=60, le=86400)
    updated_at: datetime | None = None


class SystemConfigEnvelope(BaseModel):
    config: SystemConfig
