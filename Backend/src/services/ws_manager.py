from typing import List, Dict
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: Dict):
        # Send message to all connected websockets; ignore failures per connection
        living = []
        for ws in list(self.active):
            try:
                await ws.send_json(message)
                living.append(ws)
            except Exception:
                # drop
                try:
                    ws.close()
                except Exception:
                    pass
        self.active = living


# Module-level manager instance
manager = WebSocketManager()
