import json
import random
from datetime import datetime, timezone
from typing import Any

import aiohttp

from core.database import get_db_connection

MEME_API_BASE_URL = "https://meme-api.com/gimme"

FETCH_BATCH_SIZE = 15   # fetch 15, pick best N clean ones
MAX_MEMES = 4           # max returned to frontend (enough for the largest view)
MAX_RETRIES = 3
FALLBACK_CACHE_KEY = "meme:latest"


class MemeRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class MemeRepository:
    async def get_memes(self, subreddit: str = "memes", sfw_only: bool = True) -> dict[str, Any]:
        try:
            live_data = await self._fetch_memes(subreddit=subreddit, sfw_only=sfw_only)
        except MemeRepositoryError:
            fallback = self._get_fallback()
            if fallback is not None:
                fallback["source"] = "cache"
                return fallback
            raise

        self._store_fallback(live_data)
        live_data["source"] = "live"
        return live_data

    async def _fetch_memes(self, subreddit: str, sfw_only: bool) -> dict[str, Any]:
        url = f"{MEME_API_BASE_URL}/{subreddit}/{FETCH_BATCH_SIZE}"
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(MAX_RETRIES):
                try:
                    async with session.get(url) as response:
                        if response.status >= 400:
                            raise MemeRepositoryError(
                                f"meme-api.com returned HTTP {response.status}",
                                status_code=502,
                            )
                        payload = await response.json(content_type=None)
                except TimeoutError as exc:
                    if attempt == MAX_RETRIES - 1:
                        raise MemeRepositoryError(
                            "meme-api.com request timed out.", status_code=502
                        ) from exc
                    continue
                except aiohttp.ClientError as exc:
                    raise MemeRepositoryError(
                        "meme-api.com is not reachable.", status_code=502
                    ) from exc

                raw_memes = payload.get("memes", []) if isinstance(payload, dict) else []

                candidates = [
                    m for m in raw_memes
                    if m.get("url")
                    and (not sfw_only or (not m.get("nsfw") and not m.get("spoiler")))
                ]

                if candidates:
                    random.shuffle(candidates)
                    return {"memes": [self._parse_meme(m) for m in candidates[:MAX_MEMES]]}

        raise MemeRepositoryError(
            f"No suitable memes found in r/{subreddit} after {MAX_RETRIES} retries.",
            status_code=503,
        )

    @staticmethod
    def _parse_meme(raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "image_url": raw.get("url", ""),
            "title": raw.get("title", ""),
            "subreddit": raw.get("subreddit", ""),
            "previews": raw.get("preview", []) or [],
        }

    def _get_fallback(self) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM weather_cache WHERE cache_key = ?",
                (FALLBACK_CACHE_KEY,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row["payload"])

    def _store_fallback(self, payload: dict[str, Any]) -> None:
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
                (FALLBACK_CACHE_KEY, json.dumps(payload), now),
            )
