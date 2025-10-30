import paho.mqtt.client as mqtt
from core.config import settings
import json
import asyncio
from typing import Callable, Dict, Any

class MQTTService:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        # Callbacks dictionary for different topics
        self.callbacks: Dict[str, Callable] = {}
        
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        if rc == 0:
            print("Connected to MQTT Broker")
            # Subscribe to all relevant topics
            self.client.subscribe("nimrag/#")
        else:
            print(f"Failed to connect to MQTT Broker with code: {rc}")
            
    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received"""
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        
        # Call the appropriate callback if registered
        if topic in self.callbacks:
            self.callbacks[topic](payload)
            
    async def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        
    def publish(self, topic: str, payload: Any):
        """Publish message to topic"""
        self.client.publish(topic, json.dumps(payload))
        
    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to topic with callback"""
        self.callbacks[topic] = callback
        self.client.subscribe(topic)