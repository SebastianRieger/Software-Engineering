import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiohttp
import openmeteo_requests
import requests_cache
from retry_requests import retry

from core.config import settings
from core.database import get_db_connection

logger = logging.getLogger(__name__)


WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
GEOCODING_CACHE_TTL_SECONDS = 24 * 60 * 60

WMO_CONDITION_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with light hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class WeatherRepository:
    def __init__(self) -> None:
        cache_dir = settings.sqlite_path.parent / ".http_cache"
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        cache_session = requests_cache.CachedSession(
            str(cache_dir / "open-meteo"),
            expire_after=settings.FORECAST_CACHE_TTL_SECONDS,
        )
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=retry_session)

    async def geocode_city(self, city: str) -> dict[str, Any]:
        normalized_city = city.strip()
        cache_key = f"geocode:{normalized_city.casefold()}"
        cached = self._get_cached_payload(cache_key, GEOCODING_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached

        geocoded = await self._fetch_geocoding(normalized_city)
        self._store_payload(cache_key, geocoded)
        return geocoded

    async def get_current_weather(
        self,
        lat: float | None = None,
        lon: float | None = None,
        city: str | None = None,
    ) -> dict[str, Any]:
        lat, lon, location_name = await self._resolve_location(
            lat=lat, lon=lon, city=city
        )
        cache_key = self._cache_key("current", lat, lon)
        cached = self._get_cached_payload(cache_key, settings.WEATHER_CACHE_TTL_SECONDS)
        if cached is not None:
            cached["source"] = "cache"
            if location_name and not cached.get("location_name"):
                cached["location_name"] = location_name
            return cached

        try:
            live_data = await self._fetch_current_weather(
                lat=lat, lon=lon, location_name=location_name
            )
        except WeatherRepositoryError:
            stale_cache = self._get_cached_payload(cache_key, ttl_seconds=None)
            if stale_cache is not None:
                stale_cache["source"] = "cache"
                if location_name and not stale_cache.get("location_name"):
                    stale_cache["location_name"] = location_name
                return stale_cache
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    async def get_forecast(
        self,
        lat: float | None = None,
        lon: float | None = None,
        days: int = 5,
        city: str | None = None,
    ) -> dict[str, Any]:
        lat, lon, location_name = await self._resolve_location(
            lat=lat, lon=lon, city=city
        )
        cache_key = self._cache_key(f"forecast:{days}", lat, lon)
        cached = self._get_cached_payload(
            cache_key, settings.FORECAST_CACHE_TTL_SECONDS
        )
        if cached is not None:
            cached["source"] = "cache"
            if location_name and not cached.get("location_name"):
                cached["location_name"] = location_name
            return cached

        try:
            live_data = await self._fetch_forecast(
                lat=lat,
                lon=lon,
                days=days,
                location_name=location_name,
            )
        except WeatherRepositoryError:
            stale_cache = self._get_cached_payload(cache_key, ttl_seconds=None)
            if stale_cache is not None:
                stale_cache["source"] = "cache"
                if location_name and not stale_cache.get("location_name"):
                    stale_cache["location_name"] = location_name
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

    async def _fetch_current_weather(
        self,
        lat: float,
        lon: float,
        location_name: str | None,
    ) -> dict[str, Any]:
        response = await self._request_weather_api(
            {
                "latitude": lat,
                "longitude": lon,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "weather_code",
                    "wind_speed_10m",
                ],
                "timezone": "auto",
            }
        )
        current = response.Current()
        response_timezone = self._response_timezone(response.UtcOffsetSeconds())

        return {
            "location_name": location_name,
            "coordinates": {
                "lat": float(response.Latitude()),
                "lon": float(response.Longitude()),
            },
            "temperature": float(current.Variables(0).Value()),
            "humidity": int(round(current.Variables(1).Value())),
            "condition": self._weather_condition_from_code(
                current.Variables(2).Value()
            ),
            "wind_speed": float(current.Variables(3).Value()),
            "timestamp": datetime.fromtimestamp(
                current.Time(),
                tz=timezone.utc,
            )
            .astimezone(response_timezone)
            .isoformat(),
        }

    async def _fetch_forecast(
        self,
        lat: float,
        lon: float,
        days: int,
        location_name: str | None,
    ) -> dict[str, Any]:
        response = await self._request_weather_api(
            {
                "latitude": lat,
                "longitude": lon,
                "daily": [
                    "weather_code",
                    "temperature_2m_min",
                    "temperature_2m_max",
                ],
                "timezone": "auto",
                "forecast_days": days,
            }
        )
        daily = response.Daily()
        dates = self._build_date_series(
            start_timestamp=daily.Time(),
            end_timestamp=daily.TimeEnd(),
            interval_seconds=daily.Interval(),
            response_timezone=self._response_timezone(response.UtcOffsetSeconds()),
        )
        weather_codes = daily.Variables(0).ValuesAsNumpy()
        min_temps = daily.Variables(1).ValuesAsNumpy()
        max_temps = daily.Variables(2).ValuesAsNumpy()

        forecast_items = []
        for index, forecast_date in enumerate(dates[:days]):
            forecast_items.append(
                {
                    "date": forecast_date,
                    "min_temp": float(min_temps[index]),
                    "max_temp": float(max_temps[index]),
                    "condition": self._weather_condition_from_code(
                        weather_codes[index]
                    ),
                }
            )

        return {
            "location_name": location_name,
            "coordinates": {
                "lat": float(response.Latitude()),
                "lon": float(response.Longitude()),
            },
            "days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "forecast": forecast_items,
        }

    async def _request_weather_api(self, params: dict[str, Any]):
        try:
            responses = await asyncio.to_thread(
                self.openmeteo.weather_api,
                WEATHER_API_URL,
                params=params,
            )
            return responses[0]
        except Exception as exc:
            logger.warning("Open-Meteo request failed: %s", exc)
            raise WeatherRepositoryError(
                "Weather provider is currently unavailable.",
                status_code=502,
            ) from exc

    async def _fetch_geocoding(self, city: str) -> dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=settings.WEATHER_TIMEOUT_SECONDS)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    GEOCODING_API_URL,
                    params={
                        "name": city,
                        "count": 1,
                        "language": "de",
                        "format": "json",
                    },
                ) as response:
                    if response.status >= 400:
                        detail = await response.text()
                        raise WeatherRepositoryError(
                            f"Geocoding provider returned {response.status}: {detail}",
                            status_code=502,
                        )

                    payload = await response.json()
        except aiohttp.ClientError as exc:
            logger.warning("Open-Meteo geocoding request failed: %s", exc)
            raise WeatherRepositoryError(
                "Location search is currently unavailable.",
                status_code=502,
            ) from exc

        results = payload.get("results") or []
        if not results:
            raise WeatherRepositoryError(
                f"No coordinates found for '{city}'.",
                status_code=404,
            )

        top_result = results[0]
        return {
            "query": city,
            "result": {
                "name": top_result["name"],
                "country": top_result.get("country"),
                "admin1": top_result.get("admin1"),
                "timezone": top_result.get("timezone"),
                "coordinates": {
                    "lat": top_result["latitude"],
                    "lon": top_result["longitude"],
                },
            },
        }

    async def _resolve_location(
        self,
        lat: float | None,
        lon: float | None,
        city: str | None,
    ) -> tuple[float, float, str | None]:
        if city is not None:
            if lat is not None or lon is not None:
                raise WeatherRepositoryError(
                    "Use either city or lat/lon, not both in the same request.",
                    status_code=422,
                )
            geocoded = await self.geocode_city(city)
            coordinates = geocoded["result"]["coordinates"]
            return coordinates["lat"], coordinates["lon"], geocoded["result"]["name"]

        if lat is None and lon is None:
            return settings.DEFAULT_LAT, settings.DEFAULT_LON, None

        if lat is None or lon is None:
            raise WeatherRepositoryError(
                "Both lat and lon must be provided together.",
                status_code=422,
            )

        return lat, lon, None

    @staticmethod
    def _build_date_series(
        start_timestamp: int,
        end_timestamp: int,
        interval_seconds: int,
        response_timezone: timezone,
    ) -> list[str]:
        dates: list[str] = []
        current_timestamp = start_timestamp
        while current_timestamp < end_timestamp:
            dates.append(
                datetime.fromtimestamp(
                    current_timestamp,
                    tz=timezone.utc,
                )
                .astimezone(response_timezone)
                .date()
                .isoformat()
            )
            current_timestamp += interval_seconds
        return dates

    @staticmethod
    def _weather_condition_from_code(code: float) -> str:
        return WMO_CONDITION_MAP.get(int(round(code)), "Unknown")

    @staticmethod
    def _response_timezone(utc_offset_seconds: int) -> timezone:
        return timezone(timedelta(seconds=utc_offset_seconds))

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
