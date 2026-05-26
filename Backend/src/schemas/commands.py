from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from schemas.interactions import InputActionConfig

CommandModalityType = Literal["gesture", "voice", "musical_audio", "keyboard", "dev"]


class CommandModalitySettings(BaseModel):
    enabled: bool = True
    active_training_artifact_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_default_modality_settings() -> (
    dict[CommandModalityType, CommandModalitySettings]
):
    return {
        "gesture": CommandModalitySettings(enabled=True),
        "voice": CommandModalitySettings(enabled=True),
        "musical_audio": CommandModalitySettings(enabled=False),
        "keyboard": CommandModalitySettings(enabled=True),
        "dev": CommandModalitySettings(enabled=True),
    }


class CommandDevicePreferences(BaseModel):
    gesture_camera_index: int | None = Field(default=None, ge=0)
    voice_device_index: int | None = Field(default=None, ge=-1)
    musical_audio_device_index: int | None = Field(default=None, ge=-1)


class CommandProfile(BaseModel):
    profile_id: str = Field(default="default", min_length=1)
    display_name: str = Field(default="Standard", min_length=1)
    description: str | None = None
    input_action_config: InputActionConfig = Field(default_factory=InputActionConfig)
    modality_settings: dict[CommandModalityType, CommandModalitySettings] = Field(
        default_factory=build_default_modality_settings
    )
    device_preferences: CommandDevicePreferences = Field(
        default_factory=CommandDevicePreferences
    )
    updated_at: datetime | None = None


class CommandProfilesConfig(BaseModel):
    active_profile_id: str = Field(default="default", min_length=1)
    profiles: list[CommandProfile] = Field(default_factory=lambda: [CommandProfile()])
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def ensure_active_profile_exists(self) -> "CommandProfilesConfig":
        if not self.profiles:
            self.profiles = [CommandProfile()]

        if not any(
            profile.profile_id == self.active_profile_id for profile in self.profiles
        ):
            self.active_profile_id = self.profiles[0].profile_id

        return self


class CommandProfilesConfigEnvelope(BaseModel):
    config: CommandProfilesConfig
