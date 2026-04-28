from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


UIActionType = Literal[
    "move_focus_left",
    "move_focus_right",
    "move_focus_up",
    "move_focus_down",
    "toggle_shop",
    "primary_click",
    "secondary_select",
    "resize_expand",
    "resize_shrink",
    "move_selected_widget",
    "cancel_selection",
]

InputSourceType = Literal["gesture", "voice", "dev", "keyboard"]


class InputActionMapping(BaseModel):
    input_source: InputSourceType
    raw_input: str = Field(min_length=1)
    action: UIActionType
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_default_input_action_mappings() -> list[InputActionMapping]:
    return [
        InputActionMapping(input_source="gesture", raw_input="swipe_left", action="move_focus_left"),
        InputActionMapping(input_source="gesture", raw_input="swipe_right", action="move_focus_right"),
        InputActionMapping(input_source="gesture", raw_input="swipe_up", action="move_focus_up"),
        InputActionMapping(input_source="gesture", raw_input="swipe_down", action="move_focus_down"),
        InputActionMapping(input_source="gesture", raw_input="circle", action="toggle_shop"),
        InputActionMapping(input_source="gesture", raw_input="push_click_short", action="primary_click"),
        InputActionMapping(input_source="gesture", raw_input="push_click_long", action="secondary_select"),
        InputActionMapping(input_source="gesture", raw_input="zoom_out_hands", action="resize_expand"),
        InputActionMapping(input_source="gesture", raw_input="zoom_in_hands", action="resize_shrink"),
    ]


class InputActionConfig(BaseModel):
    mappings: list[InputActionMapping] = Field(default_factory=build_default_input_action_mappings)
    updated_at: datetime | None = None


class InputActionConfigEnvelope(BaseModel):
    config: InputActionConfig


class UIActionEventPayload(BaseModel):
    action: UIActionType
    timestamp: datetime
    input_source: InputSourceType
    raw_input: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UIActionEventEnvelope(BaseModel):
    eventType: Literal["UIActionRequested"] = "UIActionRequested"
    payload: UIActionEventPayload