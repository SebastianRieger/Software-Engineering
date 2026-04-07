import json
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import aiohttp

from core.config import settings
from core.database import get_db_connection


logger = logging.getLogger(__name__)


class WeatherRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class WeatherRepository:
    def __init__(self) -> None:
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def get_current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        cache_key = self._cache_key("current", lat, lon)
        cached = self._get_cached_payload(cache_key, settings.WEATHER_CACHE_TTL_SECONDS)
        if cached is not None:
            cached["source"] = "cache"
            return cached

        try:
            live_data = await self._fetch_current_weather(lat, lon)
        except WeatherRepositoryError:
            stale_cache = self._get_cached_payload(cache_key, ttl_seconds=None)
            if stale_cache is not None:
                stale_cache["source"] = "cache"
                return stale_cache
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    async def get_forecast(self, lat: float, lon: float, days: int = 5) -> dict[str, Any]:
        cache_key = self._cache_key(f"forecast:{days}", lat, lon)
        cached = self._get_cached_payload(cache_key, settings.FORECAST_CACHE_TTL_SECONDS)
        if cached is not None:
            cached["source"] = "cache"
            return cached

        try:
            live_data = await self._fetch_forecast(lat, lon, days)
        except WeatherRepositoryError:
            stale_cache = self._get_cached_payload(cache_key, ttl_seconds=None)
            if stale_cache is not None:
                stale_cache["source"] = "cache"
                return stale_cache
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    def count_cache_entries(self) -> int:
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM weather_cache"
            ).fetchone()
        return int(row["count"])

    async def _fetch_current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        data = await self._request_json(
            "/weather",
            {"lat": lat, "lon": lon, "units": "metric"},
        )

        return {
            "location_name": data.get("name"),
            "coordinates": {"lat": lat, "lon": lon},
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["main"],
            "wind_speed": data["wind"]["speed"],
            "timestamp": datetime.fromtimestamp(data["dt"], tz=timezone.utc).isoformat(),
        }

    async def _fetch_forecast(self, lat: float, lon: float, days: int) -> dict[str, Any]:
        data = await self._request_json(
            "/forecast",
            {"lat": lat, "lon": lon, "units": "metric"},
        )

        daily_buckets: dict[str, dict[str, Any]] = {}
        for item in data.get("list", []):
            timestamp = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            bucket_key = timestamp.date().isoformat()
            bucket = daily_buckets.setdefault(
                bucket_key,
                {
                    "date": timestamp.date().isoformat(),
                    "min_temp": item["main"]["temp_min"],
                    "max_temp": item["main"]["temp_max"],
                    "conditions": [],
                },
            )
            bucket["min_temp"] = min(bucket["min_temp"], item["main"]["temp_min"])
            bucket["max_temp"] = max(bucket["max_temp"], item["main"]["temp_max"])
            bucket["conditions"].append(item["weather"][0]["main"])

        forecast_items = []
        for bucket_key in sorted(daily_buckets.keys())[:days]:
            bucket = daily_buckets[bucket_key]
            common_condition = Counter(bucket["conditions"]).most_common(1)[0][0]
            forecast_items.append(
                {
                    "date": bucket["date"],
                    "min_temp": bucket["min_temp"],
                    "max_temp": bucket["max_temp"],
                    "condition": common_condition,
                }
            )

        return {
            "location_name": data.get("city", {}).get("name"),
            "coordinates": {"lat": lat, "lon": lon},
            "days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "forecast": forecast_items,
        }

    async def _request_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise WeatherRepositoryError(
                "Weather API key is not configured and no cached data is available.",
                status_code=503,
            )

        request_params = {"appid": self.api_key, **params}
        timeout = aiohttp.ClientTimeout(total=settings.WEATHER_TIMEOUT_SECONDS)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url}{endpoint}",
                    params=request_params,
                ) as response:
                    if response.status >= 400:
                        detail = await response.text()
                        raise WeatherRepositoryError(
                            f"Weather provider returned {response.status}: {detail}",
                            status_code=502,
                        )
                    return await response.json()
        except aiohttp.ClientError as exc:
            logger.warning("Weather provider request failed: %s", exc)
            raise WeatherRepositoryError(
                "Weather provider is currently unavailable.",
                status_code=502,
            ) from exc

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
    def _cache_key(prefix: str, lat: float, lon: float) -> str:
        return f"{prefix}:{lat:.4f}:{lon:.4f}"
