# Teststrategie fuer den Smart-Spiegel (Nimrag)

Dokumentation und Grundlage fuer einen Blogeintrag.

## 1. Ueberblick

Um die Qualitaet unseres Smart-Spiegel-Projekts Nimrag sicherzustellen, setzen wir auf eine klar definierte Teststrategie. Diese umfasst verschiedene Testarten, moderne Testwerkzeuge und eine strikte Integration in unsere CI/CD-Pipeline. Ziel ist es, Stabilitaet, Wartbarkeit und Zuverlaessigkeit des Systems langfristig zu gewaehrleisten.

## 2. Eingesetzte Testarten

### Unit Tests

- Testen einzelne Funktionen oder Module isoliert.
- Beispiele:
  - Vue-Komponentenlogik und Composables
  - Hilfsfunktionen im Frontend
  - API-Dienste (Weather, LED, MQTT)
  - Authentifizierungs- und GPIO-Funktionen

### Integrationstests

- Pruefen das Zusammenspiel mehrerer Module.
- Beispiele:
  - Frontend und FastAPI-Backend
  - LED-Steuerung und Hardware-Abstraktionen (gpiozero)
  - Weather-Service und externe APIs
  - MQTT-Kommunikation zwischen Komponenten

### End-to-End-Tests (E2E)

- Simulieren echte Nutzerinteraktionen auf dem Raspberry Pi.
- Beispiele:
  - Boot-Prozess des Smart-Spiegels
  - Laden der Widgets (Wetter, Musik, Konfiguration)
  - Gesten- und Voice-Control
  - Offline-Modus und Fallback-Mechanismen

### API-Tests

- Stellen sicher, dass FastAPI-Endpunkte korrekt funktionieren.
- Beispiele:
  - Response-Struktur der Weather- und Config-Endpunkte
  - LED-Steuerung ueber API
  - Authentifizierung und Autorisierung
  - Fehlercodes und Timeout-Handling

## 3. Zielwert fuer die Testabdeckung

Wir definieren einen Zielwert von 70 bis 80 Prozent Testabdeckung.

### Warum dieser Wert?

- Der Smart-Spiegel ist ein modernes IoT-Produkt, aber nicht sicherheitskritisch.
- 100 Prozent Coverage ist weder realistisch noch sinnvoll.
- 70 bis 80 Prozent bietet ein gutes Verhaeltnis aus Aufwand und Nutzen.

### Wichtiger als die Zahl: die richtigen Bereiche

Folgende Bereiche muessen besonders gut abgedeckt sein:

- Vue-Komponenten und UI-Logik im Frontend
- Netzwerk-Funktionen wie API-Kommunikation und MQTT
- Weather- und LED-Services als kritische Hardware-Integration
- Fehlerbehandlung:
  - Offline-Modus ohne Internet
  - API-Timeouts und Fallback-Mechanismen
  - Raspberry-Pi-Boot-Fehler
- Start- und Boot-Prozess des Raspberry Pi

## 4. Automatische Testwerkzeuge

### Frontend (Vue 3 plus TypeScript)

- Vitest
  - Schnelle Unit- und Integrationstests
  - Wird im Repo fuer Coverage-Reports und Testlaeufe genutzt; die erste Quality-Ausbaustufe sammelt die Werte report-only
- Vue Test Utils
  - Realistische Komponententests fuer Vue-3-Single-File-Components
- Testing Library (Vue)
  - Fokus auf echtes User-Verhalten statt Implementierungsdetails
- MSW (Mock Service Worker) geplant
  - API-Mocks ohne echten FastAPI-Server
  - Ideal fuer Offline- und Fehlerfall-Tests

### Backend (Python plus FastAPI)

- pytest
  - Stabil, schnell und flexibel
  - Ideal fuer API- und Logiktests
- pytest-asyncio
  - Support fuer async/await in Tests, wichtig fuer FastAPI
- pytest-cov
  - Erzeugt die Coverage-Berichte fuer den aktuellen Quality-Lauf
- TestClient (FastAPI)
  - Echte HTTP-aehnliche Tests ohne Server-Overhead
- Mock Services
  - Mocks fuer LED-Service, Weather-Service und MQTT, siehe `conftest.py`

### Repo-weites Quality-Reporting

- Root-Quality-Lauf ueber `npm run quality`
  - Fuehrt Backend-, Frontend- und Duplication-Messung plus Aggregation aus
- ESLint im Frontend
  - Liefert Lint- und einfache Complexity-Signale fuer `src/`
- Radon im Backend
  - Liefert Cyclomatic Complexity, Maintainability Index, Halstead und Raw Metrics fuer `Backend/src`
- jscpd repo-weit
  - Misst Duplication nur auf produktivem Code in Backend und Frontend

## 5. Verwaltung der Testfaelle

Die CI-Einbindung wird schrittweise ausgebaut. Der aktuelle Quality-Workflow erzeugt Berichte und Artefakte report-only, statt bereits harte Merge-Gates fuer alle Metriken zu erzwingen.

- Pull Requests koennen einen separaten Quality-Metrics-Workflow ausloesen.
- Coverage-, Lint-, Typecheck-, Complexity- und Duplication-Berichte werden als Artefakte erzeugt.
- Harter Gate-Betrieb fuer Schwellwerte ist erst fuer eine spaetere Ausbaustufe vorgesehen.

## 6. Fazit

Unsere Teststrategie stellt sicher, dass Nimrag zuverlaessig, wartbar und stabil bleibt. Durch die Kombination aus Unit-, Integrations-, API- und E2E-Tests, modernen Werkzeugen und einer strikten CI-Integration schaffen wir eine solide Grundlage fuer ein professionelles IoT-Produkt.