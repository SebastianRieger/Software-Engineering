from pydantic import BaseModel


class SpotifyTrack(BaseModel):
    track_name: str
    artist: str
    album: str
    album_cover_url: str | None = None
    progress_ms: int
    duration_ms: int


class NowPlayingResponse(BaseModel):
    is_playing: bool
    track: SpotifyTrack | None = None
    queue: list[SpotifyTrack] = []


class SpotifyAuthStatusResponse(BaseModel):
    authenticated: bool
    auth_url: str | None = None
