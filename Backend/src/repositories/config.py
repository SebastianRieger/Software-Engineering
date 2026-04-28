from datetime import datetime, timezone

from core.database import get_db_connection
from schemas.configuration import LayoutConfig, SystemConfig
from schemas.gestures import GestureConfig
from schemas.interactions import InputActionConfig
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

        if row is None:
            return VoiceConfig()

        return VoiceConfig.model_validate_json(row["payload"])

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

        return updated_config

    def get_input_action_config(self) -> InputActionConfig:
        config_key = self._input_action_key()
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM app_config WHERE config_key = ?",
                (config_key,),
            ).fetchone()

        if row is None:
            return InputActionConfig()

        return InputActionConfig.model_validate_json(row["payload"])

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

        return updated_config

    def count_entries(self) -> int:
        with get_db_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM app_config").fetchone()
        return int(row["count"])

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
