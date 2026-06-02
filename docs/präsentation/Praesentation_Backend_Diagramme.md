# Nimrag – Präsentation: Backend & Gestensteuerung
## Diagramme & Visualisierungen (Stand: Code-Basis 2026)

> Alle Diagramme basieren direkt auf dem aktuellen Quellcode (`Backend/src`).
> Nicht auf ältere Docs-Dateien verlassen — diese sind teilweise veraltet.

---

# PRÄSENTATION — Vereinfachte Diagramme

> Diese drei Diagramme sind für die 5-Minuten-Präsentation optimiert:
> wenig Text, klare Struktur, keine technischen Details.

---

## P1. System-Architektur — High-Level-Überblick

```mermaid
graph LR
    CAM([Kamera]) -->|Videobild| BE

    subgraph BE["Backend"]
        GE[Gestensteuerung]
        DAT[Daten & Widgets]
        DB[(Datenbank)]
        GE --> DB
        DAT --> DB
    end

    BE -->|Echtzeit-Events| FE
    FE -->|Einstellungen| BE

    subgraph FE["Frontend"]
        GRID[Widget-Grid]
    end

    style CAM fill:#2c3e50,color:#fff
    style GE fill:#8e44ad,color:#fff
    style DAT fill:#2980b9,color:#fff
    style GRID fill:#27ae60,color:#fff
```

---

## P2. Gestensteuerung — Ablauf

```mermaid
graph LR
    A([Kamera]) --> B[Hand erkannt]
    B --> C[Cursor aktiv]
    C --> D{Eingabe}
    D -->|Wischen| E[Widget wechseln]
    D -->|Kreis| F[Aktion bestätigen]
    D -->|Cursor halten| G[Button klicken]
    D -->|Pinch| H[Widget greifen]
    E --> I([Frontend reagiert])
    F --> I
    G --> I
    H --> I

    style A fill:#2c3e50,color:#fff
    style C fill:#8e44ad,color:#fff
    style I fill:#27ae60,color:#fff
```

---

## P3. Pinch-to-Move — Widget verschieben

```mermaid
graph LR
    A([Finger gespreizt]) --> B["Daumen & Zeigefinger<br/>zusammenführen"]
    B --> C[Widget gegriffen]
    C --> D["Hand bewegen —<br/>Widget folgt Cursor"]
    D --> E[Finger öffnen]
    E --> F{Zielfeld frei?}
    F -->|Ja| G([Widget abgelegt])
    F -->|Belegt| H([Widgets tauschen Plätze])

    style A fill:#2c3e50,color:#fff
    style C fill:#8e44ad,color:#fff
    style G fill:#27ae60,color:#fff
    style H fill:#27ae60,color:#fff
```

---

---

# ENTWICKLER-REFERENZ — Vollständige Diagramme

> Die folgenden Diagramme sind für Dokumentation und Entwicklerhandbuch gedacht,
> nicht für die Präsentation.

---

## 1. Systemarchitektur – Gesamtüberblick

```mermaid
graph TD
    Camera[📷 USB-Kamera] -->|Video-Stream| GS
    User[👤 Nutzer\nGesten / Sprache]

    subgraph Frontend["Frontend (Vue.js)"]
        UI[Widgets & Grid-UI]
    end

    subgraph Backend["Backend (FastAPI · Python 3.12)"]
        direction TB

        WS["/ws\nWebSocket-Endpunkt"]
        APILayer["API Layer\nsystem_endpoints · device_endpoints\ndata_endpoints · api_v1/..."]

        subgraph Core["core/"]
            RH["RealtimeHub\nEvent-Bus"]
            CFG["config.py\nSettings + 150+ Gesture-Parameter"]
            DB["database.py\nSQLite Init"]
        end

        subgraph Services["services/"]
            GS["GestureService\nruntime.py\n(Orchestrator-Thread)"]
            CS["CalibrationService\ncalibration.py"]
            IO["InputOrchestrator\ninput/orchestrator.py"]
            VS["VoiceService\nvoice.py"]
        end

        subgraph GestureSubsystem["services/gesture/ (Gestensubsystem)"]
            TR["tracking.py\nMediaPipe · Landmarks · Cursor"]
            DT["detection.py\nFeature-Extraktion · Scoring"]
            CT["contracts.py\nGestureContract (Single Source of Truth)"]
            PR["push_runtime.py\nState-Machine: Push-Klick"]
            PIR["pinch_runtime.py\nState-Machine: Pinch"]
            SM["sequence_matcher.py\nDTW-basiertes Profil-Matching"]
        end

        subgraph Repositories["repositories/"]
            CR["ConfigRepository\nKey-Value-Store (SQLite)"]
            WR["WeatherRepository · NewsRepository · ..."]
        end

        SQLite[("nimrag.db\nSQLite")]
    end

    User -->|Geste| Camera
    Frontend -->|REST-Requests| APILayer
    Frontend -->|WebSocket connect| WS
    WS <-->|JSON-Events| RH
    APILayer --> Services
    GS --> TR
    TR -->|GestureObservation| GS
    GS --> DT
    DT --> CT
    GS --> PR
    GS --> PIR
    GS --> SM
    GS -->|publish_from_thread| RH
    CS --> RH
    IO --> RH
    VS --> IO
    GS --> IO
    Services --> Repositories
    Repositories --> SQLite
```

---

## 2. Gesture Detection Pipeline – Sequenzdiagramm

```mermaid
sequenceDiagram
    participant Cam as 📷 Kamera
    participant TR as tracking.py<br/>(MediaPipe)
    participant RT as runtime.py<br/>(GestureService)
    participant DT as detection.py<br/>(Klassifikation)
    participant IO as InputOrchestrator
    participant RH as RealtimeHub
    participant FE as Frontend

    Cam->>TR: Video-Frame
    TR->>TR: MediaPipe:<br/>21 Hand-Landmarks
    TR->>TR: extract_hand_pose_features()<br/>→ push_depth, hand_openness,<br/>index_extension_ratio, center_distance
    TR->>TR: compute_hand_tracking_point()<br/>→ Cursor-Position (Index-Fingerspitze)
    TR-->>RT: GestureObservation

    RT->>RT: Smoothing (EMA α=0.6)<br/>+ Trajectory anhängen (max. 64 Punkte)

    RT->>DT: analyze_runtime_gesture(<br/>trajectory, pose_features)

    DT->>DT: extract_gesture_features()<br/>→ dx/dy, radius_mean, total_sweep

    DT->>DT: extract_temporal_gesture_window()<br/>→ Phase: preparing → committing → releasing

    DT->>DT: detect_gesture_primitives()<br/>→ circular_motion? swipe_vector_left?<br/>index_primary? pinch_contact?

    DT->>DT: detect_gesture_candidates()<br/>→ GestureContract prüfen<br/>(required_primitives · allowed_phases)

    DT->>DT: select_best_gesture_candidate()<br/>→ score × priority → Winner

    DT-->>RT: GestureDetectionResult

    RT->>RT: Cooldown-Check (0.55s)<br/>+ Phase-Gate

    RT->>IO: publish_raw_input_detected(<br/>source="camera", raw_input="swipe_left")

    IO->>IO: Mapping prüfen<br/>gesture → UIAction<br/>+ Repeat-Window (250ms)

    IO->>RH: UIActionRequested {action, args}
    RH->>FE: WebSocket JSON-Event
    Note over FE: Widget wechseln / verschieben / bestätigen
```

---

## 3. Pinch-to-Move – Interaktionsablauf

```mermaid
sequenceDiagram
    participant User as 👤 Nutzer
    participant RT as runtime.py
    participant PIR as pinch_runtime.py
    participant RH as RealtimeHub
    participant FE as Frontend

    User->>RT: Zeigefinger + Daumen zusammenführen
    RT->>PIR: detect_pinch_gesture(pose_features)
    PIR->>PIR: distance < PINCH_CLOSE_THRESHOLD (0.30)<br/>→ Zustand: pinch_close FIRE
    PIR-->>RT: GestureType = "pinch_close"
    RT->>RH: publish "pinch_close" + Cursor-Position
    RH->>FE: UIActionRequested {action: "grab_widget"}
    Note over FE: Widget wird "gegriffen"

    loop Während Pinch gehalten
        RT->>RH: Cursor-Position (Index-Fingerspitze)
        RH->>FE: Cursor-Update
        Note over FE: Widget folgt dem Cursor
    end

    User->>RT: Finger öffnen (Daumen + Zeigefinger auseinander)
    RT->>PIR: detect_pinch_gesture(pose_features)
    PIR->>PIR: distance > PINCH_OPEN_THRESHOLD (0.52)<br/>→ Zustand: pinch_open FIRE
    PIR-->>RT: GestureType = "pinch_open"
    RT->>RH: publish "pinch_open"
    RH->>FE: UIActionRequested {action: "release_widget"}
    Note over FE: Widget wird an neuer Position abgelegt
```

---

## 4. Kalibrierungs-Workflow

```mermaid
graph LR
    A([Session\nstarten]) --> B[Geste auswählen\n11 Gesten × 10–20 Samples]
    B --> C[Sample\naufnehmen]
    C --> D{Accept /<br/>Discard?}
    D -->|Discard| C
    D -->|Accept| E[Nächste Geste]
    E --> B
    E -->|Alle Gesten fertig| F

    F[Analyse-Phase] --> G[Distanzmatrix\nO n²]
    G --> H[Medoid-Auswahl\n→ repräsentativstes Sample]
    H --> I[DTW-Threshold\n= P90 der Abstände]
    I --> J{Apply?}
    J -->|Ja| K[(GestureConfig\nin SQLite persistieren)]
    J -->|Rollback| L[(Vorherige Config\nwiederherstellen)]

    K --> M([Aktive Runtime\nnutzt neues Profil])

    style F fill:#4a90d9,color:#fff
    style K fill:#27ae60,color:#fff
    style L fill:#e74c3c,color:#fff
```

---

## 5. WebSocket Real-Time Event Flow

```mermaid
graph LR
    subgraph Threads["Background-Threads"]
        GT[GestureService\nThread]
        VT[VoiceService\nThread]
    end

    subgraph AsyncIO["FastAPI AsyncIO Event Loop"]
        RH[RealtimeHub\nasyncio.Queue\npro Client]
        WS[ws\nWebSocket-Handler]
    end

    GT -->|publish_from_thread\nrun_coroutine_threadsafe| RH
    VT -->|publish_from_thread| RH
    RH -->|await queue.get| WS
    WS -->|send_json| FE[Frontend\nWebSocket-Client]

    style GT fill:#8e44ad,color:#fff
    style VT fill:#8e44ad,color:#fff
    style RH fill:#2980b9,color:#fff
```

---

## 6. Gesture-Subsystem: Zuständigkeiten (Ownership-Grenzen)

```mermaid
graph TD
    subgraph "GestureService (runtime.py) — Orchestrator"
        LOOP[Gesture-Loop\n~30 FPS]
        COOL[Cooldown-Manager\n0.55s zwischen Events]
        CAP[Calibration-Sample-Capture\nbei aktiver Kalibrierung]
    end

    subgraph "detection.py — einziger Klassifikations-Owner"
        FEAT[Feature-Extraktion\ndx/dy, radius, sweep]
        PHASE[Phasen-Klassifikation\nidle → preparing → committing → releasing]
        PRIM[Primitive-Scoring\ncircular_motion, swipe_vector_*, index_primary...]
        CAND[Kandidaten-Auswertung\nGestureContract-Check]
        WIN[Sieger-Selektion\nscore × priority]
    end

    subgraph "tracking.py — MediaPipe-Adapter"
        MP[MediaPipe\nHand Landmarker]
        POSE[HandPoseFeatures\npush_depth, openness, index_ext...]
        CURSOR[Cursor-Position\nindex_tip Landmark]
    end

    subgraph "contracts.py — Single Source of Truth"
        CON[GestureContract × 11\nrequired_primitives, score_threshold,\npriority, allowed_phases]
    end

    subgraph "Spezialisierte State-Machines"
        PUSH[push_runtime.py\npush_click_short / long]
        PINCH[pinch_runtime.py\npinch_close / pinch_open]
    end

    LOOP -->|GestureObservation| FEAT
    MP --> POSE
    MP --> CURSOR
    POSE --> LOOP
    FEAT --> PHASE
    PHASE --> PRIM
    PRIM --> CAND
    CON -->|Referenz| CAND
    CAND --> WIN
    WIN --> COOL
    LOOP --> PUSH
    LOOP --> PINCH
    COOL -->|Event fire| IO[InputOrchestrator]
```

---

## 7. Tech-Stack-Tabelle

| Komponente | Technologie | Zweck |
|---|---|---|
| Framework | FastAPI (Python 3.12) | REST-API + WebSocket |
| Hand-Tracking | MediaPipe Hand Landmarker | 21 Landmarks pro Hand |
| Persistenz | SQLite (nimrag.db) | Config, Cache, Sessions |
| Config-Contracts | Pydantic BaseSettings | 150+ Gesture-Parameter |
| Datenvalidierung | Pydantic v2 Models | Typ-Sicherheit über alle Layer |
| Realtime | asyncio.Queue + WebSocket | Event-Broadcasting |
| Sequenz-Matching | DTW (dtaidistance) | Nutzer-Profile für Kalibrierung |
| Threading | Python threading + RLock | Gesture-Loop im Hintergrund |

---

## 8. Gesten-Übersicht (Alle implementierten Gesten)

| Geste | Priorität | Threshold | Typ | Präsentation |
|---|---|---|---|---|
| `pinch_close` | 70 | 0.0 | Pinch SM | ✅ Kern-Geste |
| `pinch_open` | 70 | 0.0 | Pinch SM | ✅ Kern-Geste |
| `push_click_long` | 60 | 0.58 | Push SM | technisch |
| `push_click_short` | 55 | 0.56 | Push SM | technisch |
| `circle` | 45 | 0.52 | Detection | ✅ Kern-Geste |
| `zoom_out_hands` | 50 | 0.54 | Detection (2-Hand) | technisch |
| `zoom_in_hands` | 50 | 0.54 | Detection (2-Hand) | technisch |
| `swipe_left` | 40 | 0.40 | Detection | ✅ Kern-Geste |
| `swipe_right` | 40 | 0.40 | Detection | ✅ Kern-Geste |
| `swipe_up` | 38 | 0.40 | Detection | technisch |
| `swipe_down` | 38 | 0.40 | Detection | technisch |

---

## 9. DTW – Dynamic Time Warping (kurze visuelle Erklärung)

```
Naive Distanz (schlecht):          DTW (richtig):
                                   
 A: ──●──●──●──●                  A: ──●──●──●──●
    |  |  |  |                        ╲  │  │  ╱
 B: ──●──●──●──●                  B: ──●──●──●──●
                                   
 Zeitversatz → hohe Distanz       Elastisches Matching → korrekte Distanz
```

**Im Code:** `dtaidistance.dtw_ndim.distance_fast()` mit 8 parallelen Kanälen:
`x, y, velocity_x, velocity_y, hand_openness, index_extension_ratio, push_depth, center_distance`

Zweck: Wenn ein Nutzer eine Geste schneller oder langsamer ausführt als das gespeicherte Referenzprofil, erkennt DTW sie trotzdem korrekt.

---

## 10. Modularer Monolith – Bewusste Architekturentscheidung

```mermaid
graph LR
    subgraph "Verworfen: Microservices"
        MS1[Gesture-Service\n:8001]
        MS2[Voice-Service\n:8002]
        MS3[Config-Service\n:8003]
        MS4[Realtime-Service\n:8004]
        MS1 <-->|HTTP/gRPC| MS2
        MS2 <-->|HTTP/gRPC| MS3
        MS3 <-->|HTTP/gRPC| MS4
    end

    subgraph "Gewählt: Modularer Monolith"
        MM[FastAPI Backend\n:8000\nalle Services als Python-Module\ngeteilter In-Process Event-Bus]
    end

    PRO[✅ Vorteile:\n- Keine Netzwerk-Latenz\n- Kein Service-Discovery\n- Ein Deployment\n- Kleines Team: 5 Personen\n- Klare Layer-Grenzen trotzdem möglich]

    MM --- PRO
```
