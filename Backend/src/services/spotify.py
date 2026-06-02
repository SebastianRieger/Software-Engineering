import asyncio
import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import aiohttp

from core.config import settings
from repositories.spotify import SpotifyRepository

logger = logging.getLogger(__name__)

_AUTH_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
_QUEUE_URL = "https://api.spotify.com/v1/me/player/queue"
_SCOPES = "user-read-currently-playing user-read-playback-state"


def _make_timeout() -> aiohttp.ClientTimeout:
    t = settings.SPOTIFY_TIMEOUT_SECONDS
    return aiohttp.ClientTimeout(total=t, connect=t, sock_connect=t, sock_read=t)


class SpotifyServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class SpotifyService:
    def __init__(self, repository: SpotifyRepository | None = None) -> None:
        self.repository = repository or SpotifyRepository()

    def get_auth_url(self) -> str:
        params = urlencode({
            "client_id": settings.SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
            "scope": _SCOPES,
        })
        return f"{_AUTH_URL}?{params}"

    def is_authenticated(self) -> bool:
        return self.repository.get_tokens() is not None

    async def exchange_code(self, code: str) -> None:
        tokens = await self._request_tokens({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        })
        self._persist_tokens(tokens)

    async def get_now_playing(self) -> dict[str, Any]:
        access_token = await self._get_valid_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        async with aiohttp.ClientSession(timeout=_make_timeout()) as session:
            np_data, queue_items = await asyncio.gather(
                self._fetch_now_playing_raw(session, headers),
                self._fetch_queue_raw(session, headers),
            )

        if np_data is None:
            return {"is_playing": False, "track": None, "queue": []}

        item = np_data.get("item")
        if item is None:
            return {"is_playing": False, "track": None, "queue": []}

        return {
            "is_playing": np_data.get("is_playing", False),
            "track": self._parse_track(item, progress_ms=np_data.get("progress_ms", 0)),
            "queue": queue_items,
        }

    async def _fetch_now_playing_raw(
        self, session: aiohttp.ClientSession, headers: dict
    ) -> dict[str, Any] | None:
        async with session.get(_NOW_PLAYING_URL, headers=headers) as response:
            if response.status == 204:
                return None
            if response.status >= 400:
                raise SpotifyServiceError(
                    f"Spotify API Fehler: {response.status}", status_code=502
                )
            return await response.json()

    async def _fetch_queue_raw(
        self, session: aiohttp.ClientSession, headers: dict
    ) -> list[dict[str, Any]]:
        try:
            async with session.get(_QUEUE_URL, headers=headers) as response:
                if response.status != 200:
                    return []
                data = await response.json()
        except Exception:
            return []

        result = []
        for item in (data.get("queue") or [])[:3]:
            if item.get("type") == "track":
                result.append(self._parse_track(item))
        return result

    @staticmethod
    def _parse_track(item: dict[str, Any], progress_ms: int = 0) -> dict[str, Any]:
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        images = item.get("album", {}).get("images", [])
        return {
            "track_name": item["name"],
            "artist": artists,
            "album": item.get("album", {}).get("name", ""),
            "album_cover_url": images[0]["url"] if images else None,
            "progress_ms": progress_ms,
            "duration_ms": item.get("duration_ms", 0),
        }

    async def _get_valid_access_token(self) -> str:
        tokens = self.repository.get_tokens()
        if tokens is None:
            raise SpotifyServiceError(
                "Nicht mit Spotify verbunden.", status_code=401
            )

        expires_at = datetime.fromisoformat(tokens["expires_at"])
        if datetime.now(timezone.utc) >= expires_at:
            tokens = await self._refresh_access_token(tokens["refresh_token"])

        return tokens["access_token"]

    async def _refresh_access_token(self, refresh_token: str) -> dict:
        tokens = await self._request_tokens({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
        if "refresh_token" not in tokens:
            tokens["refresh_token"] = refresh_token
        self._persist_tokens(tokens)
        expires_at = self._compute_expires_at(tokens["expires_in"])
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_at": expires_at.isoformat(),
        }

    async def _request_tokens(self, payload: dict) -> dict:
        credentials = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()
        timeout = _make_timeout()

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                _TOKEN_URL,
                data=payload,
                headers={
                    "Authorization": f"Basic {encoded}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ) as response:
                if response.status >= 400:
                    detail = await response.text()
                    raise SpotifyServiceError(
                        f"Token-Anfrage fehlgeschlagen ({response.status}): {detail}",
                        status_code=502,
                    )
                return await response.json()

    def _persist_tokens(self, tokens: dict) -> None:
        expires_at = self._compute_expires_at(tokens["expires_in"])
        self.repository.save_tokens(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_at=expires_at,
        )

    @staticmethod
    def _compute_expires_at(expires_in: int) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
