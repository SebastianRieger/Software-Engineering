from fastapi import APIRouter, HTTPException, Query, WebSocket
from pydantic import BaseModel

from services.gestures import gesture_service
from services.ws_manager import manager

router = APIRouter()


class StartResponse(BaseModel):
    status: str


@router.post("/start", response_model=StartResponse)
def start_camera(camera_index: int = Query(0, description="Kameraindex, Standard 0")):
    """Startet die Kameraverarbeitung für Gestenerkennung."""
    try:
        gesture_service.camera_index = camera_index
        gesture_service.start()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "started"}


@router.post("/stop", response_model=StartResponse)
def stop_camera():
    """Stoppt die Kameraverarbeitung."""
    gesture_service.stop()
    return {"status": "stopped"}


@router.get("/status")
def get_status():
    """Gibt den aktuellen Erkennungsstatus und einfache Bewegungsinfos zurück."""
    return gesture_service.get_status()


@router.get("/frame")
def get_frame():
    """Gibt das zuletzt erkannte Vorschaubild als base64-Data-URL zurück."""
    status = gesture_service.get_status()
    frame = status.get("frame")
    if not frame:
        raise HTTPException(status_code=404, detail="Kein Vorschaubild verfügbar")
    return {"image": frame}


@router.post("/capture")
def capture(path: str | None = None):
    """Optional: Speichert das aktuelle Bild auf dem Backend und gibt base64 zurück."""
    img = gesture_service.capture_image(path)
    if img is None:
        raise HTTPException(status_code=404, detail="Kein Bild verfügbar")
    return {"image": img}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that streams gesture events (JSON)."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client may send pings
            msg = await websocket.receive_text()
            # echo or ignore client messages
            await websocket.send_text(f"ok: {msg}")
    except Exception:
        pass
    finally:
        manager.disconnect(websocket)
