from pydantic import BaseModel, Field
from typing import Literal


class LEDColorRequest(BaseModel):
    red: float = Field(ge=0.0, le=1.0)
    green: float = Field(ge=0.0, le=1.0)
    blue: float = Field(ge=0.0, le=1.0)


class LEDBrightnessRequest(BaseModel):
    brightness: float = Field(ge=0.0, le=1.0)


class LEDStateResponse(BaseModel):
    message: str
    red: float = Field(ge=0.0, le=1.0)
    green: float = Field(ge=0.0, le=1.0)
    blue: float = Field(ge=0.0, le=1.0)
    brightness: float = Field(ge=0.0, le=1.0)
    available: bool
    mode: Literal["hardware", "mock"] = "mock"
    last_error: str | None = None
