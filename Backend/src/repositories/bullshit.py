import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import aiohttp

from core.database import get_db_connection

CORPORATE_BS_API_URL = "https://corporatebs-generator.sameerkumar.website/"
PHRASES_PER_HOUR = 5


class BullshitRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class BullshitRepository:
    async def get_phrases(self) -> dict[str, Any]:
        hour_key = datetime.now().strftime("%Y-%m-%d-%H")
        cache_key = f"bullshit:{hour_key}"

        cached = self._get_cached_payload(cache_key)
        if cached is not None:
            cached["source"] = "cache"
            return cached

        try:
            live_data = await self._fetch_phrases(PHRASES_PER_HOUR)
        except BullshitRepositoryError:
            stale = self._get_any_cached_bullshit()
            if stale is not None:
                stale["source"] = "cache"
                return stale
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    async def _fetch_phrases(self, count: int) -> dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=10)

        async def fetch_one(session: aiohttp.ClientSession) -> str | Exception:
            try:
                async with session.get(CORPORATE_BS_API_URL) as response:
                    if response.status >= 400:
                        return BullshitRepositoryError(
                            f"Corporate BS API returned HTTP {response.status}",
                            status_code=502,
                        )
                    payload = await response.json(content_type=None)
                    text = payload.get("phrase", "").strip() if isinstance(payload, dict) else ""
                    if not text:
                        return BullshitRepositoryError(
                            "Corporate BS API returned no phrase.", status_code=502
                        )
                    return text
            except (TimeoutError, aiohttp.ClientError) as exc:
                return exc

        async with aiohttp.ClientSession(timeout=timeout) as session:
            results = await asyncio.gather(
                *[fetch_one(session) for _ in range(count)],
                return_exceptions=True,
            )

        phrases = [r for r in results if isinstance(r, str)]

        if not phrases:
            raise BullshitRepositoryError(
                "All Corporate BS API requests failed.", status_code=502
            )

        return {"phrases": phrases}

    def _get_cached_payload(self, cache_key: str) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM weather_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row["payload"])

    def _get_any_cached_bullshit(self) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM weather_cache
                WHERE cache_key LIKE 'bullshit:%'
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
