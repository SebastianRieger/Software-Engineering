# Ist-Zustand

## Projektstatus

Die Codebasis ist jetzt ein belastbarer Kernprototyp mit echter Backend-Persistenz, placement-basierter Frontend-Steuerung, gemeinsamer Command-Konfiguration fuer mehrere Modalitaeten und einem integrierten In-App-Kalibrierungs- und Trainingspfad. Neben Gesten ist Voice semantisch bis zur UI-Aktionsschicht integriert; zusaetzlich existiert jetzt ein erster Musical-Audio-Pfad fuer pfeif- oder melodiebasierte Commands mitsamt Template-Artefakten und Few-Shot-Training im Settings-Flow.

## Frontend

### Vorhanden

- Vue-3-Frontend mit zustandsgetriebenem Grid-Board, Widget-Registry und placement-basierter Layoutpersistenz
- zentraler `ModuleManager` fuer Fokus, Shop, ArrangeMode und Realtime-Eingaben, jetzt mit extrahiertem testbarem Interaction-Reducer fuer die eigentlichen UI-Zustandsuebergaenge
- fetch-basierter API-Client fuer Layout-, System-, Hardware- und jetzt auch Kalibrierungsendpunkte
- gemeinsamer WebSocket-Client fuer `GestureDetected`, `RawInputDetected`, `CommandMatchEvaluated`, `UIActionRequested`, `VoiceCommandDetected` und Kalibrierungs-Lifecycle-Events
- eigener Kalibrierungswizard im laufenden UI-Flow mit Profilauswahl, Zielauswahl, Fortschrittsanzeige, Analyse-Review, Apply und Discard
- dediziertes Command-Settings-Panel fuer aktive Command-Profile, modality-weite Mappings, Geraete-Praeferenzen und Musical-Audio-Artefakte
- browserbasierter Trainingsassistent fuer Musical Audio mit Take-Aufnahme, Konturvorschau, Accept/Reject und Template-Ableitung aus freigegebenen Takes
- explizite Sperre normaler Fokus-, Shop- und ArrangeMode-Interaktionen waehrend aktiver Kalibrierung
- Hardware-Widget mit direkten Start/Stop-Kontrollen, dessen Kamera- und Mikrofonwahl jetzt aus dem aktiven Command-Profil statt aus widget-lokalen Settings kommt

### Hauptprobleme

- erste automatisierte Frontend-Testbasis fuer den extrahierten Interaction-Reducer ist vorhanden; groessere Manager- und Realtime-Flows fehlen aber weiter
- noch keine gemeinsame Store- oder Composable-Schicht fuer groessere UI-Features
- Kalender- und Smart-Home-Vertikalen sind im Frontend weiter nicht ausgebaut
- der Trainingsflow speichert derzeit kompakte Kontur-Templates statt roher Audioaufnahmen; eine spaetere erweiterte Session-Historie ist noch offen

## Backend

### Vorhanden

- FastAPI-Backend mit klar getrennten Routern fuer Daten-, Device-, Config-, Gesture-, Voice-, Musical-Audio- und Calibration-Endpunkte
- SQLite-basierte Persistenz ueber `app_config` fuer Layout, System, Gesture-Config, Voice-Config, Command-Profile, Musical-Audio-Config, Training-Artefakte, Input-Mappings und Kalibrierungsdaten
- dedizierter `CalibrationService` fuer Session-Lifecycle, positive Sample-Aufnahme, Analyse, Apply, Rollback und Discard
- Gestenruntime, die waehrend aktiver Kalibrierung erkannte Samples an den Kalibrierungsdienst weiterleitet und normale UI-Aktionen unterdrueckt
- Realtime-Kanal fuer rohe Gestenerkennung, modality-generic `RawInputDetected`, `CommandMatchEvaluated`, semantische UI-Aktionen und Kalibrierungs-Events wie Start, Target-Arming, Sample-Accept, Analyse-Ready und Apply oder Rollback
- gemeinsamer `InputOrchestrator` im Backend, der modality-generic Input-Mappings aus `InputActionConfig` aufloest, Suppression-/Disable-Entscheidungen sichtbar macht und `UIActionRequested` fuer Gesten, Voice und Musical Audio publiziert
- dedizierter `MusicalAudioService`, der fuer Live-Erkennung zwingend `aubio` fuer Pitch/Onset und `DTAIDistance` fuer DTW-Matching nutzt und Training-Artifact-Ladung aus der Konfigurationspersistenz bezieht
- gruene Backend-Testbasis fuer Persistenz, API-Lifecycle, Rollback, Konfliktverhalten, WebSocket-Ereignisse und Runtime-Gating
- Device-Endpunkte fuer reale Kamera- und Audio-Input-Erkennung, damit mehrere angeschlossene Geraete im aktiven Command-Profil hinterlegt und von dort aus runtimeseitig verwendet werden koennen

### Hauptprobleme

- Voice-Kalibrierung ist strukturell vorbereitet, aber absichtlich noch nicht implementiert
- Voice ist jetzt semantisch bis zur gemeinsamen UI-Aktionsschicht integriert; die Kalibrierung fuer Voice fehlt weiterhin
- Kalender- und Smart-Home-Endpunkte bleiben Platzhalter
- die Kalibrierungsanalyse ist bewusst heuristisch und profilorientiert, nicht lernbasiert
- es gibt weiterhin keine Authentifizierung, Rollen oder produktionsreife Secret-Verwaltung

## Aktueller Gestenstand

- die Gestenerkennung basiert auf handzentriertem Tracking mit Handgroessen-Normalisierung
- unterstuetzt werden `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down`, `circle`, `push_click_short`, `push_click_long`, `zoom_out_hands` und `zoom_in_hands`
- erkannte Gesten werden ueber einen gemeinsamen Input-Orchestrator semantisch auf UI-Aktionen gemappt
- erkannte Voice-Kommandos werden zu normalisierten `voice.*`-Raw-Inputs transformiert und ueber dieselbe Orchestrierung auf UI-Aktionen gemappt
- erkannte melodische Muster werden zu `musical_audio.*`-Raw-Inputs normalisiert und ueber dieselbe Orchestrierung auf UI-Aktionen gemappt
- dieselbe Runtime liefert jetzt zusaetzlich Kalibrierungsevidenz wie Konfidenz, Hand, Tracking-Quelle, Trajektorienzusammenfassung, Push-Tiefe, Zoom-Distanz und Dauer
- Schwellwerte koennen aus positiven Live-Wiederholungen profilorientiert neu vorgeschlagen und explizit angewendet oder zurueckgesetzt werden

## Command- und Training-Stand

- `GET/PUT /api/v1/config/command-profiles` verwaltet modality-weite Enablement-, Mapping- und Device-Ownership pro aktivem Profil
- `GET/PUT /api/v1/config/musical-audio` und die zugehoerigen Artefakt-Endpunkte verwalten Runtime-Defaults und kompakte Few-Shot-Templates
- das Frontend kann mehrere browserseitig aufgenommene Takes analysieren, freigeben oder verwerfen und daraus ein neues Artefakt-Template ableiten
- das aktive Musical-Audio-Artefakt wird explizit im Command-Profil und in der Runtime-Konfiguration markiert, statt nur implizit ueber manuelle Notenedits zu existieren

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
- die modality-generic Input-Orchestrierung im Backend und der testbare lokale Interaction-Reducer im Frontend
- der SQLite-basierte, nachvollziehbare Persistenzpfad fuer Konfiguration und Profile