# UML Klassendiagramme: Backend & Frontend Struktur

## 1. Backend UML Klassendiagramm

### Beschreibung
Detailliertes UML-Klassendiagramm der Backend-Services mit Attributen und Methoden (kompakt).

```mermaid
classDiagram
    class FastAPIApp {
        -app: FastAPI
        -event_bus: EventBus
        -lifespan: ContextManager
        +start(): void
        +shutdown(): void
        +include_router(): void
    }

    class EventBus {
        -subscribers: Dict
        -queue: AsyncQueue
        +subscribe(event: str, callback): void
        +publish(event: str, data: Any): void
        +notify_all(): void
    }

    class WeatherService {
        -api_key: str
        -base_url: str
        -cache: Dict
        -event_bus: EventBus
        +get_current_weather(): Dict
        +get_forecast(days: int): List
        +start_periodic_updates(): void
        -publish_event(): void
    }

    class LEDService {
        -red_pin: int
        -green_pin: int
        -blue_pin: int
        -current_color: Tuple
        +set_color(rgb: Tuple): void
        +set_brightness(level: float): void
        +fade_to_color(rgb: Tuple, duration: float): void
        +turn_off(): void
    }

    class MQTTService {
        -client: mqtt.Client
        -broker_url: str
        -callbacks: Dict
        +connect(): void
        +disconnect(): void
        +publish(topic: str, payload: Any): void
        +subscribe(topic: str, callback): void
        -on_message_callback(): void
    }

    class GestureService {
        -cap: VideoCapture
        -thread: Thread
        -trajectory: List
        -running: bool
        +start(): void
        +stop(): void
        -detect_gesture(): str
        -calculate_trajectory(): void
    }

    class VoiceService {
        -vosk_model: Model
        -recognizer: Recognizer
        -running: bool
        +start(): void
        +stop(): void
        -recognize_command(): str
        +parse_intent(text: str): Dict
    }

    class MusicService {
        -spotify_client: SpotifyClient
        -current_track: Dict
        +get_current_track(): Dict
        +get_user_playlists(): List
        +play_track(uri: str): void
        +pause(): void
    }

    class CalendarService {
        -google_client: GoogleClient
        -user_id: str
        +get_events(days: int): List
        +add_event(event: Dict): void
        +delete_event(id: str): void
    }

    class WebSocketManager {
        -connections: Set
        -broadcast_queue: Queue
        +register(websocket: WebSocket): void
        +unregister(websocket: WebSocket): void
        +broadcast(message: str): void
        -encode_message(): str
    }

    class APIRouter {
        -prefix: str
        -tags: List
        +get_weather(): Dict
        +post_led_control(color: str): Dict
        +get_smart_home(): List
        +get_events(): List
    }

    class Config {
        -project_name: str
        -api_version: str
        -database_url: str
        -mqtt_broker: str
        -weather_api_key: str
        +load_config(): void
        +validate(): bool
    }

    %% Relationships
    FastAPIApp --> EventBus
    FastAPIApp --> APIRouter
    FastAPIApp --> WebSocketManager
    
    WeatherService --> EventBus
    LEDService --> EventBus
    MQTTService --> EventBus
    GestureService --> EventBus
    VoiceService --> EventBus
    MusicService --> EventBus
    CalendarService --> EventBus
    
    APIRouter --> WeatherService
    APIRouter --> LEDService
    APIRouter --> MQTTService
    APIRouter --> CalendarService
    APIRouter --> MusicService
    
    WebSocketManager --> EventBus
    
    FastAPIApp --> Config
    WeatherService --> Config
    MQTTService --> Config
```

### Komponenten-Details

**FastAPIApp**
```
- Zentrale Anwendung
- Lifecycle Management
- Router-Integration
```

**EventBus**
```
- Pub/Sub Pattern
- Event-Verwaltung
- Async Queue
```

**Services (7 Stück)**
```
- WeatherService: OpenWeatherMap Integration
- LEDService: GPIO/PWM Control
- MQTTService: IoT Device Communication
- GestureService: MediaPipe Tracking
- VoiceService: Vosk ASR
- MusicService: Spotify API
- CalendarService: Google Calendar
```

**WebSocketManager**
```
- Connection Management
- Message Broadcasting
- Event Distribution
```

---

## 2. Frontend UML Klassendiagramm

### Beschreibung
UML-Klassendiagramm der Vue 3 Frontend-Struktur (kompakt).

```mermaid
classDiagram
    class App {
        +setup(): void
        +render(): void
    }

    class Router {
        -routes: Array
        -current: string
        +push(path: string): void
        +back(): void
    }

    class Store {
        -state: Object
        -mutations: Object
        -actions: Object
        +commit(type: string, payload: Any): void
        +dispatch(type: string, payload: Any): void
    }

    class WeatherModule {
        -state: Object
        -mutations: Object
        -actions: Object
        +setWeatherData(data: Object): void
        +fetchWeather(): void
        -api_call(): void
    }

    class LEDModule {
        -state: Object
        -mutations: Object
        -actions: Object
        +setLEDColor(rgb: Array): void
        +updateBrightness(level: number): void
        +sendCommand(): void
    }

    class SmartHomeModule {
        -state: Object
        -mutations: Object
        -actions: Object
        +updateDeviceState(id: string, state: Object): void
        +loadDevices(): void
        +controlDevice(id: string, command: Object): void
    }

    class WeatherWidget {
        -props: Object
        -data: Object
        +setup(): void
        +render(): VNode
        -formatTemperature(): string
        -getWeatherIcon(): string
    }

    class LEDWidget {
        -props: Object
        -data: Object
        +setup(): void
        +render(): VNode
        +onColorChange(color: string): void
        +onBrightnessChange(level: number): void
    }

    class SmartHomeWidget {
        -props: Object
        -devices: Array
        +setup(): void
        +render(): VNode
        +toggleDevice(id: string): void
        +updateDeviceState(): void
    }

    class TimeWidget {
        -props: Object
        -currentTime: Date
        +setup(): void
        +render(): VNode
        -updateTime(): void
    }

    class CalendarWidget {
        -props: Object
        -events: Array
        +setup(): void
        +render(): VNode
        +getEvents(): Array
        -formatDate(): string
    }

    class useWebSocket {
        -socket: WebSocket
        -connected: bool
        -reconnect_interval: number
        +connect(): void
        +disconnect(): void
        +send(message: Object): void
        +on_message(callback): void
        -handle_reconnect(): void
    }

    class useNotification {
        -notifications: Array
        +show(message: string, type: string): void
        +dismiss(id: string): void
        -auto_dismiss(): void
    }

    class useTheme {
        -current_theme: string
        -themes: Object
        +toggle_theme(): void
        +apply_theme(name: string): void
        -persist_theme(): void
    }

    class HTTPClient {
        -baseURL: string
        -timeout: number
        -headers: Object
        +get(url: string): Promise
        +post(url: string, data: Object): Promise
        +put(url: string, data: Object): Promise
        +delete(url: string): Promise
        +interceptor(): void
    }

    class StorageService {
        -storage: Storage
        +get(key: string): Any
        +set(key: string, value: Any): void
        +remove(key: string): void
        +clear(): void
    }

    class FormatterService {
        +formatDate(date: Date): string
        +formatTemperature(temp: number): string
        +formatTime(time: Date): string
        +formatDuration(ms: number): string
    }

    %% Relationships
    App --> Router
    App --> Store
    
    Store --> WeatherModule
    Store --> LEDModule
    Store --> SmartHomeModule
    
    Router --> WeatherWidget
    Router --> LEDWidget
    Router --> SmartHomeWidget
    Router --> TimeWidget
    Router --> CalendarWidget
    
    WeatherWidget --> WeatherModule
    WeatherWidget --> FormatterService
    WeatherWidget --> useNotification
    
    LEDWidget --> LEDModule
    LEDWidget --> HTTPClient
    LEDWidget --> useNotification
    
    SmartHomeWidget --> SmartHomeModule
    SmartHomeWidget --> HTTPClient
    SmartHomeWidget --> useNotification
    
    CalendarWidget --> useWebSocket
    CalendarWidget --> FormatterService
    
    TimeWidget --> FormatterService
    
    useWebSocket --> Store
    useNotification --> StorageService
    useTheme --> StorageService
    
    HTTPClient --> StorageService
```

### Komponenten-Details

**App & Router**
```
- Root Component
- Navigation Management
```

**Store (Vuex)**
```
- Global State Management
- 3 Modules (Weather, LED, SmartHome)
```

**Widgets (5 Stück)**
```
- WeatherWidget: Temperature, Forecast
- LEDWidget: Color, Brightness Control
- SmartHomeWidget: Device Control
- TimeWidget: Current Time Display
- CalendarWidget: Upcoming Events
```

**Composables (3 Stück)**
```
- useWebSocket: Real-time Communication
- useNotification: Alert Management
- useTheme: Theme Switching
```

**Services (3 Stück)**
```
- HTTPClient: API Communication
- StorageService: LocalStorage Wrapper
- FormatterService: Data Formatting
```

---

## 3. Beziehungen zwischen Backend & Frontend

```mermaid
classDiagram
    class "Backend\nFastAPI" {
        +/api/v1/weather: GET
        +/api/v1/led/control: POST
        +/api/v1/smart-home: GET/POST
        +/ws: WebSocket
    }

    class "Frontend\nVue 3" {
        +WeatherWidget
        +LEDWidget
        +SmartHomeWidget
    }

    class HTTPRequest {
        -method: str
        -url: str
        -headers: dict
        -body: dict
    }

    class WebSocketMessage {
        -type: str
        -data: dict
        -timestamp: int
    }

    %% Relationships
    "Frontend\nVue 3" -->|HTTP REST| "Backend\nFastAPI"
    "Frontend\nVue 3" -->|WebSocket Events| "Backend\nFastAPI"
    HTTPRequest -.->|used by| "Frontend\nVue 3"
    WebSocketMessage -.->|used by| "Frontend\nVue 3"
```

---

## 4. Data Models (Wichtige DTOs)

### Backend DTO Models

```mermaid
classDiagram
    class WeatherDTO {
        +temperature: float
        +humidity: int
        +condition: string
        +wind_speed: float
        +timestamp: datetime
    }

    class LEDCommandDTO {
        +color: string
        +brightness: float
        +duration: float
    }

    class DeviceDTO {
        +device_id: string
        +device_type: string
        +state: dict
        +last_updated: datetime
    }

    class EventDTO {
        +event_type: string
        +timestamp: datetime
        +payload: dict
        +metadata: dict
    }

    class UserCommandDTO {
        +command_type: string
        +parameters: dict
        +user_id: string
        +timestamp: datetime
    }
```

### Frontend State Models

```mermaid
classDiagram
    class WeatherState {
        +current_temp: number
        +humidity: number
        +condition: string
        +forecast: Array
        +last_updated: Date
    }

    class LEDState {
        +color: string
        +brightness: number
        +is_on: boolean
        +current_effect: string
    }

    class SmartHomeState {
        +devices: Array
        +loading: boolean
        +error: string
        +last_sync: Date
    }

    class UIState {
        +current_theme: string
        +notifications: Array
        +loading_states: dict
        +error_messages: dict
    }
```

---

## 5. Sequenz bei API-Aufruf (kompakt)

```mermaid
sequenceDiagram
    participant Frontend as Vue<br/>Component
    participant Store as Vuex<br/>Store
    participant HTTP as HTTP<br/>Client
    participant Backend as FastAPI<br/>Endpoint
    participant Service as Business<br/>Service
    participant Database as DB/Cache

    Frontend->>Store: commit('setLoading')
    Frontend->>HTTP: GET /api/v1/weather
    HTTP->>Backend: HTTP Request
    Backend->>Service: get_weather()
    Service->>Database: query_cache()
    alt Cache Hit
        Database-->>Service: cached_data
    else Cache Miss
        Service->>Database: api_call()
        Database-->>Service: fresh_data
    end
    Service-->>Backend: WeatherDTO
    Backend-->>HTTP: 200 OK + JSON
    HTTP-->>Store: commit('setWeatherData', data)
    Store-->>Frontend: UI Updates
```

---

## 6. Übersicht: Klassen nach Schicht

```
BACKEND (Python):
├─ Framework Layer
│  └─ FastAPIApp, APIRouter, Config
├─ Service Layer
│  ├─ WeatherService
│  ├─ LEDService
│  ├─ MQTTService
│  ├─ GestureService
│  ├─ VoiceService
│  ├─ MusicService
│  └─ CalendarService
├─ Event System
│  ├─ EventBus
│  └─ WebSocketManager
└─ Data Models
   └─ DTOs (WeatherDTO, LEDCommandDTO, etc.)

FRONTEND (Vue 3 + TypeScript):
├─ Core
│  ├─ App
│  ├─ Router
│  └─ Store (Vuex)
├─ Components/Widgets
│  ├─ WeatherWidget
│  ├─ LEDWidget
│  ├─ SmartHomeWidget
│  ├─ TimeWidget
│  └─ CalendarWidget
├─ Composables
│  ├─ useWebSocket
│  ├─ useNotification
│  └─ useTheme
├─ Services
│  ├─ HTTPClient
│  ├─ StorageService
│  └─ FormatterService
└─ State Modules
   ├─ WeatherModule
   ├─ LEDModule
   └─ SmartHomeModule
```

---

## 7. Wichtige Methoden Pro Klasse (Quick Reference)

```
WeatherService:
├─ get_current_weather() → Dict
├─ get_forecast(days) → List
├─ start_periodic_updates() → void
└─ publish_event() → void

LEDService:
├─ set_color(rgb) → void
├─ set_brightness(level) → void
├─ fade_to_color(rgb, duration) → void
└─ turn_off() → void

MQTTService:
├─ connect() → void
├─ publish(topic, payload) → void
├─ subscribe(topic, callback) → void
└─ disconnect() → void

GestureService:
├─ start() → void
├─ detect_gesture() → str
├─ calculate_trajectory() → void
└─ stop() → void

EventBus:
├─ subscribe(event, callback) → void
├─ publish(event, data) → void
└─ notify_all() → void

WebSocketManager:
├─ register(websocket) → void
├─ broadcast(message) → void
├─ unregister(websocket) → void
└─ encode_message() → str

─────────────────────────────────

WeatherWidget:
├─ setup() → void
├─ render() → VNode
├─ formatTemperature() → string
└─ getWeatherIcon() → string

LEDWidget:
├─ setup() → void
├─ onColorChange(color) → void
├─ onBrightnessChange(level) → void
└─ render() → VNode

SmartHomeWidget:
├─ toggleDevice(id) → void
├─ updateDeviceState() → void
├─ setup() → void
└─ render() → VNode

useWebSocket:
├─ connect() → void
├─ send(message) → void
├─ on_message(callback) → void
└─ disconnect() → void

HTTPClient:
├─ get(url) → Promise
├─ post(url, data) → Promise
├─ put(url, data) → Promise
├─ delete(url) → Promise
└─ interceptor() → void

Store:
├─ commit(type, payload) → void
├─ dispatch(type, payload) → void
├─ getters → computed
└─ state → reactive
```

---

## 8. Zusammenfassung: Klassen-Struktur

| Layer | Backend | Frontend |
|-------|---------|----------|
| **Framework** | FastAPIApp, APIRouter | App, Router |
| **State** | Config | Store + Modules |
| **Services** | 7 Services | HTTPClient, StorageService |
| **Communication** | EventBus, WebSocketManager | useWebSocket, HTTPClient |
| **UI** | - | 5 Widgets |
| **Utilities** | - | Composables, FormatterService |

---

**Status**: ✅ Kompakte UML-Diagramme ready zum Verwenden  
**Format**: Mermaid Klassendiagramme  
**Detaillierungsgrad**: Kurz & prägnant ohne zu ausführlich

