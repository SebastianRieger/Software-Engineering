from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class LEDControl(BaseModel):
    color: str
    brightness: int = 100
    mode: str = "static"


@router.post("/led/control")
async def control_led(cmd: LEDControl):
    # TODO: integrate with hardware/leds module
    return {"status": "ok", "applied": cmd.dict()}
