from fastapi import APIRouter, HTTPException, Query, WebSocket, File, UploadFile
from pydantic import BaseModel
import os
import tempfile

from services.gestures import gesture_service, process_video_file
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


@router.post("/process-video")
async def process_video(
    video_path: str = Query(None, description="Pfad zur MKV/MP4 Datei"),
    file: UploadFile = None,
):
    """
    Verarbeitet ein Video und erkennt Gesten (Kreis, Swipes).
    Entweder video_path (lokal) oder file (Upload) angeben.
    
    Returns: {"gestures": [...], "frames_processed": int}
    """
    if not video_path and not file:
        raise HTTPException(status_code=400, detail="video_path oder file erforderlich")
    
    path_to_process = video_path
    
    # Wenn Upload, temporäre Datei speichern
    if file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mkv") as tmp:
            content = await file.read()
            tmp.write(content)
            path_to_process = tmp.name
    
    try:
        if not os.path.exists(path_to_process):
            raise HTTPException(status_code=404, detail=f"Video nicht gefunden: {path_to_process}")
        
        result = process_video_file(path_to_process)
        return result
    finally:
        # Cleanup temporary file
        if file and os.path.exists(path_to_process):
            try:
                os.remove(path_to_process)
            except Exception:
                pass
