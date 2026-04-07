from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
