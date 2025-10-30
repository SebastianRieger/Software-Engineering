from typing import Dict


class WebSocketManager:
    def __init__(self):
        self.active: Dict[str, object] = {}

    def connect(self, client_id: str, ws):
        self.active[client_id] = ws

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)

    async def broadcast(self, message: dict):
        # iterate and send to connected websockets
        for _id, ws in list(self.active.items()):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(_id)


ws_manager = WebSocketManager()
