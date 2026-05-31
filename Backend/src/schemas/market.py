from typing import Literal

from pydantic import BaseModel, Field


class MarketItem(BaseModel):
    id: str
    symbol: str
    name: str
    price: float
    change: float
    percent_change: float
    currency: str
    asset_type: Literal["stock", "crypto"]


class MarketResponse(BaseModel):
    items: list[MarketItem] = Field(default_factory=list)
    source: Literal["live", "cache"] = "live"
