# Test Report – Nimrag Smart Mirror

**Datum:** Juni 2026  
**Test-Framework Backend:** pytest + pytest-cov  
**Test-Framework Frontend:** Vitest  
**CI-Integration:** GitHub Actions (`ci-cd.yml`)

---

## Übersicht

| Bereich | Testdateien | Abdeckung |
|---|---|---|
| Backend (Python / FastAPI) | 16 | via `coverage.xml` in CI |
| Frontend (Vue 3 / TypeScript) | 37 | via Vitest Coverage in CI |

---

## Backend-Tests

### Testdateien

| Datei | Abgedeckte Komponente |
|---|---|
| `test_weather.py` | Wetter-Endpunkte, Geocoding, Cache-Verhalten |
| `test_news.py` | Tagesschau-Proxy, Ressort- und Regionsfilter |
| `test_configuration.py` | Layout- und System-Konfigurationsendpunkte |
| `test_external_api_health.py` | Non-blocking Healthcheck externer APIs |
| `test_gestures.py` | Gesten-Session (Start, Stop, Status) |
| `test_gesture_contracts.py` | Typsicherheit der Gesten-Datenstrukturen |
| `test_gesture_benchmark.py` | Performance-Baseline für Gesten-Klassifikation |
| `test_gesture_sequence.py` | Sequenz-Matcher und Kandidaten-Logik |
| `test_push_cycle_analysis.py` | Push-Gesten-Zyklusanalyse (Offline) |
| `test_swipe_cycle_analysis.py` | Swipe-Gesten-Zyklusanalyse (Offline) |
| `test_interactions.py` | Action-Dispatcher und Interaktionsauflösung |
| `test_led.py` | LED-Service-Logik |
| `test_calibration.py` | Kalibrierungsendpunkte und -schemas |
| `test_voice.py` | Voice-Service-Konfiguration und -Pfade |
| `test_musical_audio.py` | Musical-Audio-Service-Grundfunktionen |
| `conftest.py` | Shared Fixtures (HTTP-Client, Dependency Overrides) |

### Ausführung (lokal)

```bash
# Windows
Backend\.venv\Scripts\python.exe -m pytest -v tests

# Linux / macOS
Backend/.venv/bin/python -m pytest -v tests

# Mit Coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Testdesign-Hinweise

- Wetter-, News- und Konfigurationstests verwenden **Dependency Injection Overrides** via FastAPI, sodass keine echten API-Keys für CI benötigt werden.
- Gesten-Tests laufen ohne Hardware (MediaPipe wird gemockt).
- Die SQLite-Testdatenbank (`ci_test.db`) wird pro CI-Run frisch angelegt.

---

## Frontend-Tests

### Testdateien – Composables

| Datei | Composable |
|---|---|
| `useWidgetManager.test.ts` | Widget-Lifecycle, Grid-Persistenz, localStorage |
| `useEditMode.test.ts` | Edit-Modus, Keyboard-Events |
| `useModuleShop.test.ts` | Shop-Verwaltung, Widget-Auswahl |
| `useWidgetResize.test.ts` | Widget-Größenänderung |
| `useActionDispatcher.test.ts` | Action-Dispatching via WebSocket |
| `useAppConfig.test.ts` | App-Konfiguration vom Backend |
| `useBullshitDerStunde.test.ts` | Corporate-Bullshit-Composable |
| `useFaktDesTages.test.ts` | Nutzloser-Fakt-Composable |
| `useFrageDesTages.test.ts` | Trivia-Frage-Composable |
| `useHandTracking.test.ts` | Hand-Tracking-Initialisierung |
| `useHoverTrigger.test.ts` | Hover-basierte Trigger-Logik |
| `useNinaWarnings.test.ts` | NINA-Warnungen-Composable |
| `useRandomMeme.test.ts` | Meme-Abruf-Composable |
| `useClockWidgetMode.test.ts` | Analog/Digital-Modus-Umschaltung |

### Testdateien – Komponenten

| Datei | Komponente |
|---|---|
| `App.test.ts` | Root-App-Komponente |
| `ClockWidget.test.ts` | Uhr-Widget (analog + digital) |
| `TemplateWidget.test.ts` | Hardware-Status-Widget |
| `CameraWidget.test.ts` | Kamera-Widget, Permission-States |
| `GridBoard.test.ts` | Grid-Rendering, Cell-Slots |
| `Market.test.ts` | Markt-Widget, Kurs-Darstellung |
| `ModuleShop.test.ts` | Widget-Shop, Auswahl-UI |
| `News.test.ts` | News-Widget, Feed-Darstellung |
| `NinaWarningsWidget.test.ts` | NINA-Warnungen-Darstellung |
| `WeatherWidget.test.ts` | Wetter-Widget, Daten-Binding |

### Testdateien – Services

| Datei | Service |
|---|---|
| `api.service.test.ts` | HTTP-Basis-Client |
| `apiConfig.service.test.ts` | API-Konfigurationsabruf |
| `appConfig.service.test.ts` | App-Config-Service |
| `realtime.service.test.ts` | WebSocket-Verbindung |
| `bullshit.service.test.ts` | Bullshit-API-Service |
| `fact.service.test.ts` | Fakten-API-Service |
| `gestureFrameStream.service.test.ts` | Gesten-Frame-Stream |
| `market.service.test.ts` | Marktdaten-Service |
| `meme.service.test.ts` | Meme-API-Service |
| `news.service.test.ts` | News-Service |
| `systemHealth.service.test.ts` | System-Health-Check |
| `trivia.service.test.ts` | Trivia-Service |
| `weather.service.test.ts` | Wetter-Service |

### Ausführung (lokal)

```bash
cd Frontend/nimrag-frontend
npm run test            # einmaliger Lauf
npm run test:coverage   # mit Coverage-Report
```

---

## Testergebnisse in CI

In GitHub Actions (Job `test-backend` und `test-frontend`) werden alle Tests automatisch bei jedem Push auf `main` und `dev` ausgeführt. Coverage-Artefakte (`backend-coverage`, `frontend-coverage`) werden 14 Tage aufbewahrt.

Der `quality-gates`-Job läuft erst nach erfolgreichem Abschluss beider Test-Jobs.

---

## Bekannte Einschränkungen

| Einschränkung | Beschreibung |
|---|---|
| Kamera-Tests | `getUserMedia` kann in JSDOM-Umgebung nicht simuliert werden; Widget testet nur den Permission-Denied-Pfad |
| GPIO / LED | Hardware-Tests laufen nur auf dem Raspberry Pi; in CI wird der Service gemockt |
| Spotify OAuth | OAuth-Flow ist nicht automatisiert testbar; nur Unit-Tests für Token-Handling vorhanden |
| MediaPipe | Gesten-Erkennung im Frontend wird nur bis zur Initialisierung getestet; echte Kameradaten erfordern E2E-Tests |
