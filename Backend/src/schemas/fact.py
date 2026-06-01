from typing import Literal

from pydantic import BaseModel


class DailyFact(BaseModel):
    text: str
    source: Literal["live", "cache"] = "live"
