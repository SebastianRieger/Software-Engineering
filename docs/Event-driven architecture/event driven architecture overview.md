
# Event-Driven Architektur für das Nimrag Smart Mirror Projekt

Basierend auf der Analyse der Projektdokumentation wurde eine umfassende event-getriebene Architektur entwickelt, die das Python FastAPI Backend optimal mit dem Vue.js Frontend vereint und alle wichtigen Aspekte des Smart Mirror Systems abdeckt.[^1][^2]

## Architekturübersicht

Die event-getriebene Architektur ist in fünf Hauptschichten organisiert, die über verschiedene Event-Kommunikationskanäle miteinander verbunden sind:

### Frontend Layer (Vue 3 + TypeScript)

Das Vue.js Frontend fungiert als **Event Consumer und Producer**. Die Hauptkomponenten sind:[^3][^4]

**Vue Components (Widget-Komponenten)**: Zeit/Datum, Wetter, Kalender, LED-Steuerung, Smart Home Kontrolle, Musik-Player und Gesten-Feedback. Diese Komponenten reagieren auf eingehende Events und emittieren Benutzeraktionen als Events.[^3]

**Vuex Store (State Management)**: Der zentrale State Container empfängt Events über WebSocket, aktualisiert den globalen State durch Mutations und löst Actions für asynchrone Event-Verarbeitung aus. Jedes Widget-Feature erhält ein eigenes Vuex-Modul für klare Separation.[^4][^5]

**Event Listeners (WebSocket Client)**: Ein wiederverwendbarer Composable `useWebSocket()` stellt die bidirektionale Verbindung zum Backend her. Bei eingehenden Events werden diese automatisch an die entsprechenden Vuex Mutations weitergeleitet.[^5][^3]

### Event Bus / Message Broker Layer

Diese zentrale Schicht orchestriert die gesamte Event-Kommunikation:

**FastAPI WebSocket Server**: Ermöglicht bidirektionale Echtzeit-Kommunikation zwischen Frontend und Backend. Events werden als JSON-Nachrichten mit standardisiertem Format übertragen: `{eventType, timestamp, payload, metadata}`.[^6][^7]

**MQTT Broker (Mosquitto)**: Verarbeitet die IoT-Kommunikation mit Smart Home Geräten und LED-Steuerung. Topic-Struktur: `nimrag/smarthome/`, `nimrag/led/`, `nimrag/system/`. Unterstützt QoS-Level 0-2 für unterschiedliche Zuverlässigkeitsanforderungen.[^7][^8][^9][^10]

**Event Bus (In-Memory)**: Ein Python-basierter In-Memory Event Bus implementiert das Observer Pattern für schnelle Backend-interne Kommunikation. Verwendet AsyncIO für non-blocking Event Processing.[^11][^12]

**Redis Pub/Sub (Optional)**: Bei Multi-Instance Deployments synchronisiert Redis Events zwischen mehreren FastAPI-Instanzen.[^13][^10]

### Backend Layer (FastAPI + Python)

**FastAPI spielt die zentrale Rolle als Event Orchestrator**:[^6][^7]

**Lifespan Events**: FastAPI's `lifespan` Context Manager verwaltet den gesamten Application Lifecycle. Beim Startup werden alle Services initialisiert (MQTT-Client, Voice Service, Gesture Service) und ein `ApplicationStarted` Event publiziert. Beim Shutdown erfolgt ein geordnetes Cleanup aller Ressourcen.[^14][^15][^16]

**REST API Endpoints**: HTTP-Endpoints triggern Events (z.B. `POST /api/led/control` → `LEDControlCommand` Event). Sie implementieren das Command-Pattern der CQRS-Architektur.[^17][^18][^7][^6]

**WebSocket Endpoints**: Der `/ws` Endpoint verwaltet persistente Verbindungen zu Frontend-Clients. Ein Event Handler subscribt relevante Events und sendet diese über WebSocket an verbundene Clients.[^19][^6]

**Event Publishers**: Services können Events über den zentralen Event Bus publizieren: `await event_bus.publish("WeatherDataUpdated", weather_data)`.[^12][^11]

**Event Subscribers/Handlers**: Decorator-basierte oder Callback-basierte Handler reagieren auf spezifische Event-Typen. Beispiel: `event_bus.subscribe("GestureDetected", gesture_handler)`.[^9][^12]

**Dependency Injection System**: FastAPI's DI ermöglicht Injection des Event Bus in alle Services und Endpoints. Der Event Bus wird als Singleton über `Depends(get_event_bus)` injiziert.[^20][^21]

**Background Tasks**: Async Tasks für lange laufende Prozesse wie periodische API-Abfragen oder Video-Verarbeitung. FastAPI's `BackgroundTasks` für einfache Fire-and-Forget Tasks, AsyncIO `create_task()` für komplexere Event-Processing-Workflows.[^22][^23][^24]

### Domain Services Layer

Spezialisierte Services behandeln spezifische Fachlogik und emittieren Domain Events:[^25][^26]

**Widget Service**: Verwaltet Wetter-, Kalender- und Zeit-Daten. Läuft als periodische Background Task und publiziert `WeatherDataUpdated`, `CalendarEventAdded` Events.[^7]

**Voice Service (Vosk ASR)**: Verarbeitet Mikrofon-Input offline, erkennt Sprachbefehle und emittiert `VoiceCommandDetected` Events.[^2][^1]

**Gesture Service (MediaPipe)**: Analysiert Kamera-Stream in Echtzeit, erkennt Handgesten und publiziert `GestureDetected` Events.[^1][^2]

**LED Control Service**: Steuert RGB-LEDs über GPIO/PWM, subscribt zu Wetter- und System-Events für automatische Anpassungen, emittiert `LEDStateChanged` Events.[^2][^1]

**Smart Home Service (MQTT Client)**: Integriert mit fastapi-mqtt, empfängt MQTT-Messages von IoT-Geräten, konvertiert sie zu internen Events (`SmartHomeDeviceStateChanged`), und publiziert interne Events zurück zu MQTT-Topics.[^8][^9]

**Music Service**: Integration mit Spotify API für Wiedergabe-Informationen.

**Configuration Service**: Verwaltet Widget-Konfigurationen und emittiert `WidgetConfigurationChanged` Events.

### External Systems \& Hardware

**External APIs**: Weather API (OpenWeatherMap), Google Calendar API, Spotify Web API. Alle Aufrufe erfolgen asynchron mit httpx.[^1]

**Smart Home Devices**: Kommunikation über MQTT mit Geräten wie Philips Hue, Home Assistant, Zigbee-Geräten.[^2]

**Hardware**: USB-Kamera für Gestenerkennung, Mikrofon für Spracherkennung, GPIO-Pins für LED-Steuerung.[^1][^2]

## Event-Entitäten und Kommunikation

### Domain Events (Fachliche Events)

**WeatherDataUpdated**[^26][^25]

- Payload: `{temperature, humidity, condition, forecast, timestamp}`
- Producer: Weather Service
- Consumers: Weather Widget (Frontend), LED Control Service

**VoiceCommandDetected**[^25]

- Payload: `{command, confidence, parameters, userId}`
- Producer: Voice Service (Vosk)
- Consumers: Command Router Service

**GestureDetected**[^25]

- Payload: `{gestureType, coordinates, confidence, timestamp}`
- Producer: Gesture Service (MediaPipe)
- Consumers: UI Navigation Service, Widget Controller

**LEDStateChanged**[^25]

- Payload: `{brightness, color, pattern, zone}`
- Producer: LED Control Service
- Consumers: LED Widget (Frontend), Smart Home Service

**SmartHomeDeviceStateChanged**[^25]

- Payload: `{deviceId, deviceType, state, attributes}`
- Producer: Smart Home Service (MQTT Client)
- Consumers: Smart Home Widget, Automation Service


### System Events (Technische Events)

**ApplicationStarted / ApplicationShutdown**: Lifecycle Events für Service-Initialisierung und Cleanup.[^15][^14]

**ErrorOccurred**: Zentralisierte Error-Handling mit strukturiertem Logging.[^26]

**ConnectionEstablished / ConnectionLost**: WebSocket und MQTT Connection Monitoring.

## Kommunikationspatterns

### Event Flow Beispiel: Wetter Update

1. **Weather Service** führt periodischen Task alle 10 Minuten aus (AsyncIO Task)[^22]
2. HTTP Request zu OpenWeatherMap API (async mit httpx)
3. **Event Publishing**: `await event_bus.publish("WeatherDataUpdated", weather_data)`
4. **Event Bus** notifiziert alle Subscriber:
    - WebSocket Handler → sendet zu allen verbundenen Frontend-Clients[^6]
    - LED Control Service → passt LED-Farbe basierend auf Wetterlage an
    - Cache Service → speichert für Offline-Modus
5. **Vue Frontend** empfängt via WebSocket → Vuex Mutation → State Update → UI Re-Render[^4][^3]

### Event Flow Beispiel: Smart Home Integration

1. **Philips Hue Lampe** ändert Status → MQTT Message zu `nimrag/smarthome/devices/hue-1/state`[^8][^7]
2. **MQTT Service** empfängt Message via `@mqtt.on_message()` Decorator[^9]
3. Konvertierung zu internem Event: `event_bus.publish("SmartHomeDeviceStateChanged", device_data)`
4. **Event Bus** distribuiert an:
    - WebSocket Handler → Frontend Update
    - Smart Home Widget → Display-Aktualisierung
5. **Vue Frontend** zeigt neuen Status in Echtzeit an

## FastAPI's Rolle in der Event-Architektur

FastAPI ist das zentrale Nervensystem der Event-Architektur und übernimmt mehrere kritische Rollen:[^7][^6]

### 1. Application Lifecycle Management

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    mqtt_service = MQTTService(event_bus)
    await mqtt_service.connect()
    
    weather_service = WeatherService(event_bus)
    asyncio.create_task(weather_service.start_periodic_updates())
    
    await event_bus.publish("ApplicationStarted", {...})
    
    yield
    
    # SHUTDOWN
    await event_bus.publish("ApplicationShutdown", {...})
    await mqtt_service.disconnect()

app = FastAPI(lifespan=lifespan)
```

Der Lifespan-Context startet alle Event-basierten Services beim Application Start und führt geordnetes Cleanup beim Shutdown durch.[^16][^14][^15]

### 2. Event Bus Hosting \& Dependency Injection

```python
event_bus = EventBus()  # Singleton

def get_event_bus() -> EventBus:
    return event_bus

@app.post("/api/led/control")
async def control_led(
    color: str,
    brightness: int,
    event_bus: EventBus = Depends(get_event_bus)
):
    await event_bus.publish("LEDControlCommand", {
        "color": color,
        "brightness": brightness
    })
    return {"status": "command_sent"}
```

Der Event Bus wird als Dependency in alle Endpoints und Services injiziert. FastAPI's DI-System ermöglicht einfaches Testing durch Mocking.[^21][^27][^20]

### 3. WebSocket Server für Real-time Communication

```python
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    event_bus: EventBus = Depends(get_event_bus)
):
    await websocket.accept()
    
    async def send_to_client(event_data: dict):
        await websocket.send_json(event_data)
    
    event_bus.subscribe("WeatherDataUpdated", send_to_client)
    event_bus.subscribe("GestureDetected", send_to_client)
    
    try:
        while True:
            data = await websocket.receive_json()
            await event_bus.publish(f"Frontend{data['eventType']}", data)
    except WebSocketDisconnect:
        pass
```

FastAPI's native WebSocket-Support ermöglicht bidirektionale Event-Kommunikation mit dem Frontend.[^19][^3][^6]

### 4. Background Task Management

**Periodic Tasks** für kontinuierliche Event-Generation:

```python
class WeatherService:
    async def start_periodic_updates(self):
        while self.running:
            weather_data = await self.fetch_weather()
            await self.event_bus.publish("WeatherDataUpdated", weather_data)
            await asyncio.sleep(600)  # 10 Minuten
```

**Fire-and-Forget Tasks** via `BackgroundTasks`:[^28][^23][^29]

```python
@app.post("/send-notification")
async def send_notification(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email, ...)
    return {"status": "queued"}
```


### 5. MQTT Integration

```python
from fastapi_mqtt import FastMQTT, MQTTConfig

mqtt_client = FastMQTT(config=MQTTConfig(host="localhost", port=1883))

@mqtt_client.on_message()
async def on_mqtt_message(client, topic, payload, qos, properties):
    event_data = json.loads(payload.decode())
    await event_bus.publish(f"MQTT_{topic.split('/')[-1]}", event_data)

# Publiziere interne Events zu MQTT
async def publish_led_event(event_data: dict):
    mqtt_client.publish("nimrag/led/state", json.dumps(event_data), qos=1)

event_bus.subscribe("LEDStateChanged", publish_led_event)
```

FastAPI-MQTT ermöglicht deklarative Event-Handler mit Decorators und automatische Reconnection.[^8][^9]

## Technologie-Stack und Tools

### Frontend

- **Vue 3** (3.x): Reactive UI Framework mit Composition API[^2][^1]
- **Vuex 4**: State Management für Event-basierte Updates[^4]
- **TypeScript**: Type-safe Event Definitions und Payloads[^1][^2]
- **Vite**: Fast Development Server mit HMR[^2][^1]
- **WebSocket API**: Native Browser-Support, keine zusätzlichen Libraries nötig[^5][^3]


### Backend (Python)

- **FastAPI** (0.104+): Async-first Web Framework[^6][^7][^1]
- **Uvicorn** (0.24+): Production ASGI Server mit WebSocket-Support
- **Pydantic** (2.x): Event Schema Validation und Type-Safety
- **AsyncIO**: Native async/await für Event Processing[^22]


### Message Broker

- **Mosquitto** (2.0+): MQTT Broker für IoT-Kommunikation[^7][^8]
- **fastapi-mqtt** (2.2.0): MQTT Integration für FastAPI[^9][^8]
- **Redis** (7.x, optional): Distributed Event Bus für Multi-Instance Deployments[^10][^13]


### Domain Services

- **Vosk** (0.3.45): Offline Speech Recognition[^1][^2]
- **MediaPipe** (0.10+): Gesture Recognition[^2][^1]
- **OpenCV** (4.8+): Computer Vision Backend
- **gpiozero** (2.0): GPIO Control für LEDs[^1]
- **httpx** (0.25+): Async HTTP Client für External APIs


### Development \& Testing

- **pytest** + **pytest-asyncio**: Async Testing Framework
- **Docker** + **Docker Compose**: Containerization (Backend, Mosquitto, Redis)
- **mypy**: Static Type Checking
- **ruff**: Fast Python Linter


## Vorteile dieser Event-Driven Architektur

**Loose Coupling**: Services kennen sich nicht direkt, nur über Events. Neue Features können einfach durch Subscription zu bestehenden Events hinzugefügt werden.[^30][^31][^32]

**Scalability**: Horizontale Skalierung durch Redis Pub/Sub. Services können unabhängig voneinander skaliert werden.[^32][^33][^13]

**Real-time Responsiveness**: WebSocket + MQTT ermöglichen Echtzeit-Updates im Frontend. Kein Polling notwendig.[^3][^5][^4]

**Fault Tolerance**: Wenn ein Service ausfällt, können andere weiterlaufen. MQTT QoS-Levels garantieren Message Delivery.[^33][^34][^32][^10]

**Testability**: Event Bus kann einfach gemockt werden. Unit Tests können Events triggern und Reaktionen überprüfen.

**Modularity**: Klare Trennung zwischen Domain Logic (Services), Event Transport (Broker) und Presentation (Frontend).[^31][^30][^32]

**Type Safety**: TypeScript im Frontend und Pydantic im Backend reduzieren Runtime-Errors erheblich.

**Offline Capability**: Events können in SQLite gespeichert (Event Sourcing) und bei Wiederverbindung replayed werden.[^35][^17]

## Implementierungsdetails

Alle drei erstellten Dokumente enthalten detaillierte Implementierungsbeispiele:

**nimrag_architecture.txt**: Visuelle Darstellung der 5-Schichten-Architektur mit allen Komponenten und Kommunikationsflüssen.

**event_architecture_detailed.txt**: Vollständige Event-Definitionen, Event Bus Implementierung, FastAPI Code-Beispiele, Vue.js WebSocket Integration und konkrete Event Flow Szenarien.

**technology_stack_guide.txt**: Alle benötigten Packages mit Versionen, Installation-Guides, Docker-Setup, requirements.txt und package.json Konfigurationen.

Diese event-getriebene Architektur bietet eine solide, skalierbare und wartbare Basis für das Nimrag Smart Mirror Projekt, die alle Anforderungen aus der SRS-Dokumentation erfüllt und moderne Best Practices für Event-Driven Architecture, CQRS und Microservices-Patterns implementiert.
