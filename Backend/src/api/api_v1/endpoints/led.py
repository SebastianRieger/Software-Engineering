from fastapi import APIRouter

from schemas.led import LEDBrightnessRequest, LEDColorRequest, LEDStateResponse

router = APIRouter()

_led_state = {
    "red": 0.0,
    "green": 0.0,
    "blue": 0.0,
    "brightness": 1.0,
}


@router.post("/color", response_model=LEDStateResponse)
async def set_led_color(payload: LEDColorRequest):
    _led_state["red"] = payload.red
    _led_state["green"] = payload.green
    _led_state["blue"] = payload.blue
    return {
        "message": "LED color set",
        **_led_state,
    }


@router.post("/brightness", response_model=LEDStateResponse)
async def set_led_brightness(payload: LEDBrightnessRequest):
    _led_state["brightness"] = payload.brightness
    return {
        "message": "LED brightness set",
        **_led_state,
    }
