from typing import Literal

from pydantic import BaseModel


class BullshitResponse(BaseModel):
    phrases: list[str]
    source: Literal["live", "cache"] = "live"
