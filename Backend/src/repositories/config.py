from datetime import datetime, timezone

from core.database import get_db_connection
from schemas.calibration import (
    CalibrationAppliedSnapshot,
    CalibrationModality,
    CalibrationProfile,
    CalibrationSessionRecord,
)
from schemas.commands import (
    CommandDevicePreferences,
    CommandModalitySettings,
    CommandProfile,
    CommandProfilesConfig,
)
from schemas.configuration import LayoutConfig, SystemConfig
from schemas.gestures import GestureConfig
from schemas.interactions import InputActionConfig
from schemas.musical_audio import MusicalAudioConfig, MusicalAudioTrainingArtifact
from schemas.voice import VoiceConfig


class ConfigRepository:
    def get_layout(self, profile: str = "default") -> LayoutConfig:
        config_key = self._layout_key(profile)
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return LayoutConfig()

        return LayoutConfig.model_validate_json(row["payload"])

    def save_layout(self, layout: LayoutConfig, profile: str = "default") -> LayoutConfig:
        timestamp = datetime.now(timezone.utc)
        updated_layout = layout.model_copy(update={"updated_at": timestamp})
        config_key = self._layout_key(profile)

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_layout.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_layout

    def get_system_config(self) -> SystemConfig:
        config_key = self._system_key()
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return SystemConfig()

        return SystemConfig.model_validate_json(row["payload"])

    def save_system_config(self, config: SystemConfig) -> SystemConfig:
        timestamp = datetime.now(timezone.utc)
        updated_config = config.model_copy(update={"updated_at": timestamp})
        config_key = self._system_key()

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_config.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_config

    def get_gesture_config(self) -> GestureConfig:
        config_key = self._gesture_key()
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return GestureConfig()

        return GestureConfig.model_validate_json(row["payload"])

    def save_gesture_config(self, config: GestureConfig) -> GestureConfig:
        timestamp = datetime.now(timezone.utc)
        updated_config = config.model_copy(update={"updated_at": timestamp})
        config_key = self._gesture_key()

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_config.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_config

    def get_voice_config(self) -> VoiceConfig:
        config_key = self._voice_key()
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        config = VoiceConfig() if row is None else VoiceConfig.model_validate_json(row["payload"])
        active_profile = self._get_active_command_profile_from_row()
        if active_profile is None:
            return config

        modality = active_profile.modality_settings.get("voice", CommandModalitySettings(enabled=config.enabled))
        device_index = active_profile.device_preferences.voice_device_index
        return config.model_copy(
            update={
                "enabled": modality.enabled,
                "device_index": device_index if device_index is not None else config.device_index,
            }
        )

    def save_voice_config(self, config: VoiceConfig) -> VoiceConfig:
        timestamp = datetime.now(timezone.utc)
        updated_config = config.model_copy(update={"updated_at": timestamp})
        config_key = self._voice_key()

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_config.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        command_profiles = self.get_command_profiles_config()
        active_profile = self._select_active_command_profile(command_profiles)
        updated_profile = active_profile.model_copy(
            update={
                "device_preferences": active_profile.device_preferences.model_copy(
                    update={"voice_device_index": updated_config.device_index}
                ),
                "modality_settings": {
                    **active_profile.modality_settings,
                    "voice": active_profile.modality_settings.get(
                        "voice",
                        CommandModalitySettings(enabled=True),
                    ).model_copy(update={"enabled": updated_config.enabled}),
                },
                "updated_at": timestamp,
            }
        )
        self.save_command_profiles_config(
            command_profiles.model_copy(
                update={
                    "profiles": [
                        updated_profile if profile.profile_id == updated_profile.profile_id else profile
                        for profile in command_profiles.profiles
                    ],
                    "updated_at": timestamp,
                }
            )
        )

        return updated_config

    def get_input_action_config(self) -> InputActionConfig:
        command_profiles = self._get_command_profiles_row()
        if command_profiles is not None:
            config = CommandProfilesConfig.model_validate_json(command_profiles["payload"])
            return self._select_active_command_profile(config).input_action_config

        return self._get_legacy_input_action_config()

    def save_input_action_config(self, config: InputActionConfig) -> InputActionConfig:
        timestamp = datetime.now(timezone.utc)
        updated_config = config.model_copy(update={"updated_at": timestamp})
        config_key = self._input_action_key()

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_config.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        command_profiles = self.get_command_profiles_config()
        active_profile = self._select_active_command_profile(command_profiles)
        updated_profile = active_profile.model_copy(
            update={
                "input_action_config": updated_config,
                "updated_at": timestamp,
            }
        )
        self.save_command_profiles_config(
            command_profiles.model_copy(
                update={
                    "profiles": [
                        updated_profile if profile.profile_id == updated_profile.profile_id else profile
                        for profile in command_profiles.profiles
                    ],
                    "updated_at": timestamp,
                }
            )
        )

        return updated_config

    def get_command_profiles_config(self) -> CommandProfilesConfig:
        row = self._get_command_profiles_row()
        if row is not None:
            return CommandProfilesConfig.model_validate_json(row["payload"])

        legacy_input_actions = self._get_legacy_input_action_config()
        voice_config = self.get_voice_config()
        return CommandProfilesConfig(
            active_profile_id="default",
            profiles=[
                CommandProfile(
                    profile_id="default",
                    display_name="Standard",
                    input_action_config=legacy_input_actions,
                    modality_settings={
                        "gesture": CommandModalitySettings(enabled=True),
                        "voice": CommandModalitySettings(enabled=voice_config.enabled),
                        "musical_audio": CommandModalitySettings(enabled=False),
                        "keyboard": CommandModalitySettings(enabled=True),
                        "dev": CommandModalitySettings(enabled=True),
                    },
                    device_preferences=CommandDevicePreferences(
                        voice_device_index=voice_config.device_index,
                    ),
                )
            ],
        )

    def save_command_profiles_config(self, config: CommandProfilesConfig) -> CommandProfilesConfig:
        timestamp = datetime.now(timezone.utc)
        updated_config = config.model_copy(
            update={
                "profiles": [
                    profile.model_copy(update={"updated_at": timestamp})
                    for profile in config.profiles
                ],
                "updated_at": timestamp,
            }
        )
        config_key = self._command_profiles_key()

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_config.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        active_profile = self._select_active_command_profile(updated_config)
        legacy_input_actions = active_profile.input_action_config.model_copy(update={"updated_at": timestamp})
        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    self._input_action_key(),
                    legacy_input_actions.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_config

    def get_active_command_profile(self) -> CommandProfile:
        return self._select_active_command_profile(self.get_command_profiles_config())

    def get_musical_audio_config(self) -> MusicalAudioConfig:
        config = self._load_persisted_musical_audio_config()
        active_profile = self.get_active_command_profile()
        return self._compose_musical_audio_config(config, active_profile)

    def save_musical_audio_config(self, config: MusicalAudioConfig) -> MusicalAudioConfig:
        timestamp = datetime.now(timezone.utc)
        updated_config = MusicalAudioConfig(
            sample_rate=config.sample_rate,
            block_size=config.block_size,
            queue_max_chunks=config.queue_max_chunks,
            silence_threshold=config.silence_threshold,
            pitch_confidence_threshold=config.pitch_confidence_threshold,
            command_cooldown_seconds=config.command_cooldown_seconds,
            min_pattern_notes=config.min_pattern_notes,
            max_pattern_window_seconds=config.max_pattern_window_seconds,
            updated_at=timestamp,
        )
        config_key = self._musical_audio_key()

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_config.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        command_profiles = self.get_command_profiles_config()
        active_profile = self._select_active_command_profile(command_profiles)
        updated_profile = active_profile.model_copy(
            update={
                "device_preferences": active_profile.device_preferences.model_copy(
                    update={"musical_audio_device_index": config.device_index}
                ),
                "modality_settings": {
                    **active_profile.modality_settings,
                    "musical_audio": active_profile.modality_settings.get(
                        "musical_audio",
                        CommandModalitySettings(enabled=False),
                    ).model_copy(
                        update={
                            "enabled": config.enabled,
                            "active_training_artifact_id": config.active_artifact_id,
                        }
                    ),
                },
                "updated_at": timestamp,
            }
        )
        self.save_command_profiles_config(
            command_profiles.model_copy(
                update={
                    "profiles": [
                        updated_profile if profile.profile_id == updated_profile.profile_id else profile
                        for profile in command_profiles.profiles
                    ],
                    "updated_at": timestamp,
                }
            )
        )

        return self.get_musical_audio_config()

    def list_musical_audio_training_artifacts(self, profile_id: str = "default") -> list[MusicalAudioTrainingArtifact]:
        like_pattern = self._musical_audio_artifact_prefix(profile_id)
        with get_db_connection() as connection:
            rows = connection.execute(
                "SELECT payload FROM app_config WHERE config_key LIKE ? ORDER BY updated_at DESC",
                (f"{like_pattern}%",),
            ).fetchall()

        return [MusicalAudioTrainingArtifact.model_validate_json(row["payload"]) for row in rows]

    def get_musical_audio_training_artifact(
        self,
        artifact_id: str,
        profile_id: str = "default",
    ) -> MusicalAudioTrainingArtifact | None:
        config_key = self._musical_audio_artifact_key(profile_id=profile_id, artifact_id=artifact_id)
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return None

        return MusicalAudioTrainingArtifact.model_validate_json(row["payload"])

    def save_musical_audio_training_artifact(
        self,
        artifact: MusicalAudioTrainingArtifact,
    ) -> MusicalAudioTrainingArtifact:
        timestamp = datetime.now(timezone.utc)
        existing = self.get_musical_audio_training_artifact(artifact.artifact_id, profile_id=artifact.profile_id)
        created_at = existing.created_at if existing is not None else timestamp
        updated_artifact = artifact.model_copy(update={"created_at": created_at, "updated_at": timestamp})
        config_key = self._musical_audio_artifact_key(
            profile_id=updated_artifact.profile_id,
            artifact_id=updated_artifact.artifact_id,
        )

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_artifact.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_artifact

    def delete_musical_audio_training_artifact(self, artifact_id: str, profile_id: str = "default") -> bool:
        config_key = self._musical_audio_artifact_key(profile_id=profile_id, artifact_id=artifact_id)
        with get_db_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM app_config WHERE config_key = ?",
                (config_key,),
            )
        return cursor.rowcount > 0

    def get_calibration_session(self, session_id: str) -> CalibrationSessionRecord | None:
        config_key = self._calibration_session_key(session_id)
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return None

        return CalibrationSessionRecord.model_validate_json(row["payload"])

    def list_calibration_sessions(
        self,
        modality: CalibrationModality | None = None,
    ) -> list[CalibrationSessionRecord]:
        like_pattern = self._calibration_sessions_prefix()
        with get_db_connection() as connection:
            rows = connection.execute(
                "SELECT payload FROM app_config WHERE config_key LIKE ? ORDER BY updated_at DESC",
                (f"{like_pattern}%",),
            ).fetchall()

        sessions = [CalibrationSessionRecord.model_validate_json(row["payload"]) for row in rows]
        if modality is None:
            return sessions
        return [session for session in sessions if session.modality == modality]

    def save_calibration_session(self, session: CalibrationSessionRecord) -> CalibrationSessionRecord:
        timestamp = datetime.now(timezone.utc)
        updated_session = session.model_copy(update={"updated_at": timestamp})
        config_key = self._calibration_session_key(session.session_id)

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_session.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_session

    def get_calibration_profile(
        self,
        modality: CalibrationModality,
        profile: str = "default",
    ) -> CalibrationProfile | None:
        config_key = self._calibration_profile_key(modality=modality, profile=profile)
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return None

        return CalibrationProfile.model_validate_json(row["payload"])

    def save_calibration_profile(self, profile: CalibrationProfile) -> CalibrationProfile:
        timestamp = datetime.now(timezone.utc)
        updated_profile = profile.model_copy(update={"saved_at": timestamp})
        config_key = self._calibration_profile_key(modality=profile.modality, profile=profile.profile)

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_profile.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_profile

    def get_last_applied_calibration_snapshot(
        self,
        modality: CalibrationModality,
        profile: str = "default",
    ) -> CalibrationAppliedSnapshot | None:
        config_key = self._calibration_last_applied_key(modality=modality, profile=profile)
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return None

        return CalibrationAppliedSnapshot.model_validate_json(row["payload"])

    def save_last_applied_calibration_snapshot(
        self,
        snapshot: CalibrationAppliedSnapshot,
    ) -> CalibrationAppliedSnapshot:
        timestamp = datetime.now(timezone.utc)
        updated_snapshot = snapshot.model_copy(update={"captured_at": timestamp})
        config_key = self._calibration_last_applied_key(modality=snapshot.modality, profile=snapshot.profile)

        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config (config_key, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    config_key,
                    updated_snapshot.model_dump_json(),
                    timestamp.isoformat(),
                ),
            )

        return updated_snapshot

    def count_entries(self) -> int:
        with get_db_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM app_config").fetchone()
        return int(row["count"])

    def _get_legacy_input_action_config(self) -> InputActionConfig:
        config_key = self._input_action_key()
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return InputActionConfig()

        return InputActionConfig.model_validate_json(row["payload"])

    def _get_command_profiles_row(self):
        config_key = self._command_profiles_key()
        with get_db_connection() as connection:
            return connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

    def _apply_voice_command_profile_overrides(self, config: VoiceConfig) -> VoiceConfig:
        command_profiles_row = self._get_command_profiles_row()
        if command_profiles_row is None:
            return config

        active_profile = self._select_active_command_profile(
            CommandProfilesConfig.model_validate_json(command_profiles_row["payload"])
        )
        voice_settings = active_profile.modality_settings.get("voice", CommandModalitySettings(enabled=config.enabled))
        device_index = active_profile.device_preferences.voice_device_index
        return config.model_copy(
            update={
                "enabled": voice_settings.enabled,
                "device_index": device_index if device_index is not None else config.device_index,
            }
        )

    def _apply_musical_audio_command_profile_overrides(
        self,
        config: MusicalAudioConfig,
    ) -> MusicalAudioConfig:
        command_profiles_row = self._get_command_profiles_row()
        if command_profiles_row is None:
            return config

        active_profile = self._select_active_command_profile(
            CommandProfilesConfig.model_validate_json(command_profiles_row["payload"])
        )
        return self._compose_musical_audio_config(config, active_profile)

    def _load_persisted_musical_audio_config(self) -> MusicalAudioConfig:
        config_key = self._musical_audio_key()
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return MusicalAudioConfig()

        return MusicalAudioConfig.model_validate_json(row["payload"])

    @staticmethod
    def _compose_musical_audio_config(
        config: MusicalAudioConfig,
        active_profile: CommandProfile,
    ) -> MusicalAudioConfig:
        musical_settings = active_profile.modality_settings.get(
            "musical_audio",
            CommandModalitySettings(enabled=config.enabled),
        )
        device_index = active_profile.device_preferences.musical_audio_device_index
        return config.model_copy(
            update={
                "enabled": musical_settings.enabled,
                "device_index": device_index if device_index is not None else config.device_index,
                "active_artifact_id": musical_settings.active_training_artifact_id,
            }
        )

    def _get_active_command_profile_from_row(self) -> CommandProfile | None:
        row = self._get_command_profiles_row()
        if row is None:
            return None
        config = CommandProfilesConfig.model_validate_json(row["payload"])
        return self._select_active_command_profile(config)

    @staticmethod
    def _select_active_command_profile(config: CommandProfilesConfig) -> CommandProfile:
        for profile in config.profiles:
            if profile.profile_id == config.active_profile_id:
                return profile
        return config.profiles[0]

    @staticmethod
    def _layout_key(profile: str) -> str:
        return f"layout:{profile}"

    @staticmethod
    def _system_key() -> str:
        return "system:global"

    @staticmethod
    def _gesture_key() -> str:
        return "gestures:global"

    @staticmethod
    def _voice_key() -> str:
        return "voice:global"

    @staticmethod
    def _input_action_key() -> str:
        return "input-actions:global"

    @staticmethod
    def _command_profiles_key() -> str:
        return "command-profiles:global"

    @staticmethod
    def _musical_audio_key() -> str:
        return "musical-audio:global"

    @staticmethod
    def _musical_audio_artifact_prefix(profile_id: str) -> str:
        return f"musical-audio:artifact:{profile_id}:"

    @classmethod
    def _musical_audio_artifact_key(cls, profile_id: str, artifact_id: str) -> str:
        return f"{cls._musical_audio_artifact_prefix(profile_id)}{artifact_id}"

    @staticmethod
    def _calibration_sessions_prefix() -> str:
        return "calibration:session:"

    @classmethod
    def _calibration_session_key(cls, session_id: str) -> str:
        return f"{cls._calibration_sessions_prefix()}{session_id}"

    @staticmethod
    def _calibration_profile_key(modality: CalibrationModality, profile: str) -> str:
        return f"calibration:profile:{modality}:{profile}"

    @staticmethod
    def _calibration_last_applied_key(modality: CalibrationModality, profile: str) -> str:
        return f"calibration:last-applied:{modality}:{profile}"
