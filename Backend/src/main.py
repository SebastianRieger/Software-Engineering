import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from fastapi import FastAPI
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api import api_router
from core.config import settings
from core.database import init_db
from core.logging import configure_logging
from core.realtime import realtime_hub
from services.calibration import calibration_service
from services.gesture import gesture_service
from services.led import led_service
from services.musical_audio import musical_audio_service
from services.voice import voice_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    app.state.started_at = datetime.now(timezone.utc)
    realtime_hub.bind_loop(asyncio.get_running_loop())
    calibration_service.startup()
    led_service.startup()
    musical_audio_service.startup()
    voice_service.startup()
    logger.info("Nimrag backend started")
    yield
    calibration_service.shutdown()
    gesture_service.shutdown()
    led_service.shutdown()
    musical_audio_service.shutdown()
    voice_service.shutdown()
    logger.info("Nimrag backend stopped")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Nimrag Smart Mirror Backend API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# WebSocket endpoint for real-time updates


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    event_queue = await realtime_hub.connect(websocket)
    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            event_task = asyncio.create_task(event_queue.get())
            done, pending = await asyncio.wait(
                {receive_task, event_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if receive_task in done:
                data = receive_task.result()
                if data.strip().lower() == "ping":
                    await websocket.send_json(
                        {
                            "eventType": "Pong",
                            "payload": {"message": "pong"},
                        }
                    )
                continue

            event = event_task.result()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        realtime_hub.disconnect(websocket)
        logger.debug("WebSocket connection closed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
