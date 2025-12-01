# Zusätzliche Architektur-Diagramme für Nimrag Smart Mirror

## A.1 Deployment-Diagramm

### Beschreibung

Das Deployment-Diagramm zeigt die physische Verteilung der Komponenten auf der Raspberry Pi Hardware und deren Kommunikation mit externen Systemen.

```mermaid
graph TB
    subgraph "Nimrag Smart Mirror Hardware (Raspberry Pi 4)"
        
        subgraph "GPIO Pins"
            LED_PINS["LED Controller Pins<br/>GPIO 17, 27, 22<br/>PWM Output"]
            BUTTON_PINS["Button Input Pins<br/>GPIO 23, 24<br/>Digital Input"]
        end
        
        subgraph "USB Devices"
            CAMERA["USB Camera<br/>/dev/video0<br/>Video Capture"]
            MICROPHONE["USB Microphone<br/>Audio Input<br/>Stereo Recording"]
        end
        
        subgraph "HDMI/Display"
            DISPLAY_OUTPUT["HDMI Output<br/>1920x1080 60fps<br/>Display Control"]
        end
        
        subgraph "Backend Runtime"
            PYTHON["Python 3.12<br/>venv_py312/"]
            
            subgraph SERVICES["Backend Services"]
                FASTAPI_PROC["FastAPI Process<br/>Port 8000<br/>uvicorn"]
                
                WEATHER_PROC["Weather Service<br/>AsyncIO Task<br/>10 min interval"]
                
                GESTURE_PROC["Gesture Service<br/>Threading<br/>60 fps"]
                
                VOICE_PROC["Voice Service<br/>Threading<br/>Audio Processing"]
                
                LED_PROC["LED Service<br/>GPIO Control<br/>On-demand"]
                
                MQTT_PROC["MQTT Service<br/>Background Loop<br/>Always Connected"]
            end
            
            PYTHON --> SERVICES
        end
        
        subgraph "Frontend Runtime"
            NODE["Node.js Runtime<br/>npm/yarn"]
            
            VUE_APP["Vue 3 App<br/>Vite Dev Server<br/>Port 5173 (dev)<br/>Port 3000 (prod)"]
            
            NODE --> VUE_APP
        end
        
        subgraph "System Services"
            NGINX["Nginx Reverse Proxy<br/>Port 80/443<br/>SSL/TLS"]
            
            SYSTEMD["systemd Services<br/>Service Management<br/>Auto-restart"]
            
            DNSMASQ["DNSMasq<br/>Local DNS<br/>mDNS Resolution"]
        end
        
    end
    
    subgraph "Network Infrastructure"
        WIFI["WiFi Module<br/>802.11ac<br/>2.4/5 GHz"]
        ETHERNET["Ethernet Port<br/>Gigabit<br/>Optional"]
    end
    
    subgraph "External Services"
        
        subgraph "Public APIs"
            WEATHER_API["OpenWeatherMap API<br/>REST HTTP<br/>api.openweathermap.org"]
            CALENDAR_API["Google Calendar API<br/>REST HTTP<br/>googleapis.com"]
            SPOTIFY_API["Spotify Web API<br/>REST HTTP<br/>api.spotify.com"]
        end
        
        subgraph "IoT Integration"
            MQTT_BROKER["MQTT Broker<br/>Port 1883<br/>mosquitto.org or local"]
            
            SMART_DEVICES["Smart Home Devices<br/>Philips Hue<br/>Home Assistant<br/>Zigbee Devices"]
        end
        
    end
    
    subgraph "User Devices"
        MOBILE["Mobile App<br/>iPhone/Android<br/>Control Interface"]
        
        BROWSER["Web Browser<br/>PC/Tablet<br/>Remote Access"]
    end
    
    %% Connections
    LED_PINS -.GPIO.-> LED_PROC
    BUTTON_PINS -.GPIO.-> VOICE_PROC
    
    CAMERA -.USB Video.-> GESTURE_PROC
    MICROPHONE -.USB Audio.-> VOICE_PROC
    
    DISPLAY_OUTPUT -.HDMI.-> VUE_APP
    
    FASTAPI_PROC -->|HTTP| VUE_APP
    FASTAPI_PROC -->|WebSocket| VUE_APP
    
    WEATHER_PROC -->|HTTP| WEATHER_API
    VOICE_PROC -->|HTTP| CALENDAR_API
    LED_PROC -.event.-> WEATHER_PROC
    
    MQTT_PROC -.MQTT Protocol.-> MQTT_BROKER
    MQTT_BROKER -.MQTT.-> SMART_DEVICES
    
    NGINX -->|reverse proxy| FASTAPI_PROC
    NGINX -->|serve| VUE_APP
    
    SYSTEMD -->|manage| FASTAPI_PROC
    SYSTEMD -->|manage| MQTT_PROC
    
    WIFI -.network.-> MQTT_BROKER
    WIFI -.network.-> WEATHER_API
    WIFI -.network.-> CALENDAR_API
    
    MOBILE -->|HTTP| NGINX
    BROWSER -->|HTTP| NGINX
    
    class GPIO gpio
    class USB usb
    class DISPLAY display
    class SERVICES services
    class FRONTEND frontend
    class EXTERNAL external
    
    style "Nimrag Smart Mirror Hardware (Raspberry Pi 4)" fill:#E8F5E9
    style "Network Infrastructure" fill:#FFF3E0
    style "External Services" fill:#FCE4EC
    style "User Devices" fill:#E3F2FD
```

### Deployment-Charakteristiken

**Hardware:**
- Raspberry Pi 4 (4GB RAM, 64GB SD-Card)
- USB-basierte Kameras und Mikrofone
- GPIO-basierte LED-Controller
- HDMI-Display (1080p@60fps)

**Netzwerk:**
- WiFi 802.11ac für externe Kommunikation
- mDNS für lokale Geräteerkennung
- Optional: Ethernet für Stabilität

**Services:**
- Backend läuft in Python venv
- Frontend läuft über Nginx
- Systemd verwaltet Service-Lifecycle

---

## A.2 Datenfluss-Diagramm (DFD)

### Beschreibung

Das Datenfluss-Diagramm zeigt den Fluss von Daten durch das System auf oberster Ebene.

```mermaid
graph LR
    subgraph INPUT["📥 Input Sources"]
        USER["User Input<br/>Touch/Gesture<br/>Voice"]
        EXTERNAL_DEVICE["External Devices<br/>Smart Home<br/>IoT"]
        PERIODIC["Periodic Updates<br/>Weather<br/>Calendar"]
    end
    
    subgraph PROCESSING["⚙️ Processing & Logic"]
        ROUTER["Command Router<br/>Route to handler"]
        
        GESTURE_PROC["Gesture Processing<br/>MediaPipe<br/>Confidence scoring"]
        
        VOICE_PROC["Voice Processing<br/>Vosk ASR<br/>Command parsing"]
        
        BUSINESS_LOGIC["Business Logic<br/>Validation<br/>Authorization"]
        
        DATA_TRANSFORM["Data Transformation<br/>Format conversion<br/>Aggregation"]
    end
    
    subgraph STORAGE["💾 Storage & Cache"]
        CACHE["In-Memory Cache<br/>Weather<br/>Device States<br/>User Preferences"]
        
        DATABASE["Persistent DB<br/>Configuration<br/>History<br/>Logs"]
    end
    
    subgraph OUTPUT["📤 Output Destinations"]
        FRONTEND["Frontend Updates<br/>WebSocket<br/>REST Response"]
        
        HARDWARE_CONTROL["Hardware Control<br/>GPIO/PWM<br/>LED Colors"]
        
        IOT_DEVICES["IoT Devices<br/>MQTT Publish<br/>Device Commands"]
        
        EXTERNAL_API["External APIs<br/>Spotify Control<br/>Calendar Sync"]
    end
    
    INPUT -->|events| ROUTER
    
    ROUTER -->|gesture| GESTURE_PROC
    ROUTER -->|voice| VOICE_PROC
    ROUTER -->|api_call| BUSINESS_LOGIC
    
    GESTURE_PROC -->|processed| BUSINESS_LOGIC
    VOICE_PROC -->|commands| BUSINESS_LOGIC
    
    BUSINESS_LOGIC -->|query| CACHE
    BUSINESS_LOGIC -->|query| DATABASE
    
    CACHE -->|results| DATA_TRANSFORM
    DATABASE -->|results| DATA_TRANSFORM
    
    DATA_TRANSFORM -->|state| FRONTEND
    DATA_TRANSFORM -->|commands| HARDWARE_CONTROL
    DATA_TRANSFORM -->|messages| IOT_DEVICES
    DATA_TRANSFORM -->|requests| EXTERNAL_API
    
    EXTERNAL_DEVICE -->|state| CACHE
    EXTERNAL_API -->|responses| CACHE
    PERIODIC -->|data| CACHE
    
    class INPUT input
    class PROCESSING processing
    class STORAGE storage
    class OUTPUT output
    
    style INPUT fill:#B3E5FC
    style PROCESSING fill:#F8BBD0
    style STORAGE fill:#C8E6C9
    style OUTPUT fill:#FFE0B2
```

**Datenfluss-Charakteristiken:**

- **Synchrone Pfade**: REST API Calls (< 100ms)
- **Asynchrone Pfade**: WebSocket Events (< 10ms)
- **Periodische Pfade**: Scheduled Updates (10min interval)
- **Event-getriebene Pfade**: Gestures/Voice (< 100ms)

---

## A.3 State-Diagramm: WebSocket Connection Lifecycle

### Beschreibung

Das State-Diagramm zeigt die verschiedenen Zustände einer WebSocket-Verbindung und die Übergänge zwischen ihnen.

```mermaid
stateDiagram-v2
    [*] --> CONNECTING: initiate_connection()
    
    CONNECTING --> CONNECTED: connection_established
    CONNECTING --> CLOSED: connection_timeout
    CONNECTING --> FAILED: connection_error
    
    CONNECTED --> CONNECTED: send_message()\nreceive_message()
    CONNECTED --> HEARTBEAT: timeout_check()
    
    HEARTBEAT --> CONNECTED: pong_received
    HEARTBEAT --> CLOSED: pong_timeout
    
    CONNECTED --> CLOSED: close_requested()
    CONNECTED --> FAILED: unexpected_error
    
    FAILED --> RECONNECTING: retry_attempt()
    FAILED --> CLOSED: max_retries_exceeded
    
    RECONNECTING --> CONNECTED: connection_restored
    RECONNECTING --> FAILED: reconnection_failed
    
    CLOSED --> [*]
    
    note right of CONNECTING
        Attempt to establish
        WebSocket connection
        with exponential backoff
    end note
    
    note right of CONNECTED
        Connection active,
        bidirectional communication
        messages flowing
    end note
    
    note right of HEARTBEAT
        Keep-alive phase,
        waiting for pong
        response
    end note
    
    note right of FAILED
        Connection lost,
        attempting recovery
    end note
    
    note right of RECONNECTING
        Backoff delay active,
        preparing for retry
    end note
    
    note right of CLOSED
        Connection terminated
        cleanly or after
        max retries
    end note
```

**State Transitions:**

| Von | Nach | Auslöser | Aktion |
|-----|------|----------|--------|
| CONNECTING | CONNECTED | connection_established | Start heartbeat timer |
| CONNECTED | HEARTBEAT | timeout_check (30s) | Send ping |
| HEARTBEAT | CONNECTED | pong_received | Reset timer |
| CONNECTED | FAILED | error | Log error, start retry |
| FAILED | RECONNECTING | retry_attempt | Calculate backoff delay |
| RECONNECTING | CONNECTED | success | Resume normal operation |

---

## A.4 Entity-Relationship Diagramm (ERD)

### Beschreibung

Das ERD zeigt die Datenmodelle und deren Beziehungen in der Datenbank.

```mermaid
erDiagram
    USERS ||--o{ DEVICES : owns
    USERS ||--o{ PREFERENCES : has
    USERS ||--o{ ACTIVITY_LOG : generates
    
    DEVICES ||--o{ DEVICE_STATE : has
    DEVICES ||--o{ DEVICE_COMMANDS : receives
    
    SMART_HOME_DEVICES ||--o{ DEVICE_STATE : maintains
    
    EVENTS ||--o{ EVENT_METADATA : has
    WEATHER ||--o{ WEATHER_FORECAST : contains
    
    USERS {
        int user_id PK
        string username
        string email
        string password_hash
        string preferences_json
        timestamp created_at
        timestamp updated_at
    }
    
    DEVICES {
        int device_id PK
        int user_id FK
        string device_name
        string device_type
        string status
        timestamp last_activity
        string metadata_json
    }
    
    DEVICE_STATE {
        int state_id PK
        int device_id FK
        string property_name
        string property_value
        timestamp recorded_at
    }
    
    DEVICE_COMMANDS {
        int command_id PK
        int device_id FK
        string command_type
        string command_payload
        string status
        timestamp created_at
        timestamp executed_at
    }
    
    PREFERENCES {
        int preference_id PK
        int user_id FK
        string key
        string value
        timestamp updated_at
    }
    
    ACTIVITY_LOG {
        int log_id PK
        int user_id FK
        string action_type
        string action_detail
        string result_status
        timestamp created_at
    }
    
    SMART_HOME_DEVICES {
        int device_id PK
        string mqtt_topic
        string device_model
        string manufacturer
        string firmware_version
    }
    
    EVENTS {
        int event_id PK
        string event_type
        string event_category
        timestamp event_time
        string status
    }
    
    EVENT_METADATA {
        int metadata_id PK
        int event_id FK
        string key
        string value
    }
    
    WEATHER {
        int weather_id PK
        float temperature
        float humidity
        string condition
        float wind_speed
        timestamp recorded_at
    }
    
    WEATHER_FORECAST {
        int forecast_id PK
        int weather_id FK
        int forecast_day
        float min_temp
        float max_temp
        string condition
        int precipitation_chance
    }
```

### Datenmodelle

**USERS (Benutzer)**
- Speichert Benutzerinformationen und Authentifizierung
- Primary Key: user_id
- Beziehung: 1:N zu DEVICES, PREFERENCES, ACTIVITY_LOG

**DEVICES (Geräte)**
- Speichert gekoppelte Geräte (z.B. Smart Home Lampen)
- Primary Key: device_id
- Foreign Key: user_id (USERS)
- Beziehung: 1:N zu DEVICE_STATE, DEVICE_COMMANDS

**DEVICE_STATE (Gerätestatus)**
- Zeitreihen-Daten für Gerätezustände
- Primary Key: state_id
- Foreign Key: device_id (DEVICES)
- Ermöglicht Geschichtsabfragen

**WEATHER (Wetterdaten)**
- Speichert aktuelle Wetterdaten
- Primary Key: weather_id
- Relationship: 1:N zu WEATHER_FORECAST

---

## A.5 Use Case Diagramm: Gesture Recognition

### Beschreibung

Das Use Case Diagramm zeigt alle möglichen Anwendungsfälle der Gestenerkennung.

```mermaid
graph TB
    ACTOR["👤 User"]
    
    subgraph SYSTEM["Nimrag Gesture<br/>Recognition System"]
        UC1["Navigate Left<br/>🔄 View previous"]
        UC2["Navigate Right<br/>🔄 View next"]
        UC3["Navigate Down<br/>🔄 Scroll down"]
        UC4["Navigate Up<br/>🔄 Scroll up"]
        UC5["Gesture Timeout<br/>Reset recognition"]
        UC6["Unknown Gesture<br/>Ignore & wait"]
        UC7["Adjust Sensitivity<br/>Recalibrate"]
    end
    
    ACTOR -->|perform| UC1
    ACTOR -->|perform| UC2
    ACTOR -->|perform| UC3
    ACTOR -->|perform| UC4
    ACTOR -->|adjust| UC7
    
    UC1 -.extends.-> UC5
    UC2 -.extends.-> UC5
    UC3 -.extends.-> UC5
    UC4 -.extends.-> UC5
    UC6 -.extends.-> UC5
    
    UC7 -.includes.-> UC5
    
    class ACTOR actor
    class UC1 usecase
    class UC2 usecase
    class UC3 usecase
    class UC4 usecase
    class UC5 usecase
    class UC6 usecase
    class UC7 usecase
```

**Gesture Use Cases:**

| Use Case | Beschreibung | Aktion | Erfolgs-Kriterien |
|----------|-------------|--------|-------------------|
| Navigate Left | Wisch nach links | Vorherige Seite | Seitenumbruch < 500ms |
| Navigate Right | Wisch nach rechts | Nächste Seite | Seitenumbruch < 500ms |
| Navigate Down | Wisch nach unten | Nach unten scrollen | Smooth scroll |
| Navigate Up | Wisch nach oben | Nach oben scrollen | Smooth scroll |
| Adjust Sensitivity | Einstellung ändern | Neukalbrierung | Neue Threshold speichern |

---

## A.6 Zustandsdiagramm: LED Control States

### Beschreibung

Das Zustandsdiagramm zeigt die verschiedenen LED-Zustände und mögliche Übergänge.

```mermaid
stateDiagram-v2
    [*] --> OFF
    
    OFF --> ON: turn_on()
    OFF --> ERROR: hardware_error
    
    ON --> BRIGHTNESS_ADJUST: set_brightness()
    ON --> COLOR_CHANGE: set_color()
    ON --> FADE_IN: fade_in()
    ON --> FADE_OUT: fade_out()
    ON --> PULSE: set_pulse()
    ON --> OFF: turn_off()
    
    BRIGHTNESS_ADJUST --> ON: adjustment_complete
    COLOR_CHANGE --> ON: color_set
    FADE_IN --> ON: fade_complete
    FADE_OUT --> OFF: fade_complete
    PULSE --> ON: pulse_active
    
    ERROR --> OFF: reset()
    ERROR --> ON: recovery_attempt()
    ERROR --> ERROR: persistent_error
    
    note right of OFF
        All LEDs off,
        no power consumption
    end note
    
    note right of ON
        LEDs on with
        current settings
    end note
    
    note right of COLOR_CHANGE
        Transitioning between
        colors smoothly
    end note
    
    note right of PULSE
        Pulsing effect active,
        periodic brightness changes
    end note
    
    note right of ERROR
        Hardware error detected,
        attempting recovery
    end note
```

**LED State Machine:**

```
┌─────────────────────────────────┐
│         OFF (Default)           │
│  • All PWM pins = 0             │
│  • No power draw (except GPIO)   │
└─────────────────────────────────┘
         ↑            ↓
         │         turn_on()
         │            ↓
         ↓      ┌─────────────────┐
       OFF      │        ON       │
         ↑      │ • Current color │
         │      │ • Brightness    │
         │      └─────────────────┘
         │          ↓       ↓
         │      adjust    change
         │      brightness color
         │          ↓       ↓
         └──────────┴───────┘
```

---

## A.7 Activity Diagramm: Complete User Journey

### Beschreibung

Das Activity Diagramm zeigt einen typischen Benutzer-Workflow vom Starten der Anwendung bis zur Interaktion.

```mermaid
graph TD
    START([User starts<br/>mirror])
    
    BOOT["System boots<br/>FastAPI starts"]
    LOAD_CONFIG["Load configuration<br/>from .env"]
    INIT_SERVICES["Initialize services<br/>MQTT, Weather, Gesture"]
    LOAD_FRONTEND["Load Vue 3<br/>frontend"]
    ESTABLISH_WS["Establish WebSocket<br/>connection"]
    READY["System ready<br/>dashboard shown"]
    
    START --> BOOT
    BOOT --> LOAD_CONFIG
    LOAD_CONFIG --> INIT_SERVICES
    INIT_SERVICES --> LOAD_FRONTEND
    LOAD_FRONTEND --> ESTABLISH_WS
    ESTABLISH_WS --> READY
    
    READY --> USER_ACTION{User action}
    
    USER_ACTION -->|Gesture| GESTURE["Process gesture<br/>MediaPipe"]
    USER_ACTION -->|Voice| VOICE["Process voice<br/>Vosk"]
    USER_ACTION -->|Touch| TOUCH["Process touch<br/>Event listener"]
    USER_ACTION -->|None| PERIODIC["Check periodic<br/>updates"]
    
    GESTURE --> ROUTE["Route to handler"]
    VOICE --> ROUTE
    TOUCH --> ROUTE
    PERIODIC --> UPDATE_DATA["Update data<br/>Weather, Calendar"]
    
    ROUTE --> EXECUTE["Execute command"]
    EXECUTE --> UPDATE_STATE["Update state<br/>Vuex store"]
    
    UPDATE_DATA --> UPDATE_STATE
    
    UPDATE_STATE --> BROADCAST["Broadcast via<br/>WebSocket"]
    
    BROADCAST --> RENDER["Render UI<br/>Vue components"]
    
    RENDER --> UPDATE_HW["Update hardware<br/>LED, GPIO"]
    
    UPDATE_HW --> READY
    
    READY --> EXIT{Exit?}
    EXIT -->|No| USER_ACTION
    EXIT -->|Yes| SHUTDOWN["Graceful shutdown<br/>cleanup resources"]
    SHUTDOWN --> END([System stopped])
    
    style START fill:#90EE90
    style READY fill:#87CEEB
    style USER_ACTION fill:#FFD700
    style EXECUTE fill:#FFA07A
    style UPDATE_STATE fill:#DDA0DD
    style RENDER fill:#98FB98
    style SHUTDOWN fill:#FFB6C1
    style END fill:#FF6B6B
```

### Workflow-Schritte

1. **Boot Phase** (< 10 Sekunden)
   - System startet, Services werden initialisiert
   - WebSocket wird verbunden
   - Frontend wird geladen

2. **Ready Phase**
   - Dashboard wird angezeigt
   - Periodische Updates starten

3. **Interaction Loop**
   - Benutzer führt Aktion durch
   - Aktion wird verarbeitet
   - State wird aktualisiert
   - UI wird re-rendered

4. **Shutdown Phase**
   - Graceful Cleanup
   - Alle Connections werden beendet
   - Resources werden freigegeben

---

## A.8 Zusammenfassung: Diagramm-Übersicht

| Diagramm-Typ | Datei | Fokus | Audience |
|-------------|-------|-------|----------|
| **Sequenzdiagramme** | 6_Sequenzdiagramme_Komponentenebene.md | Zeitliche Abläufe | Entwickler |
| **Komponentendiagramme** | 8_Komponenten_und_Paketdiagramme.md | Struktur & Abhängigkeiten | Architekten |
| **Paketdiagramme** | 8_Komponenten_und_Paketdiagramme.md | Logische Organisation | Entwickler |
| **Deployment-Diagramm** | Dieses Dokument | Physische Verteilung | DevOps/Betrieb |
| **Datenfluss-Diagramm** | Dieses Dokument | Daten-Journeys | Alle |
| **State-Diagramme** | Dieses Dokument | Zustandsübergänge | Entwickler |
| **ERD** | Dieses Dokument | Datenmodelle | DBAs |
| **Use Case Diagramm** | Dieses Dokument | Funktionalitäten | Stakeholder |
| **Activity Diagramm** | Dieses Dokument | Prozessabläufe | Business Analyst |

---

## A.9 Mermaid Diagramme Best Practices

### Lesbarkeit

✓ Klare Benennung aller Komponenten  
✓ Konsistente Farbschemas  
✓ Hierarchische Organisation  
✓ Aussagekräftige Beschreibungen  

### Wartbarkeit

✓ Modulare Struktur  
✓ Dokumentation mit Kontext  
✓ Versionskontrolle der Diagramme  
✓ Automatische Validierung  

### Aktualisierung

Die Diagramme sollten aktualisiert werden wenn:
- Neue Services/Components hinzugefügt werden
- Abhängigkeiten sich ändern
- API Endpoints sich ändern
- Deployment-Strategie sich ändert

Empfohlener Update-Zyklus: Quarterly oder bei Major Changes

