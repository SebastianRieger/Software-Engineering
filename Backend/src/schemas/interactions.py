from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

UIActionType = Literal[
    "move_focus_left",
    "move_focus_right",
    "move_focus_up",
    "move_focus_down",
    "focus_grid_cell",
    "focus_widget_type",
    "toggle_shop",
    "open_shop",
    "close_shop",
    "primary_click",
    "confirm_selection",
    "secondary_select",
    "enter_arrange_mode",
    "exit_arrange_mode",
    "resize_expand",
    "resize_shrink",
    "move_selected_widget",
    "cancel_selection",
    "toggle_edit_mode",
    "delete_widget",
    "begin_drag",
    "drop_widget",
]

InputSourceType = Literal["gesture", "voice", "musical_audio", "dev", "keyboard"]
CommandMatchOutcome = Literal["accepted", "suppressed", "unmapped", "disabled"]
UIActionMode = Literal["grid", "shop", "arrange"]


class UIActionArguments(BaseModel):
    cell_index: int | None = Field(default=None, ge=1)
    widget_type: str | None = Field(default=None, min_length=1)
    mode: UIActionMode | None = None


class InputActionMapping(BaseModel):
    input_source: InputSourceType
    raw_input: str = Field(min_length=1)
    action: UIActionType
    enabled: bool = True
    action_args: UIActionArguments = Field(default_factory=UIActionArguments)
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_default_input_action_mappings() -> list[InputActionMapping]:
    return [
        InputActionMapping(
            input_source="gesture", raw_input="swipe_left", action="move_focus_left"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="swipe_right", action="move_focus_right"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="swipe_up", action="move_focus_up"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="swipe_down", action="move_focus_down"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="circle", action="toggle_edit_mode"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="pinch_close", action="primary_click"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="pinch_open", action="drop_widget"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="push_click_short", action="resize_expand"
        ),
        InputActionMapping(
            input_source="gesture",
            raw_input="push_click_long",
            action="delete_widget",
        ),
        InputActionMapping(
            input_source="gesture", raw_input="zoom_out_hands", action="resize_shrink"
        ),
        InputActionMapping(
            input_source="gesture", raw_input="zoom_in_hands", action="resize_expand"
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.move_focus_left",
            action="move_focus_left",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.move_focus_right",
            action="move_focus_right",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.move_focus_up",
            action="move_focus_up",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.move_focus_down",
            action="move_focus_down",
        ),
        InputActionMapping(
            input_source="voice", raw_input="voice.open_shop", action="open_shop"
        ),
        InputActionMapping(
            input_source="voice", raw_input="voice.close_shop", action="close_shop"
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.confirm_selection",
            action="confirm_selection",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.cancel_selection",
            action="cancel_selection",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.enter_arrange_mode",
            action="enter_arrange_mode",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.exit_arrange_mode",
            action="exit_arrange_mode",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.resize_expand",
            action="resize_expand",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.resize_shrink",
            action="resize_shrink",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.focus_grid_cell",
            action="focus_grid_cell",
        ),
        InputActionMapping(
            input_source="voice",
            raw_input="voice.focus_widget_type",
            action="focus_widget_type",
        ),
    ]


def build_default_source_priorities() -> dict[InputSourceType, int]:
    return {
        "voice": 100,
        "musical_audio": 90,
        "gesture": 80,
        "keyboard": 70,
        "dev": 100,
    }


class InputActionConfig(BaseModel):
    mappings: list[InputActionMapping] = Field(
        default_factory=build_default_input_action_mappings
    )
    global_cooldown_seconds: float = Field(default=0.3, ge=0, le=30)
    repeat_same_action_window_seconds: float = Field(default=0.4, ge=0, le=30)
    source_priorities: dict[InputSourceType, int] = Field(
        default_factory=build_default_source_priorities
    )
    updated_at: datetime | None = None


class InputActionConfigEnvelope(BaseModel):
    config: InputActionConfig


class UIActionEventPayload(BaseModel):
    action: UIActionType
    timestamp: datetime
    input_source: InputSourceType
    raw_input: str = Field(min_length=1)
    action_args: UIActionArguments = Field(default_factory=UIActionArguments)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UIActionEventEnvelope(BaseModel):
    eventType: Literal["UIActionRequested"] = "UIActionRequested"
    payload: UIActionEventPayload


class RawInputDetectedEventPayload(BaseModel):
    input_source: InputSourceType
    raw_input: str = Field(min_length=1)
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawInputDetectedEventEnvelope(BaseModel):
    eventType: Literal["RawInputDetected"] = "RawInputDetected"
    payload: RawInputDetectedEventPayload


class CommandMatchEventPayload(BaseModel):
    input_source: InputSourceType
    raw_input: str = Field(min_length=1)
    timestamp: datetime
    outcome: CommandMatchOutcome
    action: UIActionType | None = None
    reason: str | None = None
    action_args: UIActionArguments = Field(default_factory=UIActionArguments)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommandMatchEventEnvelope(BaseModel):
    eventType: Literal["CommandMatchEvaluated"] = "CommandMatchEvaluated"
    payload: CommandMatchEventPayload


class SimulatedInputRequest(BaseModel):
    input_source: InputSourceType = "gesture"
    raw_input: str = Field(min_length=1)
    action_args: UIActionArguments = Field(default_factory=UIActionArguments)
    metadata: dict[str, Any] = Field(default_factory=dict)
    emit_raw_input_event: bool = True


class SimulatedInputResponse(BaseModel):
    accepted: bool
    input_source: InputSourceType
    raw_input: str = Field(min_length=1)
    action_args: UIActionArguments = Field(default_factory=UIActionArguments)
    metadata: dict[str, Any] = Field(default_factory=dict)
    emitted_events: list[
        Literal["RawInputDetected", "CommandMatchEvaluated", "UIActionRequested"]
    ] = Field(default_factory=list)
