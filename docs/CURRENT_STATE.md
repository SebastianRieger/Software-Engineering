# Ist-Zustand

## Projektstatus

Die Codebasis ist aktuell kein reiner Architektur-Dummy mehr, sondern ein belastbarer Kernprototyp mit echter Backend-Persistenz, placement-basierter UI-Steuerung, semantischer Gesten-zu-UI-Aktionsschicht und gruener Backend-Testbasis. Sie ist trotzdem noch klar von der Zielarchitektur entfernt, weil mehrere Domaenen nur vorbereitet oder als Platzhalter angelegt sind.

## Frontend

### Vorhanden

- Vue 3 Grundsetup mit schlanker App-Shell
- Grid-Board mit 16 Zellen und zustandsgetriebener Widget-Belegung
- placement-basiertes Grid mit Fokuszustand statt reinem `cell_id`-Denken
- Widget-Shop ueber gemeinsames Widget-Registry-Konzept
- Wetter-Widget mit echter Backend-Anbindung
- Hardware-Widget mit LED-, Gesture-, Voice- und Systemstatus
- Layout-Laden und -Speichern gegen die Backend-Konfigurations-API
- kleiner typisierter Frontend-API-Client fuer Wetter, Konfiguration und Hardware-Endpunkte
- gemeinsamer WebSocket-Client, der jetzt auch im zentralen `ModuleManager` fuer Gesten- und UI-Aktions-Events genutzt wird
- neuer `utils/`-Layer fuer Layout-, Hardware- und Module-Shop-Helfer
- eigener `types/`-Layer fuer Backend-Vertraege plus Widget-Wiring- und Interaktionstypen
- Interaction-Overlay fuer letzten Rohinput, letzte UI-Aktion, Fokus und ArrangeMode
- ArrangeMode zum Verschieben und Skalieren vorhandener Widgets

### Hauptprobleme

- keine Frontend-Tests
- keine gemeinsame State- oder Composable-Schicht fuer spaetere groessere Frontend-Features
- Wetter, Layout/Systemkonfiguration und Hardwarestatus sind integriert, Kalender und Smart Home aber noch nicht
- Systemkonfiguration ist im Frontend noch nicht als eigener Editierfluss ausgebaut
- keine automatisierte Frontend-Testbasis trotz jetzt groesserer Interaktionslogik

## Backend

### Vorhanden

- FastAPI-App mit flachem API-Paket unter `src/api`
- klare Request- und Response-Schemas fuer Wetter, LED, Voice, System und Konfiguration
- SQLite-basierte Persistenz fuer Layout-Konfiguration, System-/Gesture-Config und Wetter-Cache
- Repository-Schicht fuer Konfiguration und Wetterdaten
- Wetter-Endpunkte mit Cache, Timeout-Konfiguration und Fallback auf gecachte Daten
- Konfigurations-Endpunkte fuer Layout, System und Gestenparameter
- Konfigurations-Endpunkte fuer semantische Eingabezuordnungen zwischen Gesten und UI-Aktionen
- System-Status-Endpunkt mit echten Backend-Metadaten
- Gesten-Backend mit aufgeteiltem Tracking-, Detection- und Runtime-Pfad
- gemeinsamer WebSocket-Kanal fuer Realtime-Events wie `GestureDetected` und `UIActionRequested`
- gruene Backend-Testbasis fuer Wetter, LED, Konfiguration, Voice und Gesten

### Hauptprobleme

- Kalender- und Smart-Home-Endpunkte sind weiter Platzhalter
- LED ist aktuell nur als in-memory Mock beziehungsweise einfacher Adapterpfad umgesetzt, nicht als echte Zielhardware-Integration
- die neue API-Struktur ist flach und klarer, aber es gibt noch kein explizites `adapters/`-Paket
- echte Kamera- und Raspberry-Pi-Verifikation fehlt in der automatisierten Testkette
- es gibt noch keine Authentifizierung, keine Rollen und keine produktionsreife Secret-Verwaltung

## Aktueller Gestenstand

- die Erkennung basiert auf einer handzentrierten Tracking-Basis aus Wrist- und palmnahen Landmarken
- Swipe- und Circle-Schwellwerte werden gegen geschaetzte Handgroesse beziehungsweise Palmspanne normalisiert
- zusaetzlich gibt es `swipe_up`, kurze und lange Push-Klicks sowie Zwei-Hand-Zoom
- Tuningparameter fuer Gesten koennen ueber die bestehende Konfigurationspersistenz backendseitig gehalten werden
- Tracking, Klassifikation und Runtime-Orchestrierung sind jetzt in getrennten Service-Dateien organisiert
- der Gestenservice liefert explizitere Fehlerzustaende sowie Confidence-, Tracking- und Zwei-Hand-Metadaten
- zusaetzlich wird eine modality-neutrale `UIAction`-Schicht veroeffentlicht, die das Frontend direkt fuer Fokus, Shop und ArrangeMode nutzen kann
- offene Kernluecken bleiben echte Hardwarevalidierung, moegliche weitere Gestentypen, optionale Arm-/Pose-Erweiterung und spaetere feinere State-Architektur im Frontend

## Integration

Der groesste Bruch liegt weiter zwischen dem belastbaren Kern und den noch fehlenden Verticalschnitten:

- der gemeinsame WebSocket wird im Frontend jetzt sowohl im Hardware-Widget als auch im zentralen Layout-Manager genutzt
- weitere Domänen wie Kalender und Smart Home sind im Frontend noch nicht angebunden
- der produktive UI-Schnitt ist aktuell auf Wetter, Layout/Systemkonfiguration, Hardwarestatus und Gestensteuerung konzentriert

## Aktueller Integrationsstand B1/B2

- `GET/PUT /api/v1/config/layout` und `GET/PUT /api/v1/config/system` sind produktiv angebunden
- `GET/PUT /api/v1/config/gesture-actions` ist produktiv angebunden
- die `app_config`-Tabelle in SQLite trennt Layout-, System- und Gesture-Daten ueber Konfigurationskeys
- Layout wird als placement-basierte Widget-Konfiguration mit Rueckwaertskompatibilitaet fuer `cell_id` gespeichert
- das Frontend nutzt einen kleinen fetch-basierten API-Client fuer Wetter-, Config- und Hardware-Endpunkte
- das Grid rendert Widgets placement-basiert ueber Vue-State statt ueber HTML-Swaps
- das Hardware-Widget konsumiert den gemeinsamen WebSocket fuer Realtime-Status
- der `ModuleManager` konsumiert `GestureDetected` und `UIActionRequested` fuer Fokusnavigation und direkte UI-Steuerung

## Dokumentation

Die aktive Dokumentation und die source-nahen `*Arch.md`-Dateien sind jetzt wieder am Code ausgerichtet. Historische Artefakte im Archiv bleiben weiter wertvoll, sind aber nicht mehr die Quelle der Wahrheit fuer aktuelle Architekturentscheidungen.

## Was erhalten bleiben sollte

- die modulare Widget-Idee
- FastAPI als Backend-Rahmen
- Vue 3 + TypeScript als Frontend-Basis
- die Fokussierung auf Erweiterbarkeit und Raspberry-Pi-Tauglichkeit
- die definierten Qualitaetsziele fuer Fallback, Reaktionszeit und Wartbarkeit
