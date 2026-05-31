from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from core.config import settings

GRID_ROWS = 4
GRID_COLUMNS = 4


def cell_id_to_position(cell_id: int) -> tuple[int, int]:
    zero_based_cell = cell_id - 1
    return (zero_based_cell // GRID_COLUMNS) + 1, (zero_based_cell % GRID_COLUMNS) + 1


def position_to_cell_id(row: int, col: int) -> int:
    return ((row - 1) * GRID_COLUMNS) + col


class WidgetConfig(BaseModel):
    widget_id: str = Field(min_length=1)
    widget_type: str = Field(min_length=1)
    row: int = Field(default=1, ge=1, le=GRID_ROWS)
    col: int = Field(default=1, ge=1, le=GRID_COLUMNS)
    row_span: int = Field(default=1, ge=1, le=GRID_ROWS)
    col_span: int = Field(default=1, ge=1, le=GRID_COLUMNS)
    cell_id: int | None = Field(default=None, ge=1, le=GRID_ROWS * GRID_COLUMNS)
    title: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_cell_id(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        next_value = dict(value)
        cell_id = next_value.get("cell_id")
        if cell_id is not None and (
            next_value.get("row") is None or next_value.get("col") is None
        ):
            row, col = cell_id_to_position(int(cell_id))
            next_value.setdefault("row", row)
            next_value.setdefault("col", col)

        next_value.setdefault("row_span", 1)
        next_value.setdefault("col_span", 1)
        return next_value

    @model_validator(mode="after")
    def _sync_cell_id(self) -> "WidgetConfig":
        if self.cell_id is None:
            self.cell_id = position_to_cell_id(self.row, self.col)
        return self


class LayoutConfig(BaseModel):
    version: int = 2
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


NewsRessort = Literal[
    "inland",
    "ausland",
    "wirtschaft",
    "sport",
    "video",
    "investigativ",
    "wissen",
]


class WeatherWidgetConfig(BaseModel):
    refresh_seconds: int = Field(default=900, ge=60, le=86400)


class NewsWidgetConfig(BaseModel):
    ressort: NewsRessort | None = None
    regions: list[int] = Field(default_factory=lambda: [1])
    refresh_seconds: int = Field(default=3600, ge=60, le=86400)


class CameraWidgetConfig(BaseModel):
    preferred_device_id: str | None = None
    preferred_device_label: str | None = None


class MarketWidgetConfig(BaseModel):
    symbols: list[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA", "BTC/USD", "ETH/USD"]
    )
    refresh_seconds: int = Field(default=900, ge=60, le=86400)
class NinaWidgetConfig(BaseModel):
    ars: str  # Pflichtfeld – kein Standardwert, muss in app_config.json stehen
    refresh_seconds: int = Field(default=300, ge=60, le=86400)


class WidgetDefaultsConfig(BaseModel):
    weather: WeatherWidgetConfig = Field(default_factory=WeatherWidgetConfig)
    news: NewsWidgetConfig = Field(default_factory=NewsWidgetConfig)
    camera: CameraWidgetConfig = Field(default_factory=CameraWidgetConfig)
    market: MarketWidgetConfig = Field(default_factory=MarketWidgetConfig)
    nina: NinaWidgetConfig | None = None


class AppConfig(BaseModel):
    version: int = 1
    system: SystemConfig = Field(default_factory=SystemConfig)
    widgets: WidgetDefaultsConfig = Field(default_factory=WidgetDefaultsConfig)


class AppConfigEnvelope(BaseModel):
    config: AppConfig
