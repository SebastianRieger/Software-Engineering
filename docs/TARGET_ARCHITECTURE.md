# Zielarchitektur

## Architekturentscheidung

Die realistische Zielarchitektur fuer Nimrag ist kein verteiltes Event-System und keine Microservice-Landschaft.
Fuer ein kleines Team und den aktuellen Stand ist ein **modularer Monolith** die richtige Zielstruktur:

- ein Vue-Frontend
- ein FastAPI-Backend
- eine SQLite-Datenbasis fuer Konfiguration und Cache
- optionale Hardware- und MQTT-Adapter
- WebSocket nur fuer echte Push-Faelle

## Leitprinzipien

- State statt DOM-Manipulation im Frontend
- klare API-Contracts zwischen Frontend und Backend
- externe APIs nur ueber Adapter und Repository-Schicht
- Fallback und Cache fuer wetter- und kalendernahe Daten
- Hardware und IoT nur ueber austauschbare Schnittstellen
- einfache Architektur vor theoretischer Vollstaendigkeit
- handzentrierte Gestenerkennung vor vollstaendiger Koerpererkennung

## Zielbild im Ueberblick

```mermaid
flowchart LR
    UI[Vue SPA]
    Store[Layout- und Widget-State]
    API[FastAPI API]
    WS[WebSocket Push]
    App[Application Services]
    Repo[Repositories]
    DB[(SQLite)]
    Ext[Externe APIs]
    Hw[GPIO und MQTT Adapter]

    UI --> Store
    Store --> API
    API --> App
    API --> WS
    App --> Repo
    Repo --> DB
    Repo --> Ext
    App --> Hw
    WS --> UI
```

## Frontend

### Zielstruktur

- `components/manager/` bleibt die UI-Schale fuer Board und Widget-Platzierung
- `components/widgets/` bleibt die Heimat fuer fachliche Widget-Komponenten
- `widgets/registry.ts` bleibt das Manifest fuer datengetriebene Widget-Instanzen
- `services/` bleibt die schlanke HTTP- und WebSocket-Schicht
- `types/` bleibt die lokale Vertrags- und UI-Wiring-Schicht
- `utils/` wird fuer pure Transformationslogik und UI-nahe Helper genutzt
- eine gemeinsame State- oder Composable-Schicht entsteht erst dann, wenn mehrere Widgets oder Screens dieselbe Laufzeitlogik teilen muessen

### Zielverhalten

- Zellen und Widgets werden ueber Datenmodelle beschrieben, nicht ueber direkt manipuliertes HTML
- Widget-Instanzen haben IDs, Typen, Positionen und Einstellungen
- Widget-Registrierung laeuft ueber ein klares Registry-/Manifest-Konzept
- Konfigurationsaenderungen koennen lokal angezeigt und serverseitig gespeichert werden
- Realtime wird zuerst selektiv fuer Status- und Event-Widgets genutzt, nicht sofort als globale Event-Architektur

### Erster umgesetzter Schnitt

- Layout- und Widget-Zuordnung werden im Frontend bereits ueber lokalen Vue-State und ein Widget-Registry-Modul abgebildet
- Ein kleiner API-Client kapselt Wetter- und Konfigurationszugriffe ohne zusaetzliche Client-Bibliothek
- Das Frontend nutzt inzwischen Wetter, Konfiguration und einen ersten Hardware-Status-Slice
- Ein kleiner Helper-Layer in `src/utils` entlastet die groessten Komponenten ohne eine radikal neue Frontend-Struktur einzufuehren

## Backend

### Zielstruktur

- `api/` als flaches HTTP-Paket mit nach Verantwortung gruppierten Endpoint-Dateien
- `schemas/` fuer Request- und Response-Modelle
- `services/` fuer Fachlogik
- `repositories/` fuer Cache, Persistenz und externe Datenquellen
- `adapters/` fuer OpenWeather, Kalender, GPIO und MQTT
- `core/` fuer Konfiguration, Logging und Lifespan

### Zielverhalten

- REST bleibt der Standard fuer Lesen, Schreiben und Konfiguration
- WebSocket pusht nur relevante Statusaenderungen
- Wetter und Kalender laufen ueber Repositories mit Timeout, Retry und Cache
- optionale Features wie Gesten haengen sich als Adapter und fachliche Events an den gemeinsamen Backend-Kanal
- FastAPI-Lifespan initialisiert optionale Hintergrundjobs sauber
- die Dateistruktur soll nicht kuenstlich tief verschachtelt sein; klare Verantwortungsgruppen sind wichtiger als technische Unterordner-Hierarchien

### Gestenarchitektur

- der primäre Erkennungspfad basiert auf MediaPipe Hands und einer handzentrierten Repräsentation statt auf allgemeiner Body- oder Pose-Erkennung
- Tracking und Klassifikation trennen Rohlandmarks, abgeleitete Bewegungsmerkmale, Kandidatenerzeugung und fachliche Gestenentscheidungen
- Bewegungsmerkmale sollen gegen Handgroesse oder Palmspanne skaliert werden, damit die Basiserkennung nicht von fixen Bildkoordinaten allein abhaengt
- Hand, Handgelenk und palmnahe Punkte bilden den Standardpfad; Ellenbogen- oder Armkontext bleibt optional fuer spaetere Erweiterungen
- Gestenparameter sollen als persistierbare Backend-Konfiguration gepflegt werden und nicht nur als starre ENV-Werte existieren
- Gestenereignisse und Statusantworten sollen neben dem Gestentyp auch Confidence und Tracking-Herkunft transportieren koennen
- Laufzeitfehler der Kamera- oder Adapterpfade muessen im Statusmodell sichtbar bleiben und bei transienten Lesefehlern kontrolliert abgefangen werden

### Konfigurationsdomänen

- `layout` bleibt profilspezifisch und beschreibt Widget-Typ, Position und widgetbezogene Settings
- `system` beschreibt allgemeine Systemeinstellungen wie Ort, Koordinaten, Einheiten, Theme und Refresh-Intervall
- beide Domaenen nutzen denselben Router unter `/api/v1/config`, aber getrennte Schemas und getrennte Persistenzkeys

## Geplante Featureerweiterungen

### Kalender-Slice

- Backend: eigener Adapter- und Repository-Pfad mit Cache/Fallback
- API: lesende Kalender-Endpunkte mit klaren Envelope-Vertraegen
- Frontend: zuerst ein read-only Agenda-Widget statt sofort vollwertiger Bearbeitung

### Smart-Home-Slice

- Backend: Geraeteliste, Status-Snapshots und ein kleiner Kommandopfad statt sofortiger Vollintegration
- MQTT bleibt Transportmittel nur fuer reale Geraete, nicht Selbstzweck
- Frontend: zunaechst Status- und Toggle-Widgets fuer wenige konkrete Geraetetypen

### Hardware-Control-Slice

- das heutige Hardware-Widget wird zum kleinen Kontrollzentrum fuer Gesture-, LED-, Voice- und Systemstatus
- Realtime-Events sollen dort gezielt aggregiert werden, statt unkoordiniert auf viele Widgets verteilt zu werden
- echte GPIO- oder Device-Adapter koennen spaeter denselben sichtbaren UI-Vertrag weiter bedienen

### Qualitaets- und Betriebs-Slice

- Frontend-Testbasis fuer Registry, Layout und Hardware-Helfer
- leichte Auth- und Rollenstrategie fuer spaetere Demo- oder Deployment-Szenarien
- bessere Betriebsmetadaten wie Health-, Cache- und Adapterstatus im Backend

## Erweiterungsroadmap

```mermaid
flowchart LR
    Core[Heutiger Kern\nWetter, Config, Hardwarestatus]
    Calendar[Kalender-Slice]
    SmartHome[Smart-Home-Slice]
    Hardware[Hardware-Control-Ausbau]
    Quality[Tests, Auth, Betriebsstatus]

    Core --> Calendar
    Core --> SmartHome
    Core --> Hardware
    Core --> Quality
```

## Persistenz

SQLite ist fuer die naechsten Projektphasen ausreichend und sinnvoll:

- Layout-Konfigurationen
- Widget-Instanzen und Settings
- Wetter- und Kalender-Cache
- spaeter einfache System- und Health-Informationen

## Realtime und Events

Eine schlanke Event-Strategie ist sinnvoll, aber nur intern:

- interne Python-Events oder einfache Service-Callbacks fuer lose Kopplung
- WebSocket fuer UI-Push
- MQTT nur fuer echte Geraete- und Smart-Home-Kommunikation

Nicht Ziel der naechsten Architekturphase:

- Redis Pub/Sub
- Event Sourcing
- CQRS in voller Auspraegung
- universelles Broker-zentriertes System

## Hardware und Smart Home

Hardware wird als austauschbare Adapter modelliert:

- `LedAdapter`
- `MqttAdapter`
- spaeter `VoiceAdapter`
- `GestureAdapter` als optionaler Computer-Vision-Randadapter mit handzentrierter Landmark-Erkennung

Solange keine stabile Hardwareintegration existiert, muessen Mock- oder Null-Adapter verfuegbar sein.

## Fachliche Kernfluesse

### Wetter

1. Frontend fordert Wetterdaten an
2. Backend prueft Cache
3. Falls noetig: externer API-Request mit Timeout
4. Backend liefert normiertes Wettermodell zurueck
5. WebSocket pusht spaetere Aktualisierungen optional an das Frontend

### Konfiguration

1. Nutzer aendert Layout oder Widget-Einstellung
2. Frontend aktualisiert lokalen State
3. Backend speichert Konfiguration in SQLite
4. Frontend laedt Konfiguration beim Start wieder ein

### Wetter mit Systemkonfiguration

1. Frontend laedt die Systemkonfiguration
2. Frontend fordert Wetterdaten mit den konfigurierten Koordinaten an
3. Backend prueft Cache und faellt bei Bedarf kontrolliert auf gecachte Daten zurueck
4. Frontend zeigt Loading-, Fehler- oder Live/Cache-Zustand je nach Rueckgabe

## Qualitaetsziele in realistischer Prioritaet

1. Stabilitaet und klare Contracts
2. Erweiterbarkeit von Widgets
3. Cache/Fallback fuer externe APIs
4. Raspberry-Pi-taugliche Performance
5. erst danach Voice, Gesture und komplexe Smart-Home-Flows
