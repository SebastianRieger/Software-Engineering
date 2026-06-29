from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from schemas.spotify import NowPlayingResponse, SpotifyAuthStatusResponse
from services.spotify import SpotifyService, SpotifyServiceError

router = APIRouter()


def get_spotify_service() -> SpotifyService:
    return SpotifyService()


@router.get("/auth", response_model=SpotifyAuthStatusResponse)
async def get_auth_status(service: SpotifyService = Depends(get_spotify_service)):
    if service.is_authenticated():
        return {"authenticated": True, "auth_url": None}
    return {"authenticated": False, "auth_url": service.get_auth_url()}


@router.get("/login")
async def spotify_login(service: SpotifyService = Depends(get_spotify_service)):
    return RedirectResponse(url=service.get_auth_url())


@router.get("/callback")
async def spotify_callback(
    code: str,
    service: SpotifyService = Depends(get_spotify_service),
):
    try:
        await service.exchange_code(code)
    except SpotifyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {
        "message": "Spotify erfolgreich verbunden! Du kannst dieses Fenster schließen."
    }


@router.get("/now-playing", response_model=NowPlayingResponse)
async def get_now_playing(service: SpotifyService = Depends(get_spotify_service)):
    try:
        data = await service.get_now_playing()
    except SpotifyServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    if data is None:
        return {"is_playing": False, "track": None}
    return data
