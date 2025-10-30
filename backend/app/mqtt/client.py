"""Minimal MQTT client scaffold (async)."""
import asyncio


class MQTTClient:
    def __init__(self, broker_url: str = "localhost", port: int = 1883):
        self.broker_url = broker_url
        self.port = port
        self._running = False

    async def start(self):
        # TODO: use asyncio-mqtt or other lib to connect
        self._running = True
        while self._running:
            await asyncio.sleep(1)

    async def stop(self):
        self._running = False


mqtt_client = MQTTClient()
