import json
from datetime import date, datetime, timezone
from typing import Any

import aiohttp

from core.database import get_db_connection

USELESSFACTS_API_URL = "https://uselessfacts.jsph.pl/api/v2/facts/today"


class FactRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class FactRepository:
    async def get_fact(self) -> dict[str, Any]:
        today = date.today().isoformat()
        cache_key = f"fact:{today}"

        cached = self._get_cached_payload(cache_key)
        if cached is not None:
            cached["source"] = "cache"
            return cached

        try:
            live_data = await self._fetch_fact()
        except FactRepositoryError:
            stale = self._get_any_cached_fact()
            if stale is not None:
                stale["source"] = "cache"
                return stale
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    async def _fetch_fact(self) -> dict[str, Any]:
        params = {"language": "de"}
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(USELESSFACTS_API_URL, params=params) as response:
                    if response.status >= 400:
                        raise FactRepositoryError(
                            f"uselessfacts API returned HTTP {response.status}",
                            status_code=502,
                        )
                    payload = await response.json(content_type=None)
        except TimeoutError as exc:
            raise FactRepositoryError(
                "uselessfacts API request timed out.", status_code=502
            ) from exc
        except aiohttp.ClientError as exc:
            raise FactRepositoryError(
                "uselessfacts API is not reachable.", status_code=502
            ) from exc

        text = payload.get("text", "").strip() if isinstance(payload, dict) else ""
        if not text:
            raise FactRepositoryError(
                "uselessfacts API returned no fact text.", status_code=502
            )

        return {"text": text}

    def _get_cached_payload(self, cache_key: str) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM weather_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row["payload"])

    def _get_any_cached_fact(self) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM weather_cache
                WHERE cache_key LIKE 'fact:%'
                ORDER BY fetched_at DESC
                LIMIT 1
                """,
            ).fetchone()

        if row is None:
            return None

        return json.loads(row["payload"])

    def _store_payload(self, cache_key: str, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO weather_cache (cache_key, payload, fetched_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    fetched_at = excluded.fetched_at
                """,
                (cache_key, json.dumps(payload), now),
            )
