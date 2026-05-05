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
- dedizierter fullscreen Command-Settings-Flow mit getrennten Arbeitsbereichen fuer `Profiles`, `Mappings`, `Runtime` und `Training`
- browserbasierter Trainingsassistent fuer Musical Audio mit expliziter Browser-Diagnostik, separater Browser-Geraetewahl, Take-Aufnahme, Konturvorschau, Accept/Reject und Template-Ableitung aus freigegebenen Takes
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
- derselbe `CalibrationService` erzeugt fuer Swipe-Familie und `circle` jetzt zusaetzlich DTW-faehige Sequence-Profile aus den aufgenommenen Sample-Sequenzen und aktiviert oder restauriert sie getrennt von den normalen Schwellwerten
- Gestenruntime, die waehrend aktiver Kalibrierung erkannte Samples an den Kalibrierungsdienst weiterleitet und normale UI-Aktionen unterdrueckt
- Gestenruntime mit Shadow-Modus fuer Sequence-Matching: live ausgewählte Bewegungsfenster werden gegen das aktive Profilset verglichen und liefern `sequence_scores`, Distanzen, Margins und Profil-IDs im Statusmodell
- Realtime-Kanal fuer rohe Gestenerkennung, modality-generic `RawInputDetected`, `CommandMatchEvaluated`, semantische UI-Aktionen und Kalibrierungs-Events wie Start, Target-Arming, Sample-Accept, Analyse-Ready und Apply oder Rollback
- gemeinsamer `InputOrchestrator` im Backend, der modality-generic Input-Mappings aus `InputActionConfig` aufloest, Suppression-/Disable-Entscheidungen sichtbar macht und `UIActionRequested` fuer Gesten, Voice und Musical Audio publiziert
- dedizierter `MusicalAudioService`, der fuer Live-Erkennung zwingend `aubio` fuer Pitch/Onset und `DTAIDistance` fuer DTW-Matching nutzt, einen synchronen Runtime-Preflight ausfuehrt und Statuscodes wie `configuration_disabled`, `no_active_artifact`, `device_missing` oder `invalid_sample_rate` explizit meldet
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
- die kanonische Ausfuehrung dieser Gesten ist in `docs/GESTURE_DEFINITIONS.md` festgelegt und wird im Backend als zentrale Gesture-Contracts fuer Runtime-Specs und Video-Tuner gespiegelt
- `services/gesture/tracking.py` liefert Beobachtungen und Pose-Features, `services/gesture/detection.py` bewertet Kandidaten und loest Konflikte auf, `services/gesture/runtime.py` orchestriert nur den Live-Loop und `services/gesture/push_runtime.py` bleibt ein getrennter Spezialpfad fuer Push-Klicks
- `services/gesture/runtime.py` haelt Bewegungsfenster, Two-Hand-History und Post-Fire-Grace inzwischen ueber einen internen Lifecycle-Owner konsistent statt ueber verstreute Listenfelder
- `services/gesture/detection.py` baut einen expliziten `DetectionContext`, leitet Runtime-Specs direkt aus den Gesture-Contracts ab und trennt interne Horizontal-, Vertikal- und Kreis-Kandidatenpfade klarer
- `GestureConfig` ist die aktive persistierte Laufzeitkonfiguration; ENV-Settings liefern nur Defaults vor dem Laden der Backend-Konfiguration
- dieselbe `GestureConfig` steuert inzwischen auch Push-Pose-Heuristiken, Offline-Zyklussegmentierung, Primitive-Schwellen, Resolver-Gewichte und Kandidaten-Geometriegates; Live-Runtime und Video-Tuner laufen dadurch nicht mehr ueber versteckte getrennte Literal-Sets
- erkannte Gesten werden ueber einen gemeinsamen Input-Orchestrator semantisch auf UI-Aktionen gemappt
- erkannte Voice-Kommandos werden zu normalisierten `voice.*`-Raw-Inputs transformiert und ueber dieselbe Orchestrierung auf UI-Aktionen gemappt
- erkannte melodische Muster werden zu `musical_audio.*`-Raw-Inputs normalisiert und ueber dieselbe Orchestrierung auf UI-Aktionen gemappt
- dieselbe Runtime liefert jetzt zusaetzlich Kalibrierungsevidenz wie Konfidenz, Hand, Tracking-Quelle, Trajektorienzusammenfassung, Push-Tiefe, Zoom-Distanz und Dauer
- Kalibrierungssamples enthalten fuer dynamische Einhandgesten jetzt kompakte Sequence-Artefakte mit normalisierten Punkt-, Geschwindigkeits- und Pose-Kanaelen statt nur aggregierter Summary-Metriken
- Schwellwerte koennen aus positiven Live-Wiederholungen profilorientiert neu vorgeschlagen und explizit angewendet oder zurueckgesetzt werden
- Kalibrierungsanalysen liefern jetzt neben Empfehlungen auch einen reviewbaren `gesture_config_patch`, aus dem der Kandidaten-Snapshot und spaeter das eigentliche Apply deterministisch abgeleitet werden
- Primitive-Schwellen wirken jetzt auch tatsaechlich im Resolverpfad: erforderliche Primitives werden gegen ihre jeweilige konfigurierte Schwelle statt nur gegen einen losen globalen Score-Floor bewertet
- `gesture_video_tuner.py` und `gesture_benchmark.py` koennen den heuristischen Lauf jetzt leave-one-out gegen den neuen Sequence-Matcher vergleichen und daraus ein explizites Promotion-Gate fuer den Shadow-Pfad ableiten

## Aktuelle Nicht-Ziele Der Gesture-Konsolidierung

- keine zweite parallele Gestenarchitektur neben `services/gesture/`
- keine globale Einheits-FSM fuer alle Gestenpfade
- keine per-User Live-Gesture-Configs
- kein Event-Broker als primaere Infrastruktur
- kein automatisches Training oder automatisches Anwenden von Suggestions ohne Review

## Command- und Training-Stand

- `GET/PUT /api/v1/config/command-profiles` verwaltet modality-weite Enablement-, Mapping- und Device-Ownership pro aktivem Profil
- `GET/PUT /api/v1/config/musical-audio` und die zugehoerigen Artefakt-Endpunkte verwalten Runtime-Tuning und kompakte Few-Shot-Templates; `enabled`, `device_index` und `active_artifact_id` werden als Runtime-Sicht aus dem aktiven Command-Profil abgeleitet
- das Frontend kann mehrere browserseitig aufgenommene Takes analysieren, freigeben oder verwerfen und daraus ein neues Artefakt-Template ableiten
- das aktive Musical-Audio-Artefakt und die Backend-Geraeteauswahl werden explizit im aktiven Command-Profil gehalten; die Runtime-Konfiguration beschreibt nur noch Tuning und validierte Startparameter

## Musical-Audio-Betriebsmodell

- Browser-Training und Backend-Live-Runtime sind absichtlich getrennte Betriebsarten mit unterschiedlicher Geraete- und Fehlerlogik
- Browser-Training nutzt `getUserMedia` und Web Audio, zeigt Preflight-Diagnostik fuer Kontext, Permissions und Browser-Geraete und kann ein anderes Mikrofon verwenden als die Backend-Runtime
- Backend-Live-Runtime nutzt `sounddevice`, fuehrt vor dem Thread-Start einen Geraete-/Sample-Rate-Preflight aus und exponiert validierte Kombinationen ueber `validated_device_index` und `validated_sample_rate`
- der Command-Settings-Flow macht die Ownership sichtbar: Aktivierung, aktives Runtime-Artefakt und Backend-Geraet kommen aus `CommandProfile`, Sample-Rate und Matching-Tuning aus `MusicalAudioConfig`

## Kalibrierungsstand

- `GET /api/v1/calibration/definitions` liefert aktuell die vordefinierten Gestenziele
- `POST /api/v1/calibration/sessions` startet eine Gesten-Kalibrierung mit Profilname, einem oder mehreren Ziel-IDs und Wiederholungszahl
- `GET /api/v1/calibration/sessions/{id}` liefert Fortschritt und Analysezustand
- `POST /complete`, `POST /apply`, `POST /rollback` und `POST /cancel` bilden den vollen Lifecycle fuer Review, Apply, Restore und Discard ab
- der Gestenpfad unterstuetzt vorbereitete Takes, Recording-Start/Stop, Review, Accept und Discard vor dem eigentlichen Apply auf die aktive Config
- die Persistenz speichert Sitzungen, Profile und deterministische Vorher-Nachher-Snapshots fuer Rollback
- zusaetzlich wird das aktuell aktive Gesture-Sequence-Profilset separat persistiert, damit Apply und Rollback dieselben Referenzen fuer den Shadow- oder spaeteren Promotion-Pfad wiederherstellen koennen
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