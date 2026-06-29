import json
import logging
from datetime import datetime, timezone

import aiohttp

from core.config import settings
from core.database import get_db_connection
from schemas.nina import NinaNormalizedWarning, NinaWarningsResponse

logger = logging.getLogger(__name__)

NINA_API_URL = "https://warnung.bund.de/api31/dashboard/{ars}.json"
NINA_CACHE_TTL_SECONDS = 300  # 5 minutes


class NinaRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class NinaRepository:
    @staticmethod
    def _is_active(item: dict) -> bool:
        if item.get("type") == "Cancel":
            return False

        expires = item.get("payload", {}).get("data", {}).get("expires")
        if expires:
            try:
                expires_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                if expires_dt < datetime.now(timezone.utc):
                    return False
            except (ValueError, AttributeError):
                pass

        return True

    @staticmethod
    def _normalize(item: dict) -> NinaNormalizedWarning:
        data = item.get("payload", {}).get("data", {})
        i18n_title = item.get("i18nTitle", {})

        headline = data.get("headline") or i18n_title.get("de") or "Unbekannte Warnung"

        severity_raw = data.get("severity", "Unknown")
        severity = (
            severity_raw
            if severity_raw in {"Extreme", "Severe", "Moderate", "Minor"}
            else "Unknown"
        )

        msg_type_raw = item.get("type", "Alert")
        msg_type = (
            msg_type_raw if msg_type_raw in {"Alert", "Update", "Cancel"} else "Alert"
        )

        return NinaNormalizedWarning(
            id=item.get("id", ""),
            severity=severity,
            headline=headline,
            sender_name=data.get("senderName", ""),
            event=data.get("event") or None,
            sent=data.get("sent", datetime.now(timezone.utc).isoformat()),
            msg_type=msg_type,
        )

    def _get_cached_payload(self, cache_key: str) -> list | None:
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload, fetched_at FROM nina_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()

        if row is None:
            return None

        fetched_at = datetime.fromisoformat(row["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        if age > NINA_CACHE_TTL_SECONDS:
            return None

        return json.loads(row["payload"])

    def _store_payload(self, cache_key: str, payload: list) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO nina_cache (cache_key, payload, fetched_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    fetched_at = excluded.fetched_at
                """,
                (cache_key, json.dumps(payload), now),
            )

    async def get_warnings(self, ars: str) -> NinaWarningsResponse:
        cache_key = f"nina:{ars}"
        now = datetime.now(timezone.utc)

        cached = self._get_cached_payload(cache_key)
        if cached is not None:
            warnings = [NinaNormalizedWarning(**w) for w in cached]
            return NinaWarningsResponse(
                ars=ars, warnings=warnings, fetched_at=now, source="cache"
            )

        url = NINA_API_URL.format(ars=ars)
        timeout = aiohttp.ClientTimeout(total=settings.WEATHER_TIMEOUT_SECONDS)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status >= 400:
                        raise NinaRepositoryError(
                            f"NINA API returned {response.status}",
                            status_code=502,
                        )
                    raw_items = await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            logger.warning("NINA API request failed: %s", exc)
            raise NinaRepositoryError(
                "NINA-Warndienst ist derzeit nicht erreichbar.",
                status_code=502,
            ) from exc

        active_warnings = [
            self._normalize(item) for item in raw_items if self._is_active(item)
        ]

        self._store_payload(cache_key, [w.model_dump() for w in active_warnings])

        return NinaWarningsResponse(
            ars=ars, warnings=active_warnings, fetched_at=now, source="live"
        )
