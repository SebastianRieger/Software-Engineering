from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class NinaNormalizedWarning(BaseModel):
    id: str
    severity: str  # "Extreme" | "Severe" | "Moderate" | "Minor" | "Unknown"
    headline: str
    sender_name: str
    event: str | None
    sent: str  # ISO-8601 datetime string
    msg_type: str  # "Alert" | "Update" | "Cancel"


class NinaWarningsResponse(BaseModel):
    ars: str
    warnings: list[NinaNormalizedWarning]
    fetched_at: datetime
    source: Literal["live", "cache"]
