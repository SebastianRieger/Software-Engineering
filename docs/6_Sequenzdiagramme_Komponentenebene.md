# Abschnitt 6: Sequenzdiagramme auf Komponentenebene

## 6.1 Überblick

Die Sequenzdiagramme beschreiben die Interaktionen zwischen den Komponenten des Nimrag Smart Mirror Systems auf Komponentenebene. Sie zeigen die zeitliche Abfolge von Nachrichten und Operationen bei kritischen Geschäftsprozessen.

---

## 6.2 Sequenzdiagramm: Wetter-Update-Workflow

### Beschreibung

Der Wetter-Update-Workflow beschreibt den periodischen Abruf von Wetterdaten von der OpenWeatherMap API, deren Verarbeitung im Backend und die Verteilung an alle verbundenen Frontend-Clients über WebSocket.

**Beteiligte Komponenten:**
- **WeatherService**: Periodischer Service zur Wetterdatenbeschaffung
- **EventBus**: Zentrale Nachrichtenvermittlung
- **WebSocket Handler**: Verteilung an Frontend-Clients
- **Frontend (Vue 3)**: Anzeige der Wetterdaten

**Szenario:** Alle 10 Minuten wird der WeatherService aktiviert, ruft neue Wetterdaten ab und benachrichtigt alle Subscriber.

```mermaid
sequenceDiagram
    actor AsyncTask as AsyncIO Task
    participant WS as WeatherService
    participant API as OpenWeatherMap<br/>API
    participant EB as EventBus
    participant WSH as WebSocket<br/>Handler
    participant Frontend as Vue 3<br/>Frontend
    participant Store as Vuex<br/>Store

    AsyncTask->>WS: start_periodic_updates()
    WS->>WS: Wait 10 minutes
    
    loop Every 10 minutes
        WS->>API: GET /data/2.5/weather<br/>(lat, lon, appid)
        activate API
        API-->>WS: {temp, humidity,<br/>condition, timestamp}
        deactivate API
        
        WS->>WS: Parse & Validate Data
        
        WS->>EB: publish("WeatherDataUpdated")<br/>{temperature, humidity,<br/>condition, forecast}
        activate EB
        
        EB->>WSH: notify_subscribers()
        activate WSH
        
        WSH->>Frontend: WebSocket Message<br/>{"type": "weather_update",<br/>"data": {...}}
        activate Frontend
        
        Frontend->>Store: commit('setWeatherData', data)
        activate Store
        
        Store->>Frontend: Update State
        deactivate Store
        
        Frontend->>Frontend: Render UI
        Note over Frontend: Display new weather data<br/>temperature, conditions, etc.
        deactivate Frontend
        
        deactivate WSH
        deactivate EB
    end
```

**Wichtige Aspekte:**
- **Asynchrone Verarbeitung**: Der Weather Service läuft als Background Task und blockiert nicht
- **Event-Driven**: Über EventBus können mehrere Subscriber informiert werden (z.B. auch LED Service)
- **Real-time Updates**: WebSocket ermöglicht sofortige UI-Updates ohne Polling
- **Error Handling**: API-Fehler werden abgefangen und geloggt

---

## 6.3 Sequenzdiagramm: Gestenerkennung und UI-Navigation

### Beschreibung

Der Gestenerkennung-Workflow beschreibt die Erfassung von Handgesten über die Kamera, deren Analyse durch MediaPipe und die daraus resultierende Navigation im Frontend.

**Beteiligte Komponenten:**
- **GestureService**: Video-Capture und Pose-Detection
- **EventBus**: Event-Verteilung
- **Navigation Controller**: Verarbeitung von Gesten-Commands
- **Frontend Router**: Navigation zwischen Seiten/Screens

**Szenario:** Benutzer macht eine Wisch-Geste nach rechts → GestureService erkennt die Geste → Event wird publiziert → Frontend navigiert zur nächsten Seite.

```mermaid
sequenceDiagram
    actor User
    participant Camera as Camera/<br/>MediaPipe
    participant GS as GestureService
    participant ET as Event Bus
    participant NavC as Navigation<br/>Controller
    participant Router as Vue<br/>Router
    participant UI as Frontend<br/>UI

    User->>Camera: Performs swipe_right gesture
    activate Camera
    
    Camera->>Camera: Capture frame 60fps
    Camera->>Camera: Run MediaPipe Pose detection
    Camera->>Camera: Calculate body center trajectory
    
    Camera->>GS: Frame data + pose landmarks
    deactivate Camera
    
    activate GS
    GS->>GS: Exponential moving average<br/>smoothing
    GS->>GS: Detect gesture pattern
    Note over GS: Analyze displacement vector<br/>Check gesture thresholds
    
    GS->>GS: Validate gesture cooldown
    alt Gesture detected & cooldown expired
        GS->>ET: publish("GestureDetected")<br/>{"gesture": "swipe_right",<br/>"confidence": 0.89}
    else Cooldown active
        GS->>GS: Ignore gesture
    end
    deactivate GS
    
    activate ET
    ET->>NavC: subscribe("GestureDetected")
    activate NavC
    
    NavC->>NavC: Map gesture to action
    Note over NavC: swipe_right → navigate('next')
    
    NavC->>Router: next()
    deactivate NavC
    deactivate ET
    
    activate Router
    Router->>Router: Update current route
    Router->>UI: beforeRouteChange hook
    
    deactivate Router
    activate UI
    
    UI->>UI: Transition animation
    UI->>UI: Load new component
    UI->>UI: Render new page
    
    Note over UI: Display next widget/screen<br/>with smooth transition
    deactivate UI
```

**Wichtige Aspekte:**
- **Echtzeit-Verarbeitung**: Video-Stream wird kontinuierlich mit 60fps verarbeitet
- **Gesture Debouncing**: Cooldown-Mechanismus verhindert mehrfache Erkennung
- **Konfidenz-Scores**: Nur Gesten mit ausreichender Konfidenz werden akzeptiert
- **Responsive Navigation**: UI-Updates sind smooth und nicht blockierend

---

## 6.4 Sequenzdiagramm: LED-Steuerung über REST API

### Beschreibung

Der LED-Steuerung-Workflow zeigt die Interaktion zwischen Frontend-Widget, FastAPI REST Endpoint und LED Service.

**Beteiligte Komponenten:**
- **Frontend (LED Widget)**: Benutzer-Interface für LED-Kontrolle
- **FastAPI Endpoint**: `/api/v1/led/control`
- **LEDService**: Hardware-Steuerung (GPIO/PWM)
- **EventBus**: Event-Broadcasting an andere Services

**Szenario:** Benutzer ändert die LED-Farbe über das Frontend-Widget → HTTP POST Request → LED-Steuerung → Event-Broadcast.

```mermaid
sequenceDiagram
    actor User
    participant UI as LED Widget<br/>Vue Component
    participant HTTP as HTTP Client
    participant EP as FastAPI<br/>Endpoint
    participant LS as LED<br/>Service
    participant GPIO as GPIO/PWM<br/>Hardware
    participant EB as EventBus
    participant WS as WebSocket<br/>Handler

    User->>UI: Select color: Red<br/>Brightness: 80%
    
    UI->>UI: Validate input
    Note over UI: Check color format,<br/>brightness range
    
    UI->>HTTP: POST /api/v1/led/control<br/>{color: "FF0000",<br/>brightness: 0.8}
    
    activate HTTP
    HTTP->>EP: HTTP Request
    deactivate HTTP
    
    activate EP
    EP->>EP: Validate request data
    EP->>EP: Extract parameters
    
    alt Validation success
        EP->>LS: set_color((1.0, 0.0, 0.0))<br/>set_brightness(0.8)
        activate LS
        
        LS->>LS: Convert RGB to PWM values
        Note over LS: R=1.0*0.8=0.8<br/>G=0.0*0.8=0.0<br/>B=0.0*0.8=0.0
        
        LS->>GPIO: Set PWM pin 17 → 0.8<br/>Set PWM pin 27 → 0.0<br/>Set PWM pin 22 → 0.0
        activate GPIO
        
        GPIO->>GPIO: Apply PWM signal
        Note over GPIO: Hardware: LED dims to red<br/>at 80% brightness
        deactivate GPIO
        
        LS-->>EP: {"status": "success"}
        deactivate LS
        
        EP->>EB: publish("LEDControlledByUser")<br/>{"color": [1.0, 0.0, 0.0],<br/>"brightness": 0.8,<br/>"source": "api"}
        activate EB
        
        EB->>WS: notify_subscribers()
        activate WS
        
        WS->>UI: WebSocket: {"type": "led_state_changed",<br/>"color": "FF0000",<br/>"brightness": 0.8}
        activate UI
        
        UI->>UI: Update local state
        UI->>UI: Reflect change in UI
        deactivate UI
        
        deactivate WS
        deactivate EB
        
        EP-->>HTTP: 200 OK<br/>{"status": "success",<br/>"led_state": {...}}
    else Validation error
        EP-->>HTTP: 400 Bad Request<br/>{"error": "Invalid color format"}
    end
    
    deactivate EP
    
    activate HTTP
    HTTP-->>UI: Response
    deactivate HTTP
```

**Wichtige Aspekte:**
- **Validierung**: Request-Daten werden vor Verarbeitung validiert
- **Event Broadcasting**: LED-Steuerung wird als Event publiziert für Konsistenz
- **Bidirektionale Feedback**: WebSocket bestätigt die Änderung im Frontend
- **Error Handling**: Fehler werden mit aussagekräftigen Fehlermeldungen zurückgegeben

---

## 6.5 Sequenzdiagramm: MQTT Smart Home Integration

### Beschreibung

Der Smart Home Integration-Workflow zeigt die MQTT-basierte Kommunikation mit externen IoT-Geräten.

**Beteiligte Komponenten:**
- **MQTT Broker**: Mosquitto oder ähnlich
- **MQTTService**: Verbindung zum Broker
- **Smart Home Devices**: Externe Geräte (z.B. Philips Hue)
- **EventBus**: Konvertierung zu internen Events
- **Frontend**: Anzeige von Smart Home Status

**Szenario:** Externe Smart Home Lampe wird von anderer App aus gesteuert → MQTT Message → Backend aktualisiert intern → Frontend-Anzeige aktualisiert.

```mermaid
sequenceDiagram
    actor ExtApp as External<br/>Smart Home App
    participant Device as Smart Home<br/>Device (Hue)
    participant MQTT as MQTT Broker<br/>(Mosquitto)
    participant MS as MQTT<br/>Service
    participant EB as EventBus
    participant Frontend as Vue 3<br/>Frontend

    ExtApp->>Device: Turn off light
    
    Device->>MQTT: PUBLISH to<br/>nimrag/smarthome/devices/hue-1/state<br/>{"state": "off", "brightness": 0}
    
    activate MQTT
    MQTT->>MQTT: Route message
    
    MQTT->>MS: Message received
    deactivate MQTT
    
    activate MS
    MS->>MS: _on_message callback triggered
    
    MS->>MS: Parse topic & payload
    Note over MS: Extract device_id: "hue-1"<br/>Extract state: "off"
    
    MS->>MS: Deserialize JSON payload
    
    MS->>EB: publish("SmartHomeDeviceStateChanged")<br/>{"device_id": "hue-1",<br/>"device_type": "light",<br/>"state": "off",<br/>"brightness": 0,<br/>"updated_at": timestamp}
    
    deactivate MS
    
    activate EB
    EB->>EB: Notify all subscribers
    
    EB->>Frontend: Event received in WebSocket handler
    deactivate EB
    
    activate Frontend
    Frontend->>Frontend: Update Vuex store<br/>setSmartHomeState()
    
    Frontend->>Frontend: Component re-render
    Note over Frontend: Smart Home Widget shows:<br/>Hue Light: OFF
    
    deactivate Frontend
    
    Note over Frontend,MQTT: State is now synchronized<br/>across all platforms
```

**Wichtige Aspekte:**
- **Asynchrone Kommunikation**: MQTT ist asynchron, nicht blockierend
- **Topic-basierte Routing**: MQTT-Topics organisieren Gerätekommunikation
- **State Synchronization**: Backend synchronisiert External State mit Internal State
- **Bidirektional**: Backend kann auch an MQTT-Topics publizieren für Gerätesteuerung

---

## 6.6 Sequenzdiagramm: WebSocket-Verbindungsmanagement

### Beschreibung

Der WebSocket-Verbindungsmanagement-Workflow zeigt wie WebSocket-Verbindungen aufgebaut, verwaltet und beendet werden.

**Beteiligte Komponenten:**
- **Frontend**: Vue 3 Client
- **FastAPI WebSocket Endpoint**: `/ws`
- **WebSocket Manager**: Verwaltung aller Verbindungen
- **EventBus**: Broadcasting von Events an Clients

**Szenario:** Frontend verbindet sich mit WebSocket, empfängt Events, und terminiert Verbindung.

```mermaid
sequenceDiagram
    participant Frontend as Vue 3<br/>Frontend Client
    participant WS as WebSocket<br/>Endpoint
    participant WSM as WebSocket<br/>Manager
    participant EB as EventBus
    participant Backend as Backend<br/>Services

    Frontend->>WS: WebSocket Connection Request<br/>GET /ws
    
    activate WS
    WS->>WS: Accept connection
    
    WS->>WSM: register_connection(websocket)
    activate WSM
    
    WSM->>WSM: Add to active connections
    WSM->>WSM: Create event loop listener
    
    Note over WSM: Connection established<br/>Ready to receive events
    
    deactivate WSM
    
    Frontend->>WS: Connected ✓
    deactivate WS
    
    rect rgb(200, 220, 255)
        Note over Frontend,Backend: Active event streaming
        
        Backend->>EB: publish("WeatherDataUpdated")
        activate EB
        
        EB->>WSM: notify_subscribers()
        activate WSM
        
        WSM->>WS: send(event_message)
        activate WS
        
        WS->>Frontend: WebSocket message<br/>{"type": "weather_update", ...}
        
        deactivate WS
        deactivate WSM
        deactivate EB
        
        Frontend->>Frontend: Process event<br/>Update Vuex Store
    end
    
    loop Heartbeat every 30s
        Frontend->>WS: ping
        activate WS
        WS-->>Frontend: pong
        deactivate WS
        
        Note over Frontend: Connection kept alive
    end
    
    Frontend->>WS: Close connection<br/>Code 1000 (Normal closure)
    
    activate WS
    WS->>WSM: unregister_connection(websocket_id)
    activate WSM
    
    WSM->>WSM: Remove from active connections
    WSM->>WSM: Cleanup event listeners
    
    deactivate WSM
    
    WS->>Frontend: Connection Closed
    deactivate WS
    
    Frontend->>Frontend: Cleanup local state
    Note over Frontend: Connection successfully terminated
```

**Wichtige Aspekte:**
- **Connection Lifecycle**: Etablierung, Erhalt, Beendigung
- **Heartbeat-Mechanismus**: Verhindert Timeout-Probleme
- **Event Streaming**: Kontinuierliche Übertragung von Server-Events
- **Graceful Shutdown**: Ordnungsgemäße Cleanup bei Beendigung

---

## 6.7 Zusammenfassung: Interaktionsmuster

### Wichtigste Erkenntnisse

1. **Event-Driven Patterns**: Das System basiert auf asynchronen Events für lose Kopplung
2. **Bidirektionale Kommunikation**: WebSocket ermöglicht Server-zu-Client Push
3. **Komponentenisolation**: Jeder Service ist unabhängig und kann einzeln getestet werden
4. **Fehlertoleranz**: Timeouts und Fehler werden elegant behandelt
5. **Real-time Responsiveness**: Alle Updates erfolgen in Echtzeit ohne Verzögerung

### Kommunikationskanäle

| Kanal | Richtung | Latenz | Verwendung |
|-------|----------|--------|------------|
| **REST API** | Request-Response | ~50ms | Synchrone Operationen |
| **WebSocket** | Bidirektional | <10ms | Real-time Updates |
| **MQTT** | Publish-Subscribe | ~100ms | IoT-Integration |
| **EventBus** | Publish-Subscribe | <1ms | Interne Backend-Komm. |
| **AsyncIO** | Asynchron | Variabel | Hintergrund-Tasks |

---

## 6.8 Best Practices

### Timeout-Verwaltung
- REST API: 30 Sekunden Timeout
- WebSocket: 60 Sekunden Heartbeat-Interval
- MQTT: QoS 1 für zuverlässige Zustellung

### Error Handling
- Alle Fehler werden mit strukturierten Logs erfasst
- User-Facing Fehler werden im Frontend angezeigt
- Kritische Fehler triggern Benachrichtigungen

### Performance-Optimierungen
- Event-Batching für häufige Updates
- Caching von API-Responses (Weather, Calendar)
- Exponential Backoff bei Retries

