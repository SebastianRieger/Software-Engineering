# Nimrag Smart Mirror  
## Risk Mitigation, Monitoring and Management (RMMM)

**Version:** 1.0  
**Datum:** 30.06.2026  
**Autoren:** Sebastian, Jannik, Jan, Louis  
**Status:** Abgeschlossen (Projektabgabe)

---

## Revision History

| Datum       | Version | Beschreibung                           | Autor(en)                     |
|-------------|---------|----------------------------------------|-------------------------------|
| 30.06.2026  | 1.0     | Initiales RMMM zum Projektabschluss   | Sebastian, Jannik, Jan, Louis |

---

## Inhaltsverzeichnis

1. [Einleitung](#1-einleitung)
2. [Risikobewertungsschema](#2-risikobewertungsschema)
3. [Risk Management Table](#3-risk-management-table)
   - 3.1 [Technische Risiken](#31-technische-risiken)
   - 3.2 [Externe Abhängigkeiten / API-Risiken](#32-externe-abhängigkeiten--api-risiken)
   - 3.3 [Hardware-Risiken](#33-hardware-risiken)
   - 3.4 [Projektmanagement-Risiken](#34-projektmanagement-risiken)
   - 3.5 [Sicherheits- und Datenschutzrisiken](#35-sicherheits--und-datenschutzrisiken)
4. [Risiko-Übersichtsmatrix](#4-risiko-übersichtsmatrix)
5. [Realisierte Risiken und Projekterfahrungen](#5-realisierte-risiken-und-projekterfahrungen)

---

## 1. Einleitung

Dieses Dokument beschreibt das Risikomanagement für das **Nimrag Smart Mirror**-Projekt. Es identifiziert, bewertet und beschreibt Maßnahmen zur Minderung, Überwachung und Behandlung von Risiken über den gesamten Projektverlauf (Oktober 2025 – Juni 2026).

Das RMMM folgt dem RUP-Schema mit den Phasen:
- **Mitigation (M)**: Maßnahmen zur Reduzierung der Eintrittswahrscheinlichkeit
- **Monitoring (Mo)**: Mechanismen zur frühzeitigen Erkennung
- **Management (Ma)**: Reaktionsplan falls das Risiko eintritt

**Projektkontext:** Raspberry Pi-basierter Smart Mirror mit Vue 3 Frontend, FastAPI Backend, Vosk ASR, MediaPipe Gestenerkennung, Aubio Audioerkennung, GPIO LED-Steuerung und mehreren externen APIs.

---

## 2. Risikobewertungsschema

### Wahrscheinlichkeit (Probability)

| Wert | Bezeichnung | Bedeutung |
|------|-------------|-----------|
| 1    | Sehr gering | < 10% – tritt sehr selten auf |
| 2    | Gering      | 10–30% – unwahrscheinlich |
| 3    | Mittel      | 30–50% – möglich |
| 4    | Hoch        | 50–70% – wahrscheinlich |
| 5    | Sehr hoch   | > 70% – sehr wahrscheinlich |

### Auswirkung (Impact)

| Wert | Bezeichnung | Bedeutung |
|------|-------------|-----------|
| 1    | Trivial     | Kaum spürbare Auswirkung auf Projekt/System |
| 2    | Gering      | Geringfügige Beeinträchtigung, leicht behebbar |
| 3    | Mittel      | Merkliche Beeinträchtigung, erhöhter Aufwand |
| 4    | Hoch        | Schwere Beeinträchtigung, wesentliche Teile des Projekts betroffen |
| 5    | Kritisch    | Projektziel gefährdet oder unerfüllbar |

### Risiko-Exposure (RE)

**RE = Wahrscheinlichkeit × Auswirkung**

| RE-Wert | Priorität   | Farbe  |
|---------|-------------|--------|
| 1–4     | Niedrig     | Grün   |
| 5–9     | Mittel      | Gelb   |
| 10–14   | Hoch        | Orange |
| 15–25   | Kritisch    | Rot    |

---

## 3. Risk Management Table

### 3.1 Technische Risiken

---

#### R-T01: Performance-Engpässe auf Raspberry Pi

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-T01 |
| **Kategorie** | Technisch |
| **Beschreibung** | Der Raspberry Pi (ARM, 4 GB RAM, kein GPU) könnte für die gleichzeitige Ausführung von MediaPipe (Gestenerkennung), Vosk ASR, Aubio (Audioanalyse) und FastAPI zu leistungsschwach sein, was zu Latenzen oder Systeminstabilität führt. |
| **Wahrscheinlichkeit** | 4 (Hoch) |
| **Auswirkung** | 4 (Hoch) |
| **RE** | 16 (Kritisch) |
| **Mitigation** | Leichtgewichtige Modelle verwenden (Vosk Small Model, MediaPipe CPU-only); Hardware-Services in separate Threads auslagern (nicht im FastAPI-Event-Loop); AsyncIO für nicht-blockierende I/O; Lazy Loading im Frontend; einzelne Services gezielt aktivierbar/deaktivierbar. |
| **Monitoring** | Regelmäßige Messung von CPU/RAM-Auslastung während Integration; `/api/v1/system/health` Endpoint; Latenz-Tests für Geste → UI-Event. |
| **Management** | Deaktivierung rechenintensiver Services (MusicalAudio, Gesture) bei zu hoher Last; Reduktion der Kamera-Auflösung; separate Hardware für kritische Services (z. B. nur Voice auf Pi, Gesture auf PC). |
| **Status** | Teilweise eingetreten; durch Thread-Isolierung und leichtgewichtige Modelle beherrscht. |

---

#### R-T02: Instabilität der Vosk ASR-Erkennung

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-T02 |
| **Kategorie** | Technisch |
| **Beschreibung** | Die offline Spracherkennung (Vosk) könnte bei Hintergrundgeräuschen, unbekannten Akzenten oder fehlendem Sprachmodell schlecht performen oder abstürzen. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | Confidence-Schwellwert konfigurierbar (VOICE_MIN_CONFIDENCE, Standard 0.55); Cooldown-Mechanismus gegen Falscherkennung; Zahlwort-Normalisierung für robuste Befehlserkennung; Vosk-Modell-Download via Setup-Script (`download_voice_model.sh`); optionaler Import (System startet auch ohne Vosk-Modell). |
| **Monitoring** | Logging aller erkannten Texte und Intents; Überwachung des Erkennungs-Confidence im RealtimeHub. |
| **Management** | Erhöhung des Confidence-Schwellwerts; Umschaltung auf alternatives Sprachmodell; Deaktivierung des Voice-Services bei dauerhafter Fehlfunktion. |
| **Status** | Beherrschbar durch konfigurierbare Parameter. |

---

#### R-T03: Gestenerkennung unzuverlässig bei variierenden Bedingungen

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-T03 |
| **Kategorie** | Technisch |
| **Beschreibung** | MediaPipe-Gestenerkennung könnte bei unterschiedlichem Licht, verschiedenen Handgrößen oder Hintergrundstörungen unzuverlässig sein, was zu Falsch-Erkennungen oder fehlender Erkennung führt. |
| **Wahrscheinlichkeit** | 4 (Hoch) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 12 (Hoch) |
| **Mitigation** | Kalibrierungssystem implementiert (CalibrationService, `/api/v1/calibration`); 15+ konfigurierbare Schwellwerte; Smoothing-Filter (Alpha 0.6); Cooldown-Mechanismus; Gesture Context HUD zeigt aktuelle Erkennungsqualität; Offline-Testdaten für Benchmark-Tests. |
| **Monitoring** | Logging erkannter Gesten und Confidence-Werte; `test_gesture_benchmark.py` in CI; GestureCursor für visuelle Verifikation. |
| **Management** | Kalibrierung für spezifische Umgebung durchführen; Schwellwerte anpassen; Fallback auf andere Eingabemethoden (Sprache, Audio). |
| **Status** | Durch Kalibrierungssystem und konfigurierbare Parameter gut beherrschbar. |

---

#### R-T04: WebSocket-Verbindungsabbrüche

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-T04 |
| **Kategorie** | Technisch |
| **Beschreibung** | Die WebSocket-Verbindung zwischen Frontend und Backend (RealtimeHub) könnte unerwartet unterbrochen werden, was zu fehlenden Echtzeit-Updates führt. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | RealtimeHub-Implementierung mit Verbindungsmanagement; Frontend-Service (`realtime.ts`) mit Reconnect-Logik; REST-API als Fallback für Daten-Updates (Widgets pollen alternativ). |
| **Monitoring** | Logging von Connect/Disconnect-Events im RealtimeHub; `/api/v1/system/health`. |
| **Management** | Automatischer Reconnect im Frontend; manuelle Neuladen-Option; REST-Polling als Fallback. |
| **Status** | Durch Reconnect-Logik im Frontend beherrschbar. |

---

#### R-T05: Spotify OAuth-Token-Expiry und Auth-Flow-Probleme

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-T05 |
| **Kategorie** | Technisch |
| **Beschreibung** | Spotify Access-Tokens laufen nach einer Stunde ab. Refresh-Token können ungültig werden. Der OAuth-Flow erfordert Browser-Interaktion, die im Kiosk-Modus problematisch ist. |
| **Wahrscheinlichkeit** | 4 (Hoch) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 12 (Hoch) |
| **Mitigation** | Automatischer Token-Refresh implementiert (SpotifyService: `_ensure_token()`); Token-Persistenz im SpotifyRepository; automatische Öffnung des Auth-Flows im Browser; Graceful Degradation bei ungültigem Token (Widget zeigt Fehler statt zu crashen). |
| **Monitoring** | Logging von Token-Refresh-Events; HTTP-Status-Codes aus Spotify API überwachen. |
| **Management** | Manuelle Neu-Authentifizierung über `/api/v1/spotify/auth`; SpotifyWidget zeigt Auth-Button bei fehlendem Token. |
| **Status** | Durch automatischen Refresh beherrscht; manuelle Re-Auth im Extremfall nötig. |

---

#### R-T06: Fehlender Vosk-Sprachmodell-Download

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-T06 |
| **Kategorie** | Technisch |
| **Beschreibung** | Das Vosk ASR-Sprachmodell (~50 MB bis 1 GB) muss separat heruntergeladen werden. Fehlt es, startet der VoiceService nicht. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 2 (Gering) |
| **RE** | 6 (Mittel) |
| **Mitigation** | Setup-Script `Backend/scripts/download_voice_model.sh` bereitgestellt; VoiceService importiert Vosk optional (try/except); Backend startet auch ohne Vosk-Modell. |
| **Monitoring** | VoiceService-Startlog prüfen; Status via `/api/v1/voice/status`. |
| **Management** | Script ausführen und Modell herunterladen; Dokumentation in README. |
| **Status** | Gut dokumentiert und beherrschbar. |

---

### 3.2 Externe Abhängigkeiten / API-Risiken

---

#### R-A01: Ausfall oder Rate-Limiting externer APIs

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-A01 |
| **Kategorie** | Externe Abhängigkeit |
| **Beschreibung** | Externe APIs (OpenMeteo, GNews, Twelve Data, Spotify, Nina/BBK) können ausfallen, Rate-Limits überschreiten oder API-Änderungen einführen, die die Widget-Funktionalität beeinträchtigen. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | Circuit Breaker für Wetter-API; TTL-basiertes Caching (10–30 min) für alle APIs; HTTP-Level-Cache (requests-cache); graceful Degradation: Widgets zeigen gecachte Daten statt zu crashen; WeatherRepositoryError → HTTP 502 (saubere Fehlerbehandlung). |
| **Monitoring** | `/api/v1/system/health` mit External-API-Health-Check (`test_external_api_health.py`); Logging von HTTP-Fehlerresponses. |
| **Management** | Wechsel zu alternativer API bei dauerhaftem Ausfall; Erhöhung der Cache-TTL; Widget deaktivieren bis API wieder verfügbar. |
| **Status** | Durch Caching und Circuit Breaker gut beherrschbar. |

---

#### R-A02: Änderungen an API-Interfaces (Breaking Changes)

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-A02 |
| **Kategorie** | Externe Abhängigkeit |
| **Beschreibung** | Externe API-Anbieter können ihre Schnittstellen ändern (neue Felder, geänderte Feldnamen, neue Authentifizierungsanforderungen), was zu unerwarteten Fehlern führt. |
| **Wahrscheinlichkeit** | 2 (Gering) |
| **Auswirkung** | 4 (Hoch) |
| **RE** | 8 (Mittel) |
| **Mitigation** | Repository Pattern kapselt API-spezifischen Code; Pydantic-Schemas validieren API-Antworten frühzeitig; Dependabot für Abhängigkeits-Updates. |
| **Monitoring** | CI-Tests mit API-Health-Checks; Monitoring der Repository-Response-Parsing-Fehler. |
| **Management** | Repository-Klasse entsprechend dem neuen API-Interface anpassen; Pydantic-Schema aktualisieren. |
| **Status** | Kein Auftreten während Projektlaufzeit. |

---

#### R-A03: Spotify API-Zugang und Scope-Beschränkungen

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-A03 |
| **Kategorie** | Externe Abhängigkeit |
| **Beschreibung** | Spotify Web API erfordert OAuth 2.0 und App-Registrierung im Spotify Developer Dashboard. Fehlende Credentials oder falsche Scopes verhindern Widget-Funktionalität. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | OAuth 2.0 Authorization Code Flow implementiert; benötigte Scopes dokumentiert (`user-read-currently-playing`, `user-read-playback-state`); Konfiguration via `.env` (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET); Widget zeigt Auth-Button wenn nicht authentifiziert. |
| **Monitoring** | HTTP-Status-Codes von Spotify API überwachen; Token-Refresh-Fehler loggen. |
| **Management** | Spotify-App im Developer Dashboard konfigurieren; Client-ID/Secret in `.env` eintragen; manueller Auth-Flow via `/api/v1/spotify/auth`. |
| **Status** | Implementiert und beherrschbar. |

---

#### R-A04: Google Calendar API-Integration nicht abgeschlossen

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-A04 |
| **Kategorie** | Externe Abhängigkeit / Projektrisiko |
| **Beschreibung** | Die Google Kalender-Integration war geplant, konnte jedoch im Projektzeitraum nicht vollständig implementiert werden. Der Endpunkt gibt einen Platzhalter zurück. |
| **Wahrscheinlichkeit** | 5 (Sehr hoch – bereits eingetreten) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 15 (Kritisch – bereits realisiert) |
| **Mitigation** | Google OAuth und API-Client-Bibliotheken (`google-auth`, `google-api-python-client`) bereits als Dependencies vorhanden; Endpunkt-Stub vorhanden für zukünftige Implementierung. |
| **Monitoring** | Endpunkt-Response überwachen (`GET /api/v1/calendar/`). |
| **Management** | Als bekannte Einschränkung dokumentiert (SRS v2.0, Abschnitt 3.1.2); Implementierung für zukünftige Iteration vorgesehen. |
| **Status** | Eingetreten. Als Stub/Platzhalter abgeschlossen. In SRS als nicht-implementierte Anforderung dokumentiert. |

---

### 3.3 Hardware-Risiken

---

#### R-H01: GPIO-Inkompatibilität / LED-Steuerung funktioniert nicht

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-H01 |
| **Kategorie** | Hardware |
| **Beschreibung** | GPIO-Steuerung für RGB-LEDs funktioniert nur auf Raspberry Pi. In Entwicklungsumgebungen ohne GPIO schlägt die Initialisierung fehl. gpiozero könnte mit neuen Raspberry Pi OS-Versionen inkompatibel sein. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 2 (Gering) |
| **RE** | 6 (Mittel) |
| **Mitigation** | **Adapter-Pattern** implementiert: `GpiozeroLEDAdapter` (echter GPIO) und `MockLEDAdapter` (kein GPIO); automatische Auswahl zur Laufzeit (`is_available()`); LEDService startet auch ohne GPIO (graceful degradation); optional Import von gpiozero. |
| **Monitoring** | LEDService-Startlog prüfen; `/api/v1/led/status` Endpoint; LED-Tests in pytest. |
| **Management** | Mock-Adapter nutzen in Entwicklung; auf Raspberry Pi echten Adapter verwenden; GPIO-Pins konfigurierbar in `.env`. |
| **Status** | Durch Adapter-Pattern vollständig beherrschbar. |

---

#### R-H02: USB-Kamera nicht verfügbar oder inkompatibel

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-H02 |
| **Kategorie** | Hardware |
| **Beschreibung** | Die USB-Kamera für Gestenerkennung könnte nicht erkannt werden, inkompatibel mit OpenCV/MediaPipe sein oder bei schlechten Lichtverhältnissen schlechte Bildqualität liefern. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | GestureService verwendet Standard-OpenCV-Kamera-API (universell für USB-Kameras); CameraWidget zeigt Kamerastatus; Gesture-Service deaktivierbar wenn keine Kamera verfügbar; Kalibrierungssystem für verschiedene Kameras. |
| **Monitoring** | Kamera-Stream-Status in GestureService-Logs; CameraWidget zeigt Verbindungsstatus. |
| **Management** | Alternative USB-Kamera verwenden; Gestensteuerung deaktivieren und alternative Eingabe (Sprache, Audio) nutzen. |
| **Status** | Beherrschbar. CameraWidget mit Statusanzeige implementiert. |

---

#### R-H03: Mikrofon-Qualität und Umgebungslärm

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-H03 |
| **Kategorie** | Hardware |
| **Beschreibung** | Schlechte Mikrofon-Qualität oder hoher Umgebungslärm beeinträchtigen sowohl die Vosk ASR-Erkennung als auch die Aubio-Audiobefehlserkennung. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | Mikrofonauswahl im Frontend (MicrophoneSelector – Auswahl des besten Eingangsgeräts); konfigurierbare Confidence-Schwellwerte; scipy-Resampling für unterschiedliche Abtastraten; sounddevice für Hardware-unabhängigen Audio-Zugriff. |
| **Monitoring** | Erkennungs-Confidence-Logs; MicrophoneSelector im Frontend zur Laufzeit. |
| **Management** | Besseres USB-Mikrofon verwenden; Confidence-Schwellwert erhöhen; alternative Mikrofon-Position; Eingabemethode wechseln. |
| **Status** | Durch Mikrofonauswahl und konfigurierbare Schwellwerte beherrschbar. |

---

#### R-H04: Raspberry Pi Beschaffung / Lieferverzögerungen

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-H04 |
| **Kategorie** | Hardware / Projekt |
| **Beschreibung** | Raspberry Pi Hardware könnte nicht rechtzeitig für Hardware-Tests beschafft werden (Lieferkettenproblem). |
| **Wahrscheinlichkeit** | 2 (Gering) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 6 (Mittel) |
| **Mitigation** | Entwicklung primär auf Standard-PC/Laptop; Mock-Adapter für LED; CI/CD-Tests ohne Raspberry Pi ausführbar; separater CI-Requirements-File ohne Hardware-Bibliotheken. |
| **Monitoring** | Frühzeitige Hardware-Beschaffung planen. |
| **Management** | Entwicklung auf PC fortsetzen; Hardware-Tests als letzte Phase einplanen. |
| **Status** | Beherrschbar durch Software-First-Entwicklungsansatz. |

---

### 3.4 Projektmanagement-Risiken

---

#### R-P01: Scope-Creep – Zu viele Features im begrenzten Zeitrahmen

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-P01 |
| **Kategorie** | Projektmanagement |
| **Beschreibung** | Das Projekt könnte durch zu viele geplante Features (Kalender, Smart Home, Mobile App, Notizen, etc.) in Verzug geraten und den Abgabetermin gefährden. |
| **Wahrscheinlichkeit** | 4 (Hoch) |
| **Auswirkung** | 4 (Hoch) |
| **RE** | 16 (Kritisch) |
| **Mitigation** | Klare Priorisierung: MVP-Features zuerst (Uhr, Wetter, Geste, Sprache); erweiterte Features als optional markiert; Pull-Request-basierte Entwicklung mit Feature-Branches; regelmäßige Team-Abstimmung. |
| **Monitoring** | GitHub Issues und Pull Requests tracken; wöchentliche Sprint-Reviews. |
| **Management** | Features deprioritisieren oder als Stub markieren (Kalender, Smart Home als "coming soon"); Fokus auf funktionierende Kernfunktionalität. |
| **Status** | Eingetreten (Kalender, Smart Home nicht vollständig). Durch bewusste Priorisierung beherrschbar. Abgabe rechtzeitig. |

---

#### R-P02: Wissensverteilung und Abhängigkeit von Einzelpersonen

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-P02 |
| **Kategorie** | Projektmanagement |
| **Beschreibung** | Bei einem 4-Personen-Team könnte der Ausfall oder die Überlastung einzelner Mitglieder (insbesondere bei spezialisierten Bereichen wie Gestenerkennung oder Backend) zu Verzögerungen führen. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | Klare Aufgabenteilung mit Pull Requests; Code-Reviews in PRs fördern Wissensaustausch; Dokumentation in README und docs/; CI/CD macht Tests für alle transparent. |
| **Monitoring** | PR-Aktivität auf GitHub beobachten; regelmäßige Team-Meetings. |
| **Management** | Paarweise Arbeit an kritischen Features; Dokumentation kritischer Implementierungen. |
| **Status** | Beherrschbar durch PR-basierte Entwicklung. |

---

#### R-P03: Integrationsprobleme zwischen Frontend und Backend

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-P03 |
| **Kategorie** | Projektmanagement / Technisch |
| **Beschreibung** | Inkompatible API-Interfaces zwischen Frontend-Service-Dateien und Backend-Endpunkten, unterschiedliche Entwicklungsstände, CORS-Probleme. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 9 (Mittel) |
| **Mitigation** | Pydantic-Schemas definieren klare Datenverträge; FastAPI generiert OpenAPI-Dokumentation (Swagger UI unter `/docs`); TypeScript im Frontend erzwingt Typ-Konformität; CORS-Konfiguration in FastAPI (`CORS_ORIGINS`). |
| **Monitoring** | CI/CD führt API-Tests aus; Frontend-Tests mocken Backend-Responses. |
| **Management** | Swagger-Dokumentation als Referenz; Anpassung der TypeScript-Typen an Pydantic-Schemas. |
| **Status** | Durch OpenAPI/Swagger und TypeScript gut beherrschbar. |

---

#### R-P04: Smart-Home MQTT-Integration nicht abgeschlossen

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-P04 |
| **Kategorie** | Projektmanagement |
| **Beschreibung** | Die Smart-Home MQTT-Integration (Gerätesteuerung, Energiemonitoring) war geplant, konnte aber im Projektzeitraum nicht vollständig implementiert werden. |
| **Wahrscheinlichkeit** | 5 (Sehr hoch – bereits eingetreten) |
| **Auswirkung** | 3 (Mittel) |
| **RE** | 15 (Kritisch – bereits realisiert) |
| **Mitigation** | paho-mqtt als Dependency vorhanden; MQTT-Service-Datei (`services/mqtt.py`) vorhanden; Stub-Endpunkt für zukünftige Implementierung. |
| **Monitoring** | Endpunkt-Response überwachen (`GET /api/v1/smart-home/devices`). |
| **Management** | Als bekannte Einschränkung dokumentiert; MQTT-Integration für zukünftige Iteration geplant. |
| **Status** | Eingetreten. Als Stub abgeschlossen und in SRS dokumentiert. |

---

### 3.5 Sicherheits- und Datenschutzrisiken

---

#### R-S01: API-Keys in Versionskontrolle eingecheckt

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-S01 |
| **Kategorie** | Sicherheit |
| **Beschreibung** | Versehentliches Einchecken von API-Keys (Twelve Data, Spotify Client Secret, Google Credentials) in das Git-Repository führt zu Credential-Leaks. |
| **Wahrscheinlichkeit** | 3 (Mittel) |
| **Auswirkung** | 4 (Hoch) |
| **RE** | 12 (Hoch) |
| **Mitigation** | `.env`-Datei in `.gitignore` aufgenommen; `.env.example` mit Platzhaltern im Repository; pydantic-settings lädt Konfiguration aus `.env` (nicht aus Code); keine Hardcoded Credentials im Quellcode. |
| **Monitoring** | GitHub Secret-Scanning; regelmäßige Überprüfung der `.gitignore`-Datei; Dependabot-Sicherheits-Updates. |
| **Management** | Sofortiges Revoken und Regenerieren der betroffenen API-Keys; `.env` aus Git-History entfernen. |
| **Status** | Durch `.gitignore` und `.env.example` präventiv beherrschbar. |

---

#### R-S02: Fehlende JWT-Authentifizierung an API-Endpunkten

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-S02 |
| **Kategorie** | Sicherheit |
| **Beschreibung** | JWT-Authentifizierung ist konfiguriert (python-jose, passlib), aber nicht an den API-Endpunkten erzwungen. Im LAN-Betrieb sind alle Endpunkte ohne Authentifizierung erreichbar. |
| **Wahrscheinlichkeit** | 4 (Hoch) |
| **Auswirkung** | 2 (Gering) |
| **RE** | 8 (Mittel) |
| **Mitigation** | System ist für lokalen LAN-Betrieb (Heimnetz) konzipiert, nicht für Internet-Exposition; CORS-Konfiguration beschränkt Browser-Zugriff; kein Öffnen von Ports ins Internet erforderlich. |
| **Monitoring** | Zugriffsprotokollierung via Uvicorn-Logs; keine externen Exposures. |
| **Management** | Für produktiven Einsatz im Internet: JWT-Middleware in FastAPI aktivieren; API hinter Reverse-Proxy (nginx) mit TLS betreiben. |
| **Status** | Akzeptiertes Risiko für lokalen LAN-Betrieb (Heimnetz-Kontext). In SRS als bekannte Einschränkung dokumentiert. |

---

#### R-S03: Datenschutz bei Kamera- und Mikrofon-Daten

| Attribut | Inhalt |
|----------|--------|
| **Risiko-ID** | R-S03 |
| **Kategorie** | Datenschutz |
| **Beschreibung** | Kamera- und Mikrofon-Daten (Bild, Audio) könnten versehentlich gespeichert oder an externe Dienste übertragen werden, was DSGVO-Anforderungen verletzt. |
| **Wahrscheinlichkeit** | 1 (Sehr gering) |
| **Auswirkung** | 4 (Hoch) |
| **RE** | 4 (Niedrig) |
| **Mitigation** | Vosk ASR: vollständig offline, keine Cloud-Übertragung; MediaPipe: lokale Verarbeitung, keine Daten verlassen das Gerät; Aubio: lokale Audio-Analyse; keine Persistenz von Audio-/Video-Daten; Kamera-Stream nur im LAN sichtbar. |
| **Monitoring** | Code-Review aller Service-Dateien auf externe Verbindungen; keine Kamera/Audio-Daten in Repositories. |
| **Management** | Offline-Verarbeitung beibehalten; klar in Dokumentation kommunizieren. |
| **Status** | Kein Risiko durch vollständig lokale Verarbeitung aller sensiblen Daten. |

---

## 4. Risiko-Übersichtsmatrix

| ID | Titel | W | A | RE | Priorität | Status |
|----|-------|---|---|----|-----------|--------|
| R-T01 | Performance auf Raspberry Pi | 4 | 4 | **16** | Kritisch | Beherrschbar |
| R-T02 | Vosk ASR Instabilität | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-T03 | Gestenerkennung unzuverlässig | 4 | 3 | **12** | Hoch | Beherrschbar |
| R-T04 | WebSocket-Verbindungsabbrüche | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-T05 | Spotify OAuth Token-Probleme | 4 | 3 | **12** | Hoch | Beherrschbar |
| R-T06 | Fehlender Vosk-Modell-Download | 3 | 2 | 6 | Mittel | Beherrschbar |
| R-A01 | Ausfall externer APIs | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-A02 | Breaking Changes in APIs | 2 | 4 | 8 | Mittel | Nicht eingetreten |
| R-A03 | Spotify API Scope-Probleme | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-A04 | Google Calendar nicht implementiert | 5 | 3 | **15** | Kritisch | **Eingetreten (Stub)** |
| R-H01 | GPIO inkompatibel / LED-Probleme | 3 | 2 | 6 | Mittel | Beherrschbar |
| R-H02 | USB-Kamera inkompatibel | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-H03 | Schlechte Mikrofon-Qualität | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-H04 | Raspberry Pi Lieferverzögerung | 2 | 3 | 6 | Mittel | Nicht eingetreten |
| R-P01 | Scope-Creep | 4 | 4 | **16** | Kritisch | **Teilweise eingetreten** |
| R-P02 | Wissensverteilung / Team-Ausfall | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-P03 | Frontend/Backend Integrationsprobleme | 3 | 3 | 9 | Mittel | Beherrschbar |
| R-P04 | Smart-Home MQTT nicht implementiert | 5 | 3 | **15** | Kritisch | **Eingetreten (Stub)** |
| R-S01 | API-Keys in Git eingecheckt | 3 | 4 | **12** | Hoch | Beherrschbar |
| R-S02 | Fehlende JWT-Authentifizierung | 4 | 2 | 8 | Mittel | Akzeptiert (LAN) |
| R-S03 | Datenschutz Kamera/Mikrofon | 1 | 4 | 4 | Niedrig | Kein Risiko |

**Legende:** W = Wahrscheinlichkeit (1–5), A = Auswirkung (1–5), RE = Risiko-Exposure (W × A)

---

## 5. Realisierte Risiken und Projekterfahrungen

### Eingetretene Risiken

**R-P01 (Scope-Creep)** und **R-A04 / R-P04 (Kalender / Smart Home nicht fertig)** sind die signifikantesten eingetretenen Risiken des Projekts. Durch bewusste Scope-Entscheidungen wurden diese Features als Stubs implementiert und als bekannte Einschränkungen dokumentiert. Das Kernprojekt (Geste, Sprache, Audio, LED, Widget-Ökosystem) wurde erfolgreich abgeschlossen.

### Nicht eingetretene kritische Risiken

**R-T01 (Performance auf Pi)**: Durch frühzeitige Optimierungsentscheidungen (Thread-Isolierung, leichtgewichtige Modelle, Mock-Adapter) konnte dieses Risiko beherrscht werden, ohne dass es zu kritischen Systemausfällen kam.

**R-S01 (API-Keys in Git)**: Durch `.gitignore` und `.env.example` von Beginn an verhindert.

### Gelernte Erkenntnisse (Lessons Learned)

1. **Hardware-Abstraktion früh einplanen**: Der LED-Adapter-Pattern ermöglichte problemlose Entwicklung ohne Raspberry Pi – sollte für alle Hardware-Services von Anfang an so umgesetzt werden.

2. **Scope-Risiken unterschätzt**: Kalender und Smart Home erforderten mehr Integrationsaufwand als erwartet. Frühzeitigere Priorisierung hätte geholfen.

3. **Circuit Breaker und Caching zahlen sich aus**: Mehrfache API-Ausfälle während der Entwicklung wurden transparent abgefangen – das System lief stabil weiter.

4. **Kalibrierungssystem war richtige Entscheidung**: Gestenerkennung ohne Kalibrierung wäre für unterschiedliche Nutzer und Umgebungen unbrauchbar gewesen.

5. **Repository Pattern macht Tests einfach**: Alle Services mit Repository-Pattern konnten zuverlässig mit Mock-Repositories getestet werden.

---

**Ende des Dokuments**  
*RMMM für das Nimrag Smart Mirror Projekt, Version 1.0 (Projektabschluss 30.06.2026)*
