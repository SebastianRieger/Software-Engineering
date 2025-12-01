# Abschnitt 8: Komponentendiagramme und Paketdiagramme

## 8.1 Überblick

Dieses Kapitel präsentiert die Komponenten- und Paketdiagramme des Nimrag Smart Mirror Systems. Diese Diagramme zeigen die logische und physische Struktur der Anwendung sowie die Abhängigkeiten zwischen den verschiedenen Komponenten.

### Struktur dieses Kapitels

- **8.2**: Gesamtkomponentendiagramm der Anwendung
- **8.3**: Backend-Komponenten detailliert
- **8.4**: Frontend-Komponenten detailliert
- **8.5**: Paketdiagramm der Backend-Architektur
- **8.6**: Paketdiagramm der Frontend-Architektur
- **8.7**: Dependency Matrix

---

## 8.2 Gesamtkomponentendiagramm

### Beschreibung

Das Gesamtkomponentendiagramm zeigt alle Hauptkomponenten des Nimrag Smart Mirror Systems und deren Beziehungen zueinander auf höchster Ebene.

**Komponenten auf dieser Ebene:**
- **Frontend Layer**: Vue 3 + TypeScript Anwendung
- **API Layer**: FastAPI REST & WebSocket Server
- **Service Layer**: Backend Business Logic
- **Hardware Layer**: GPIO, Camera, Microphone
- **External Systems**: APIs, MQTT Broker

```mermaid
graph TB
    subgraph Frontend["📱 Frontend Layer"]
        direction LR
        VUE3["<b>Vue 3 Application</b><br/>index.html<br/>TypeScript<br/>Vite Build"]
        
        subgraph WIDGETS["Widget System"]
            WW["Weather<br/>Widget"]
            CW["Calendar<br/>Widget"]
            LW["LED Control<br/>Widget"]
            SHW["Smart Home<br/>Widget"]
            MW["Music<br/>Widget"]
        end
        
        STORE["<b>Vuex Store</b><br/>Global State<br/>Management"]
        ROUTER["<b>Vue Router</b><br/>Navigation<br/>& Routes"]
        
        VUE3 --> WIDGETS
        VUE3 --> STORE
        VUE3 --> ROUTER
    end
    
    subgraph API["🔌 API & Communication Layer"]
        direction LR
        FASTAPI["<b>FastAPI Server</b><br/>REST API<br/>WebSocket Server<br/>Port 8000"]
        
        subgraph ENDPOINTS["API Endpoints"]
            WE["GET /api/v1/weather"]
            CE["GET /api/v1/calendar"]
            LE["POST /api/v1/led/control"]
            SHE["GET /api/v1/smart-home"]
            ME["GET /api/v1/music"]
        end
        
        FASTAPI --> ENDPOINTS
        
        WSE["<b>WebSocket Endpoint</b><br/>GET /ws<br/>Real-time Events"]
        
        FASTAPI --> WSE
    end
    
    subgraph SERVICES["🔧 Service Layer"]
        direction LR
        EB["<b>Event Bus</b><br/>Observer Pattern<br/>AsyncIO"]
        
        WS["<b>WeatherService</b><br/>OpenWeatherMap API<br/>Periodic Updates"]
        CS["<b>CalendarService</b><br/>Google Calendar API<br/>Event Sync"]
        LS["<b>LEDService</b><br/>GPIO/PWM Control<br/>RGB LEDs"]
        MQTT["<b>MQTTService</b><br/>Mosquitto Broker<br/>IoT Devices"]
        GS["<b>GestureService</b><br/>MediaPipe<br/>Pose Detection"]
        VS["<b>VoiceService</b><br/>Vosk ASR<br/>Voice Commands"]
        MS["<b>MusicService</b><br/>Spotify API<br/>Playback Info"]
        
        EB -.event publications.-> WS
        EB -.event publications.-> CS
        EB -.event publications.-> LS
        EB -.event publications.-> MQTT
        EB -.event publications.-> GS
        EB -.event publications.-> VS
        EB -.event publications.-> MS
    end
    
    subgraph HARDWARE["⚙️ Hardware Layer"]
        direction LR
        CAM["<b>Camera</b><br/>USB/CSI<br/>Video Stream"]
        MIC["<b>Microphone</b><br/>USB/Audio Jack<br/>Audio Input"]
        GPIO["<b>GPIO Controller</b><br/>PWM Output<br/>LED Pins"]
        DISPLAY["<b>Display/Mirror</b><br/>HDMI Output<br/>Resolution Control"]
    end
    
    subgraph EXTERNAL["🌐 External Systems"]
        direction LR
        WEATHER["<b>OpenWeatherMap API</b><br/>Weather Data<br/>REST HTTP"]
        CALENDAR["<b>Google Calendar API</b><br/>Events & Scheduling<br/>REST HTTP"]
        SPOTIFY["<b>Spotify Web API</b><br/>Music Info<br/>REST HTTP"]
        MQTT_BROKER["<b>MQTT Broker</b><br/>Mosquitto<br/>IoT Protocol"]
    end
    
    %% Connections
    Frontend -->|HTTP/WebSocket| API
    API -->|Dependency Injection| SERVICES
    
    SERVICES -->|Control & Read| HARDWARE
    
    WS -->|HTTP Requests| WEATHER
    CS -->|HTTP Requests| CALENDAR
    MS -->|HTTP Requests| SPOTIFY
    MQTT -->|MQTT Protocol| MQTT_BROKER
    
    GS -->|Read Frames| CAM
    VS -->|Read Audio| MIC
    DISPLAY -->|Display Output| Frontend
    
    class Frontend frontend
    class API api
    class SERVICES services
    class HARDWARE hardware
    class EXTERNAL external
    
    style Frontend fill:#E3F2FD
    style API fill:#FFF3E0
    style SERVICES fill:#F3E5F5
    style HARDWARE fill:#E8F5E9
    style EXTERNAL fill:#FCE4EC
```

**Wichtige Beziehungen:**

| Von | Zu | Typ | Protokoll | Beschreibung |
|-----|----|----|-----------|-------------|
| Frontend | API | Synchron | HTTP/WebSocket | REST Calls & Real-time Events |
| API | Services | Asynchron | Dependency Injection | Event Publishing & Service Calls |
| Services | Hardware | Direkt | GPIO/USB | Hardware Control & Data Read |
| Services | External | Asynchron | REST/MQTT | API Calls & IoT Communication |

---

## 8.3 Detaillierte Backend-Komponenten

### Beschreibung

Dieses Diagramm zeigt die internen Komponenten des Backend auf detaillierter Ebene, einschließlich aller Service-Abhängigkeiten und der Event-Flow-Architektur.

```mermaid
graph TB
    subgraph CORE["🔌 Core Framework"]
        FASTAPI_APP["FastAPI Application"]
        LIFESPAN["Lifespan Context<br/>Manager"]
        DI["Dependency Injection<br/>System"]
        CORS["CORS Middleware"]
    end
    
    subgraph API_LAYER["📡 API Layer"]
        REST["REST API Router<br/>(api_v1)"]
        
        subgraph WEATHER_EP["Weather Endpoints"]
            GET_WEATHER["GET /weather"]
            GET_FORECAST["GET /forecast"]
        end
        
        subgraph LED_EP["LED Endpoints"]
            POST_LED["POST /control"]
            GET_LED["GET /state"]
        end
        
        subgraph SMART_HOME_EP["Smart Home Endpoints"]
            GET_DEVICES["GET /devices"]
            POST_DEVICE["POST /control"]
        end
        
        subgraph CALENDAR_EP["Calendar Endpoints"]
            GET_EVENTS["GET /events"]
        end
        
        WS_EP["WebSocket Endpoint<br/>(/ws)"]
        
        REST --> WEATHER_EP
        REST --> LED_EP
        REST --> SMART_HOME_EP
        REST --> CALENDAR_EP
    end
    
    subgraph EVENT_BUS["🚌 Event Bus System"]
        EB_CORE["Event Bus Core"]
        PUBLISHER["Event Publisher"]
        SUBSCRIBER["Event Subscriber"]
        EVENT_QUEUE["Event Queue<br/>AsyncIO"]
        
        EB_CORE --> PUBLISHER
        EB_CORE --> SUBSCRIBER
        PUBLISHER --> EVENT_QUEUE
        EVENT_QUEUE --> SUBSCRIBER
    end
    
    subgraph SERVICES["🔧 Service Components"]
        subgraph WEATHER_SERVICE["Weather Service"]
            WS_PERIODIC["Periodic Task<br/>10 min interval"]
            WS_API["OpenWeatherMap<br/>HTTP Client"]
            WS_CACHE["Weather Cache"]
            WS_EVENTS["Publish Events"]
        end
        
        subgraph LED_SERVICE["LED Service"]
            LED_GPIO["GPIO Controller<br/>(gpiozero)"]
            LED_PWM["PWM Manager"]
            LED_EFFECTS["Effect Generator<br/>(fade, pulse)"]
        end
        
        subgraph MQTT_SERVICE["MQTT Service"]
            MQTT_CLIENT["MQTT Client<br/>(paho)"]
            MQTT_TOPICS["Topic Router"]
            MQTT_CONVERTER["Event Converter"]
        end
        
        subgraph GESTURE_SERVICE["Gesture Service"]
            GESTURE_CAPTURE["Video Capture<br/>(OpenCV)"]
            MEDIAPIPE["MediaPipe Pose<br/>Detection"]
            GESTURE_DETECT["Gesture Detection<br/>Algorithm"]
        end
        
        subgraph VOICE_SERVICE["Voice Service"]
            AUDIO_CAPTURE["Audio Capture"]
            VOSK["Vosk ASR<br/>Engine"]
            COMMAND_PARSE["Command Parser"]
        end
        
        subgraph CONFIG_SERVICE["Configuration Service"]
            CONFIG_LOADER["Config Loader<br/>(.env, YAML)"]
            CONFIG_CACHE["Config Cache"]
            SETTINGS["Settings Manager"]
        end
    end
    
    subgraph WS_MANAGER["📡 WebSocket Manager"]
        WS_CONNECTIONS["Active Connections<br/>Manager"]
        WS_BROADCAST["Broadcast Queue"]
        WS_ENCODER["Message Encoder<br/>(JSON)"]
    end
    
    subgraph DATA_LAYER["💾 Data Layer"]
        CACHE["In-Memory Cache"]
        DB["Database<br/>(SQLite/PostgreSQL)"]
        FILE_STORAGE["File Storage"]
    end
    
    %% Connections
    FASTAPI_APP --> LIFESPAN
    FASTAPI_APP --> DI
    FASTAPI_APP --> CORS
    
    FASTAPI_APP --> REST
    FASTAPI_APP --> WS_EP
    
    DI -.inject.-> EVENT_BUS
    DI -.inject.-> SERVICES
    DI -.inject.-> CONFIG_SERVICE
    
    GET_WEATHER --> WS_PERIODIC
    GET_LED --> LED_GPIO
    POST_DEVICE --> MQTT_CLIENT
    
    WS_PERIODIC --> WS_API
    WS_API --> WS_CACHE
    WS_CACHE --> WS_EVENTS
    WS_EVENTS --> EB_CORE
    
    LED_GPIO --> LED_PWM
    LED_PWM --> LED_EFFECTS
    
    MQTT_CLIENT --> MQTT_TOPICS
    MQTT_TOPICS --> MQTT_CONVERTER
    MQTT_CONVERTER --> EB_CORE
    
    GESTURE_CAPTURE --> MEDIAPIPE
    MEDIAPIPE --> GESTURE_DETECT
    GESTURE_DETECT --> EB_CORE
    
    AUDIO_CAPTURE --> VOSK
    VOSK --> COMMAND_PARSE
    COMMAND_PARSE --> EB_CORE
    
    CONFIG_LOADER --> SETTINGS
    SETTINGS --> CONFIG_CACHE
    
    WS_EP --> WS_CONNECTIONS
    EB_CORE --> WS_BROADCAST
    WS_BROADCAST --> WS_ENCODER
    WS_ENCODER --> WS_CONNECTIONS
    
    CACHE --> DATA_LAYER
    DB --> DATA_LAYER
    FILE_STORAGE --> DATA_LAYER
    
    class CORE core
    class API_LAYER api
    class EVENT_BUS event
    class SERVICES services
    class WS_MANAGER wsmanager
    class DATA_LAYER data
    
    style CORE fill:#FFECB3
    style API_LAYER fill:#FFF3E0
    style EVENT_BUS fill:#F8BBD0
    style SERVICES fill:#F3E5F5
    style WS_MANAGER fill:#BBDEFB
    style DATA_LAYER fill:#C8E6C9
```

**Wichtige Komponenten-Beziehungen:**

1. **FastAPI Application**: Zentrale Entry Point, orchestriert alle Components
2. **Event Bus**: Herzstück der Architektur, verbindet alle Services
3. **Services**: Spezialisierte Business-Logic, unabhängig und testbar
4. **WebSocket Manager**: Verwaltet Echtzeit-Kommunikation mit Clients

---

## 8.4 Detaillierte Frontend-Komponenten

### Beschreibung

Dieses Diagramm zeigt die Vue 3 Frontend-Architektur mit Components, State Management und Kommunikation.

```mermaid
graph TB
    subgraph VITE["🏗️ Build & Dev Infrastructure"]
        VITE_BUILD["Vite Build Tool"]
        TYPESCRIPT["TypeScript Compiler"]
        TAILWIND["Tailwind CSS"]
    end
    
    subgraph MAIN_APP["📱 Main Application"]
        APP["App.vue<br/>Root Component"]
        THEME["Theme Manager"]
        LAYOUT["Main Layout<br/>Container"]
    end
    
    subgraph ROUTER["🗺️ Navigation"]
        VUE_ROUTER["Vue Router 4"]
        
        subgraph ROUTES["Route Definitions"]
            DASHBOARD["Dashboard<br/>Route"]
            WIDGETS["Widgets<br/>Route"]
            SETTINGS["Settings<br/>Route"]
            DETAIL["Detail Views<br/>Route"]
        end
        
        VUE_ROUTER --> ROUTES
    end
    
    subgraph STORE["🗂️ State Management - Vuex Store"]
        VUEX["Vuex 4 Store"]
        
        subgraph WEATHER_MODULE["Weather Module"]
            W_STATE["State:<br/>temp, humidity,<br/>condition"]
            W_MUTATIONS["Mutations:<br/>setWeatherData"]
            W_ACTIONS["Actions:<br/>fetchWeather"]
            W_GETTERS["Getters:<br/>currentTemp,<br/>weatherIcon"]
        end
        
        subgraph LED_MODULE["LED Module"]
            L_STATE["State:<br/>color,<br/>brightness"]
            L_MUTATIONS["Mutations:<br/>setLED"]
            L_ACTIONS["Actions:<br/>updateLED"]
            L_GETTERS["Getters:<br/>currentColor"]
        end
        
        subgraph SMART_HOME_MODULE["Smart Home Module"]
            SH_STATE["State:<br/>devices,<br/>status"]
            SH_MUTATIONS["Mutations:<br/>updateDevice"]
            SH_ACTIONS["Actions:<br/>loadDevices"]
            SH_GETTERS["Getters:<br/>deviceList"]
        end
        
        VUEX --> WEATHER_MODULE
        VUEX --> LED_MODULE
        VUEX --> SMART_HOME_MODULE
    end
    
    subgraph COMPONENTS["🧩 Vue Components"]
        subgraph WIDGETS_COMP["Widget Components"]
            WEATHER_W["WeatherWidget.vue"]
            TIME_W["TimeWidget.vue"]
            CALENDAR_W["CalendarWidget.vue"]
            LED_W["LEDWidget.vue"]
            SMART_HOME_W["SmartHomeWidget.vue"]
            MUSIC_W["MusicWidget.vue"]
        end
        
        subgraph COMMON_COMP["Common Components"]
            HEADER["Header.vue"]
            FOOTER["Footer.vue"]
            SIDEBAR["Sidebar.vue"]
            MODAL["Modal.vue"]
            LOADER["Loader.vue"]
        end
    end
    
    subgraph COMPOSABLES["🪝 Composables & Hooks"]
        WS_COMPOSABLE["useWebSocket<br/>WebSocket Connection"]
        NOTIFICATION["useNotification<br/>Alert Management"]
        GESTURE["useGestureHandler<br/>Gesture Recognition"]
        VOICE["useVoiceCommands<br/>Voice Integration"]
    end
    
    subgraph COMMUNICATION["📡 Communication Layer"]
        HTTP_CLIENT["HTTP Client<br/>(axios/fetch)"]
        WS_CLIENT["WebSocket Client"]
        
        subgraph EVENT_LISTENERS["Event Listeners"]
            WEATHER_LISTENER["Weather Events"]
            GESTURE_LISTENER["Gesture Events"]
            VOICE_LISTENER["Voice Events"]
            DEVICE_LISTENER["Device State Events"]
        end
        
        WS_CLIENT --> EVENT_LISTENERS
    end
    
    subgraph UTILS["🛠️ Utilities & Services"]
        FORMATTER["Formatters<br/>(date, temp)"]
        VALIDATOR["Validators<br/>(input checks)"]
        STORAGE["Local Storage<br/>Service"]
        LOGGER["Logger Service"]
    end
    
    %% Connections
    VITE_BUILD --> TYPESCRIPT
    TYPESCRIPT --> TAILWIND
    
    APP --> THEME
    APP --> LAYOUT
    APP --> VUE_ROUTER
    
    LAYOUT --> WIDGETS_COMP
    LAYOUT --> COMMON_COMP
    
    WIDGETS_COMP -->|consume| VUEX
    WIDGETS_COMP -->|use| COMPOSABLES
    
    VUEX --> W_STATE
    VUEX --> L_STATE
    VUEX --> SH_STATE
    
    W_STATE --> W_MUTATIONS
    L_STATE --> L_MUTATIONS
    SH_STATE --> SH_MUTATIONS
    
    WS_COMPOSABLE --> WS_CLIENT
    GESTURE --> WS_CLIENT
    VOICE --> WS_CLIENT
    
    WS_CLIENT -->|update| VUEX
    HTTP_CLIENT -->|update| VUEX
    
    WIDGETS_COMP -->|use| FORMATTER
    WIDGETS_COMP -->|use| VALIDATOR
    
    COMMON_COMP --> UTILS
    
    class VITE vite
    class MAIN_APP main
    class ROUTER router
    class STORE store
    class COMPONENTS components
    class COMPOSABLES composables
    class COMMUNICATION communication
    class UTILS utils
    
    style VITE fill:#FBBF24
    style MAIN_APP fill:#60A5FA
    style ROUTER fill:#34D399
    style STORE fill:#A78BFA
    style COMPONENTS fill:#F472B6
    style COMPOSABLES fill:#FB923C
    style COMMUNICATION fill:#22D3EE
    style UTILS fill:#818CF8
```

**Frontend-Architektur-Highlights:**

1. **Component-Based**: Modulare, wiederverwendbare Vue Components
2. **State Management**: Zentrale Vuex Store für globalen State
3. **Composables**: Wiederverwendbare Logik (Vue 3 Composition API)
4. **Real-time Communication**: WebSocket für Live-Updates
5. **Responsive UI**: Tailwind CSS für moderne Styling

---

## 8.5 Backend-Paketdiagramm

### Beschreibung

Das Backend-Paketdiagramm zeigt die logische Packageorganisation des Python-Backend und deren Abhängigkeiten.

```mermaid
graph TB
    subgraph SRC["src/"]
        subgraph MAIN["main.py"]
            MAIN_APP["FastAPI App<br/>Instance"]
        end
        
        subgraph CORE["core/"]
            CONFIG["config.py<br/>Settings & Configuration<br/>environment variables"]
            CONSTANTS["constants.py<br/>App Constants"]
            LOGGER["logger.py<br/>Logging Setup"]
        end
        
        subgraph API["api/"]
            subgraph API_V1["api_v1/"]
                API_MAIN["api.py<br/>API Router"]
                
                subgraph ENDPOINTS["endpoints/"]
                    WEATHER_EP["weather.py<br/>Weather Endpoints"]
                    LED_EP["led.py<br/>LED Endpoints"]
                    SMART_HOME_EP["smart_home.py<br/>SmartHome Endpoints"]
                    CALENDAR_EP["calendar.py<br/>Calendar Endpoints"]
                    MUSIC_EP["music.py<br/>Music Endpoints"]
                end
                
                subgraph SCHEMAS["schemas/"]
                    WEATHER_SCHEMA["weather_schema.py<br/>Pydantic Models"]
                    LED_SCHEMA["led_schema.py<br/>Pydantic Models"]
                    RESPONSE_SCHEMA["response_schema.py<br/>Response Models"]
                end
                
                API_MAIN --> ENDPOINTS
                API_MAIN --> SCHEMAS
            end
        end
        
        subgraph SERVICES["services/"]
            WEATHER_SVC["weather.py<br/>WeatherService<br/>API client & caching"]
            LED_SVC["led.py<br/>LEDService<br/>GPIO/PWM control"]
            MQTT_SVC["mqtt.py<br/>MQTTService<br/>MQTT broker integration"]
            GESTURE_SVC["gestures.py<br/>GestureService<br/>MediaPipe tracking"]
            VOICE_SVC["voice.py<br/>VoiceService<br/>Vosk ASR"]
            WS_MANAGER["ws_manager.py<br/>WebSocketManager<br/>Connection management"]
            EVENT_BUS["event_bus.py<br/>EventBus<br/>Event pub/sub"]
        end
        
        subgraph MODELS["models/"]
            WEATHER_MODEL["weather_model.py<br/>Weather data model"]
            DEVICE_MODEL["device_model.py<br/>Device model"]
            EVENT_MODEL["event_model.py<br/>Event model"]
        end
        
        subgraph UTILS["utils/"]
            VALIDATORS["validators.py<br/>Input validators"]
            FORMATTERS["formatters.py<br/>Data formatters"]
            HELPERS["helpers.py<br/>Helper functions"]
            DECORATORS["decorators.py<br/>Custom decorators"]
        end
        
        subgraph MIDDLEWARE["middleware/"]
            CORS_MW["cors.py<br/>CORS configuration"]
            ERROR_MW["error_handler.py<br/>Error handling"]
            LOGGING_MW["logging.py<br/>Request logging"]
        end
    end
    
    %% Dependencies
    MAIN_APP --> CONFIG
    MAIN_APP --> API_V1
    MAIN_APP --> SERVICES
    MAIN_APP --> MIDDLEWARE
    
    API_V1 --> CORE
    API_V1 --> SERVICES
    API_V1 --> MODELS
    API_V1 --> UTILS
    
    ENDPOINTS --> SERVICES
    ENDPOINTS --> VALIDATORS
    
    SCHEMAS --> MODELS
    
    WEATHER_SVC --> MODELS
    LED_SVC --> MODELS
    MQTT_SVC --> MODELS
    GESTURE_SVC --> MODELS
    
    SERVICES --> EVENT_BUS
    SERVICES --> CONFIG
    SERVICES --> LOGGER
    
    WS_MANAGER --> EVENT_BUS
    
    UTILS --> LOGGER
    MIDDLEWARE --> UTILS
    
    class SRC src
    class CORE core
    class API api
    class SERVICES services
    class MODELS models
    class UTILS utils
    
    style CORE fill:#E0E7FF
    style API fill:#DBEAFE
    style SERVICES fill:#E9D5FF
    style MODELS fill:#D1FAE5
    style UTILS fill:#FEE2E2
```

**Package-Struktur Erklärung:**

| Package | Beschreibung | Abhängigkeiten |
|---------|-------------|-----------------|
| **core/** | Configuration & Settings | - |
| **api/** | REST API & WebSocket Endpoints | core/, services/, models/ |
| **services/** | Business Logic & External Integration | core/, models/, event_bus/ |
| **models/** | Data Models (ORM, Pydantic) | core/ |
| **utils/** | Helper Functions & Decorators | core/ |
| **middleware/** | Request/Response Processing | utils/ |

---

## 8.6 Frontend-Paketdiagramm

### Beschreibung

Das Frontend-Paketdiagramm zeigt die Vue 3 Projekt-Struktur und deren logische Organisation.

```mermaid
graph TB
    subgraph SRC_VUE["src/"]
        subgraph MAIN_VUE["main.ts"]
            VUE_INIT["Vue Application<br/>Entry Point"]
        end
        
        subgraph VIEWS["views/"]
            DASHBOARD_V["DashboardView.vue<br/>Main dashboard page"]
            SETTINGS_V["SettingsView.vue<br/>Settings page"]
            DETAIL_V["DetailView.vue<br/>Detail pages"]
        end
        
        subgraph COMPONENTS["components/"]
            subgraph LAYOUT["layout/"]
                HEADER_C["Header.vue"]
                FOOTER_C["Footer.vue"]
                SIDEBAR_C["Sidebar.vue"]
            end
            
            subgraph WIDGETS["widgets/"]
                WEATHER_C["WeatherWidget.vue"]
                TIME_C["TimeWidget.vue"]
                CALENDAR_C["CalendarWidget.vue"]
                LED_C["LEDControlWidget.vue"]
                SMART_HOME_C["SmartHomeWidget.vue"]
                MUSIC_C["MusicWidget.vue"]
            end
            
            subgraph COMMON["common/"]
                MODAL_C["Modal.vue"]
                CARD_C["Card.vue"]
                BUTTON_C["Button.vue"]
                LOADER_C["Loader.vue"]
                BADGE_C["Badge.vue"]
            end
        end
        
        subgraph STORE["store/"]
            subgraph MODULES["modules/"]
                WEATHER_MOD["weather.ts<br/>Weather store module"]
                LED_MOD["led.ts<br/>LED store module"]
                SMART_HOME_MOD["smartHome.ts<br/>SmartHome module"]
                APP_MOD["app.ts<br/>Global app state"]
            end
            
            STORE_INDEX["index.ts<br/>Store initialization"]
        end
        
        subgraph COMPOSABLES["composables/"]
            WS_COMP["useWebSocket.ts<br/>WebSocket management"]
            NOTIFICATION["useNotification.ts<br/>Toast notifications"]
            GESTURE_COMP["useGestureHandler.ts<br/>Gesture detection"]
            VOICE_COMP["useVoiceCommands.ts<br/>Voice recognition"]
            THEME_COMP["useTheme.ts<br/>Theme switching"]
        end
        
        subgraph SERVICES["services/"]
            HTTP_SVC["http.ts<br/>Axios instance<br/>interceptors"]
            STORAGE_SVC["storage.ts<br/>LocalStorage wrapper"]
            NOTIFICATION_SVC["notification.ts<br/>Notification service"]
            FORMATTER_SVC["formatter.ts<br/>Data formatting<br/>utilities"]
        end
        
        subgraph STYLES["styles/"]
            TAILWIND_CSS["tailwind.css<br/>Tailwind config"]
            GLOBAL_CSS["global.css<br/>Global styles"]
            COMPONENTS_CSS["components.css<br/>Component styles"]
        end
        
        subgraph TYPES["types/"]
            WEATHER_TYPE["weather.ts<br/>Weather interfaces"]
            DEVICE_TYPE["device.ts<br/>Device interfaces"]
            EVENT_TYPE["event.ts<br/>Event interfaces"]
            COMMON_TYPE["common.ts<br/>Common types"]
        end
        
        subgraph ROUTER["router/"]
            ROUTER_CONFIG["index.ts<br/>Router configuration<br/>& routes"]
            GUARDS["guards.ts<br/>Route guards<br/>Navigation guards"]
        end
        
        subgraph UTILS["utils/"]
            VALIDATORS["validators.ts<br/>Input validation"]
            HELPERS["helpers.ts<br/>Utility functions"]
            CONSTANTS_U["constants.ts<br/>App constants"]
        end
    end
    
    subgraph PUBLIC["public/"]
        FAVICON["favicon.ico"]
        MANIFEST["app.manifest"]
        ASSETS["assets/"]
    end
    
    %% Dependencies
    VUE_INIT --> VIEWS
    VUE_INIT --> ROUTER_CONFIG
    VUE_INIT --> STORE_INDEX
    VUE_INIT --> STYLES
    
    ROUTER_CONFIG --> VIEWS
    ROUTER_CONFIG --> GUARDS
    
    VIEWS --> COMPONENTS
    VIEWS --> STORE_INDEX
    VIEWS --> COMPOSABLES
    
    COMPONENTS --> STORE_INDEX
    COMPONENTS --> COMPOSABLES
    COMPONENTS --> TYPES
    COMPONENTS --> UTILS
    
    LAYOUT --> ROUTER_CONFIG
    WIDGETS --> STORE_INDEX
    
    STORE_INDEX --> MODULES
    MODULES --> TYPES
    MODULES --> SERVICES
    
    COMPOSABLES --> SERVICES
    COMPOSABLES --> STORE_INDEX
    
    SERVICES --> HTTP_SVC
    SERVICES --> STORAGE_SVC
    SERVICES --> FORMATTER_SVC
    
    WIDGETS --> SERVICES
    COMMON --> UTILS
    
    class SRC_VUE src
    class VIEWS views
    class COMPONENTS components
    class STORE store
    class COMPOSABLES composables
    class SERVICES services
    class TYPES types
    class ROUTER router
    
    style VIEWS fill:#BFDBFE
    style COMPONENTS fill:#FBCFE8
    style STORE fill:#D8B4FE
    style COMPOSABLES fill:#FECACA
    style SERVICES fill:#A7F3D0
    style TYPES fill:#FCD34D
    style ROUTER fill:#67E8F9
```

**Frontend-Paket-Struktur:**

| Verzeichnis | Zweck | Abhängigkeiten |
|-------------|-------|-----------------|
| **views/** | Page-Level Components | components/, store/ |
| **components/** | Reusable UI Components | types/, utils/, services/ |
| **store/** | Vuex State Management | types/, services/ |
| **composables/** | Vue 3 Composition Logic | services/, store/ |
| **services/** | API Communication | types/ |
| **types/** | TypeScript Interfaces | - |
| **router/** | Vue Router Configuration | views/ |

---

## 8.7 Dependency Matrix

### Beschreibung

Eine Dependency Matrix zeigt alle Komponenten und ihre gegenseitigen Abhängigkeiten in tabellarischer Form.

```
Backend Dependency Matrix:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                 | core | api | services | models | utils | middleware
─────────────────┼──────┼─────┼──────────┼────────┼───────┼───────────
core             │  -   │  ↑  │    ↑     │   ↑    │   ↑   │     ↑
api              │  →   │  -  │    →     │   →    │   →   │     ↓
services         │  →   │  ↑  │    -     │   →    │   →   │     -
models           │  →   │  -  │    -     │   -    │   -   │     -
utils            │  -   │  -  │    -     │   -    │   -   │     →
middleware       │  →   │  -  │    -     │   -    │   →   │     -

→ = Abhängigkeit (depends on)
↑ = Wird verwendet von (used by)
↓ = Bidirektionale Abhängigkeit (circular)
- = Keine Abhängigkeit
```

### Frontend Dependency Matrix:

```
Vue 3 Frontend Dependency Matrix:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

           | views | components | store | composables | services | types
───────────┼───────┼────────────┼───────┼─────────────┼──────────┼───────
views      │  -    │      →     │  →    │      →      │    →     │   →
components │  -    │      -     │  →    │      →      │    →     │   →
store      │  -    │      ↑     │  -    │      →      │    →     │   →
composables│  -    │      -     │  →    │      -      │    →     │   →
services   │  -    │      -     │  -    │      -      │    -     │   →
types      │  -    │      -     │  -    │      -      │    -     │   -
```

---

## 8.8 Kritische Abhängigkeiten und Risiken

### Backend kritische Abhängigkeiten

1. **EventBus (Single Point of Failure)**
   - Status: KRITISCH
   - Risiko: Wenn EventBus ausfällt, funktioniert die gesamte Kommunikation nicht
   - Mitigation: In-Memory Fallback, strukturiertes Logging

2. **FastAPI Application**
   - Status: KRITISCH
   - Risiko: Crash beendet alle Services
   - Mitigation: Process Supervisor (systemd, docker), Health Checks

3. **MQTT Broker Verbindung**
   - Status: HOCH
   - Risiko: IoT-Geräte können nicht gesteuert werden
   - Mitigation: Reconnect-Logik, Connection Pooling

### Frontend kritische Abhängigkeiten

1. **Vuex Store**
   - Status: KRITISCH
   - Risiko: State-Korruption beeinträchtigt UI
   - Mitigation: State Validation, DevTools Logging

2. **WebSocket Connection**
   - Status: HOCH
   - Risiko: Keine Real-time Updates
   - Mitigation: Reconnection Strategy, Fallback zu Polling

---

## 8.9 Zusammenfassung: Architektur-Highlights

### Stärken

✅ **Modulare Struktur**: Klare Trennung von Concerns  
✅ **Loose Coupling**: Services sind unabhängig  
✅ **Event-Driven**: Asynchrone, nicht-blockierende Kommunikation  
✅ **Scalability**: Services können horizontal skaliert werden  
✅ **Testability**: Jede Komponente kann isoliert getestet werden  

### Designmuster verwendet

| Pattern | Komponente | Zweck |
|---------|-----------|--------|
| **Observer** | EventBus | Publish-Subscribe Communication |
| **Singleton** | EventBus, Config | Single Instance per Lifecycle |
| **Dependency Injection** | FastAPI DI | Loose Coupling |
| **Strategy** | Service Layer | Pluggable Implementations |
| **Facade** | API Endpoints | Simplified Interface |
| **Factory** | Service Creation | Object Creation Abstraction |

### Performance-Charakteristiken

| Operation | Latenz | Durchsatz | Skalierbar |
|-----------|--------|-----------|-----------|
| REST API Call | ~50ms | 100-500 req/s | ✓ |
| WebSocket Message | <10ms | 1000+ msgs/s | ✓ |
| Event Bus Publishing | <1ms | 10,000+ events/s | ✓ |
| MQTT Message | ~100ms | 100+ msgs/s | ✓ |
| Database Query | ~20ms | 500+ queries/s | ✓ |

