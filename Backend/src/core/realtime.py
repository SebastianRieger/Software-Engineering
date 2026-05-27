import asyncio
from concurrent.futures import Future
from collections.abc import Awaitable
from typing import Any

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, asyncio.Queue[dict[str, Any]]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> asyncio.Queue[dict[str, Any]]:
        await websocket.accept()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connections[websocket] = queue
        return queue

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale_connections: list[WebSocket] = []

        for websocket, queue in list(self._connections.items()):
            try:
                queue.put_nowait(message)
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            self.disconnect(websocket)

    def publish_from_thread(
        self,
        message: dict[str, Any],
    ) -> Future[Any] | Awaitable[Any] | None:
        if self._loop is None or self._loop.is_closed():
            return None

        return asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)


realtime_hub = RealtimeHub()
