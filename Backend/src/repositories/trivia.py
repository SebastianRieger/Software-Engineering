import base64
import json
import random
from datetime import date, datetime, timezone
from typing import Any

import aiohttp

from core.database import get_db_connection

OPENTDB_API_URL = "https://opentdb.com/api.php"


class TriviaRepositoryError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class TriviaRepository:
    async def get_question(self) -> dict[str, Any]:
        today = date.today().isoformat()
        cache_key = f"trivia:{today}"

        cached = self._get_cached_payload(cache_key)
        if cached is not None:
            cached["source"] = "cache"
            return cached

        try:
            live_data = await self._fetch_question()
        except TriviaRepositoryError:
            stale = self._get_any_cached_trivia()
            if stale is not None:
                stale["source"] = "cache"
                return stale
            raise

        self._store_payload(cache_key, live_data)
        live_data["source"] = "live"
        return live_data

    async def _fetch_question(self) -> dict[str, Any]:
        params = {"amount": "1", "encode": "base64"}
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(OPENTDB_API_URL, params=params) as response:
                    if response.status >= 400:
                        raise TriviaRepositoryError(
                            f"OpenTDB API returned HTTP {response.status}",
                            status_code=502,
                        )
                    payload = await response.json(content_type=None)
        except TimeoutError as exc:
            raise TriviaRepositoryError(
                "OpenTDB API request timed out.", status_code=502
            ) from exc
        except aiohttp.ClientError as exc:
            raise TriviaRepositoryError(
                "OpenTDB API is not reachable.", status_code=502
            ) from exc

        response_code = payload.get("response_code", -1)
        if response_code != 0:
            raise TriviaRepositoryError(
                f"OpenTDB response_code={response_code}: no results available.",
                status_code=503,
            )

        results = payload.get("results", [])
        if not results:
            raise TriviaRepositoryError("OpenTDB returned no results.", status_code=502)

        raw = results[0]

        def decode(s: str) -> str:
            return base64.b64decode(s).decode("utf-8")

        question = decode(raw["question"])
        correct_answer = decode(raw["correct_answer"])
        incorrect_answers = [decode(a) for a in raw.get("incorrect_answers", [])]
        category = decode(raw["category"])
        difficulty = decode(raw["difficulty"])
        qtype = decode(raw["type"])

        answers = [correct_answer, *incorrect_answers]
        random.shuffle(answers)

        return {
            "question": question,
            "correct_answer": correct_answer,
            "answers": answers,
            "category": category,
            "difficulty": difficulty,
            "type": qtype,
        }

    def _get_cached_payload(self, cache_key: str) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                "SELECT payload FROM weather_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row["payload"])

    def _get_any_cached_trivia(self) -> dict[str, Any] | None:
        with get_db_connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM weather_cache
                WHERE cache_key LIKE 'trivia:%'
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
