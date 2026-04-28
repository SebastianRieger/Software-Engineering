# Ist-Zustand

## Projektstatus

Die Codebasis ist jetzt ein belastbarer Kernprototyp mit echter Backend-Persistenz, placement-basierter Frontend-Steuerung, semantischer Eingabeschicht fuer Gesten und einem voll integrierten In-App-Kalibrierungsmodus fuer vordefinierte Gesten. Die Architektur bleibt bewusst auf Erweiterbarkeit ausgelegt: Sitzungen, Persistenz und Realtime-Feedback der Kalibrierung sind modality-generic modelliert, auch wenn aktuell nur Gesten produktiv implementiert sind.

## Frontend

### Vorhanden

- Vue-3-Frontend mit zustandsgetriebenem Grid-Board, Widget-Registry und placement-basierter Layoutpersistenz
- zentraler `ModuleManager` fuer Fokus, Shop, ArrangeMode, Tastatur-Fallback und Realtime-Eingaben
- fetch-basierter API-Client fuer Layout-, System-, Hardware- und jetzt auch Kalibrierungsendpunkte
- gemeinsamer WebSocket-Client fuer `GestureDetected`, `UIActionRequested` und Kalibrierungs-Lifecycle-Events
- eigener Kalibrierungswizard im laufenden UI-Flow mit Profilauswahl, Zielauswahl, Fortschrittsanzeige, Analyse-Review, Apply und Discard
- explizite Sperre normaler Fokus-, Shop- und ArrangeMode-Interaktionen waehrend aktiver Kalibrierung
- Hardware-Widget mit echter Kamera- und Mikrofon-Geraeteliste, expliziter Auswahl und direkten Start/Stop-Kontrollen fuer beide Pfade

### Hauptprobleme

- weiterhin keine automatisierte Frontend-Testbasis
- noch keine gemeinsame Store- oder Composable-Schicht fuer groessere UI-Features
- Kalender- und Smart-Home-Vertikalen sind im Frontend weiter nicht ausgebaut
- die Kalibrierungsoberflaeche ist funktional, aber noch kein eigenstaendiger Einstellungsbereich mit Session-Historie

## Backend

### Vorhanden

- FastAPI-Backend mit klar getrennten Routern fuer Daten-, Device-, Config-, Gesture- und jetzt Calibration-Endpunkte
- SQLite-basierte Persistenz ueber `app_config` fuer Layout, System, Gesture-Config, Voice-Config, Input-Mappings und Kalibrierungsdaten
- dedizierter `CalibrationService` fuer Session-Lifecycle, positive Sample-Aufnahme, Analyse, Apply, Rollback und Discard
- Gestenruntime, die waehrend aktiver Kalibrierung erkannte Samples an den Kalibrierungsdienst weiterleitet und normale UI-Aktionen unterdrueckt
- Realtime-Kanal fuer rohe Gestenerkennung, semantische UI-Aktionen und Kalibrierungs-Events wie Start, Target-Arming, Sample-Accept, Analyse-Ready und Apply oder Rollback
- gruene Backend-Testbasis fuer Persistenz, API-Lifecycle, Rollback, Konfliktverhalten, WebSocket-Ereignisse und Runtime-Gating
- Device-Endpunkte fuer reale Kamera- und Audio-Input-Erkennung, damit mehrere angeschlossene Geraete im UI gezielt gewaehlt werden koennen

### Hauptprobleme

- Voice-Kalibrierung ist strukturell vorbereitet, aber absichtlich noch nicht implementiert
- Kalender- und Smart-Home-Endpunkte bleiben Platzhalter
- die Kalibrierungsanalyse ist bewusst heuristisch und profilorientiert, nicht lernbasiert
- es gibt weiterhin keine Authentifizierung, Rollen oder produktionsreife Secret-Verwaltung

## Aktueller Gestenstand

- die Gestenerkennung basiert auf handzentriertem Tracking mit Handgroessen-Normalisierung
- unterstuetzt werden `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down`, `circle`, `push_click_short`, `push_click_long`, `zoom_out_hands` und `zoom_in_hands`
- erkannte Gesten werden semantisch auf UI-Aktionen gemappt
- dieselbe Runtime liefert jetzt zusaetzlich Kalibrierungsevidenz wie Konfidenz, Hand, Tracking-Quelle, Trajektorienzusammenfassung, Push-Tiefe, Zoom-Distanz und Dauer
- Schwellwerte koennen aus positiven Live-Wiederholungen profilorientiert neu vorgeschlagen und explizit angewendet oder zurueckgesetzt werden

## Kalibrierungsstand

- `GET /api/v1/calibration/definitions` liefert aktuell die vordefinierten Gestenziele
- `POST /api/v1/calibration/sessions` startet eine Gesten-Kalibrierung mit Profilname, Zielmenge und Wiederholungszahl
- `GET /api/v1/calibration/sessions/{id}` liefert Fortschritt und Analysezustand
- `POST /complete`, `POST /apply`, `POST /rollback` und `POST /cancel` bilden den vollen Lifecycle fuer Review, Apply, Restore und Discard ab
- die Persistenz speichert Sitzungen, Profile und deterministische Vorher-Nachher-Snapshots fuer Rollback
- normale Schreibzugriffe auf die Gesture-Config werden waehrend aktiver Kalibrierung gesperrt

## Dokumentation

Die aktive Dokumentation ist auf die aktuelle Implementierung ausgerichtet. Quelle der Wahrheit sind jetzt die `*Arch.md`-Dateien in den betroffenen Code-Modulen sowie diese Statusseite und die beiden operativen Runbooks fuer Demo und Gestenvalidierung.

## Was erhalten bleiben sollte

- die modulare Widget-Idee
- FastAPI als Backend-Rahmen
- Vue 3 plus TypeScript als Frontend-Basis
- die explizite Trennung zwischen roher Eingabe, semantischer UI-Aktion und Kalibrierungsfeedback
- der SQLite-basierte, nachvollziehbare Persistenzpfad fuer Konfiguration und Profile