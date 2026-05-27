import json
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from core.config import settings
from schemas.configuration import AppConfig


class AppConfigRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class AppConfigRepository:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or settings.app_config_path

    def get_app_config(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()

        try:
            raw_payload = self.config_path.read_text(encoding="utf-8")
            payload = json.loads(raw_payload)
            return AppConfig.model_validate(payload)
        except JSONDecodeError as exc:
            raise AppConfigRepositoryError(
                f"App-Konfigurationsdatei ist kein gueltiges JSON: {exc.msg}",
                status_code=500,
            ) from exc
        except ValidationError as exc:
            raise AppConfigRepositoryError(
                f"App-Konfigurationsdatei ist ungueltig: {exc}",
                status_code=500,
            ) from exc