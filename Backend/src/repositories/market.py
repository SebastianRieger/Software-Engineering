import json
from datetime import datetime, timezone
from typing import Any

import aiohttp

from core.config import settings
from core.database import get_db_connection
from schemas.market import MarketItem

TWELVE_DATA_API_URL = "https://api.twelvedata.com/quote"


class MarketRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class MarketRepository:
    async def get_market(self, symbols: list[str]) -> dict[str, Any]:
        cache_key = "market:" + ",".join(sorted(symbols))
        cached = self._get_cached_payload(cache_key, settings.MARKET_CACHE_TTL_SECONDS)
        if cached is not None:
            cached["source"] = "cache"
            return cached

        try:
            live_data = await self._fetch_market(symbols)
        except MarketRepositoryError:
            stale_cache = self._get_cached_payload(cache_key, ttl_seconds=None)
            if stale_cache is not None:
                stale_cache["source"] = "cache"
                return stale_cache
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    async def _fetch_market(self, symbols: list[str]) -> dict[str, Any]:
        params = {
            "symbol": ",".join(symbols),
            "apikey": settings.TWELVE_DATA_API_KEY,
        }
        timeout = aiohttp.ClientTimeout(total=settings.WEATHER_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(TWELVE_DATA_API_URL, params=params) as response:
                    if response.status >= 400:
                        raise MarketRepositoryError(
                            f"Twelve Data API returned HTTP {response.status}",
                            status_code=502,
                        )
                    payload = await response.json(content_type=None)
        except TimeoutError as exc:
            raise MarketRepositoryError(
                "Twelve Data API request timed out.", status_code=502
            ) from exc
        except aiohttp.ClientError as exc:
            raise MarketRepositoryError(
                "Twelve Data API is not reachable.", status_code=502
            ) from exc

        if (
            isinstance(payload, dict)
            and payload.get("status") == "error"
            and "symbol" not in payload
        ):
            raise MarketRepositoryError(
                payload.get("message", "Twelve Data API error"),
                status_code=502,
            )

        items = self._parse_items(payload, symbols)
        return {"items": [item.model_dump() for item in items]}

    def _parse_items(self, payload: Any, symbols: list[str]) -> list[MarketItem]:
        items: list[MarketItem] = []
        if len(symbols) == 1:
            item = self._parse_entry(symbols[0], payload)
            if item is not None:
                items.append(item)
        else:
            if isinstance(payload, dict):
                for symbol in symbols:
                    entry = payload.get(symbol)
                    if entry is not None:
                        item = self._parse_entry(symbol, entry)
                        if item is not None:
                            items.append(item)
        return items

    @staticmethod
    def _parse_entry(symbol: str, entry: Any) -> MarketItem | None:
        if not isinstance(entry, dict) or entry.get("status") == "error":
            return None
        try:
            asset_type = "crypto" if "/" in symbol else "stock"
            return MarketItem(
                id=symbol,
                symbol=symbol,
                name=entry.get("name") or symbol,
                price=float(entry.get("close", 0)),
                change=float(entry.get("change", 0)),
                percent_change=float(entry.get("percent_change", 0)),
                currency=entry.get("currency", "USD"),
                asset_type=asset_type,
            )
        except (ValueError, TypeError):
            return None

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
