import json
from datetime import datetime, timezone
from typing import Any

import aiohttp

from core.config import settings
from core.database import get_db_connection


TAGESSCHAU_API_URL = "https://www.tagesschau.de/api2u/news/"


class NewsRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class NewsRepository:
    async def get_news(
        self,
        ressort: str | None = None,
        regions: list[int] | None = None,
    ) -> dict[str, Any]:
        cache_key = self._cache_key(ressort=ressort, regions=regions)
        cached = self._get_cached_payload(cache_key, settings.NEWS_CACHE_TTL_SECONDS)
        if cached is not None:
            cached["source"] = "cache"
            return cached

        try:
            live_data = await self._fetch_news(ressort=ressort, regions=regions)
        except NewsRepositoryError:
            stale_cache = self._get_cached_payload(cache_key, ttl_seconds=None)
            if stale_cache is not None:
                stale_cache["source"] = "cache"
                return stale_cache
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    async def _fetch_news(
        self,
        ressort: str | None,
        regions: list[int] | None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if ressort:
            params["ressort"] = ressort
        if regions:
            params["regions"] = ",".join(str(region) for region in regions)

        timeout = aiohttp.ClientTimeout(total=settings.NEWS_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(TAGESSCHAU_API_URL, params=params) as response:
                    if response.status >= 400:
                        raise NewsRepositoryError(
                            f"Tagesschau API returned HTTP {response.status}",
                            status_code=502,
                        )
                    payload = await response.json(content_type=None)
        except TimeoutError as exc:
            raise NewsRepositoryError(
                "Tagesschau API request timed out.", status_code=502
            ) from exc
        except aiohttp.ClientError as exc:
            raise NewsRepositoryError(
                "Tagesschau API is not reachable.", status_code=502
            ) from exc

        news_items = payload.get("news", []) if isinstance(payload, dict) else []
        return {"news": news_items}

    def _get_cached_payload(
        self,
        cache_key: str,
        ttl_seconds: int | None,
    ) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT payload, fetched_at
                FROM weather_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()

        if row is None:
            return None

        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if ttl_seconds is not None:
            age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
            if age_seconds > ttl_seconds:
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

    @staticmethod
    def _cache_key(ressort: str | None, regions: list[int] | None) -> str:
        ressort_key = ressort or "all"
        region_key = ",".join(str(region) for region in regions or []) or "all"
        return f"news:{ressort_key}:{region_key}"