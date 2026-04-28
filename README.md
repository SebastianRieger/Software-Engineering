# Nimrag Smart Mirror

Nimrag ist ein Hochschulprojekt fuer einen modularen Smart Mirror auf Raspberry Pi Basis.
Die aktuelle Codebasis ist ein funktionaler Prototyp, nicht das Endsystem.

## Aktueller Stand

- Frontend: Vue 3 Prototype fuer Widget-Board, Widget-Shop und einfache Widgets
- Backend: FastAPI Prototype mit Wetter-Service, Platzhalter-Endpunkten und WebSocket-Echo
- Dokumentation: auf eine kleine aktive Kernmenge reduziert, alte Artefakte liegen im Archiv

## Zielbild

Ein stabiler Smart Mirror mit:

- modularen Widgets
- konfigurierbarem Layout
- Wetter, Kalender und Uhr als Kernfunktionen
- lokalem Cache und sinnvoller Degradation
- spaeterer Hardware- und Smart-Home-Integration

## Tech Stack

- Frontend: Vue 3, TypeScript, Vite
- Backend: FastAPI, Python
- Persistenz: SQLite
- Realtime: WebSocket
- Hardware/IoT spaeter: GPIO, MQTT

## Entwicklung starten

### Empfohlener Full-Stack-Start

```bash
npm run dev
```

Der Root-Start erledigt jetzt den kompletten Entwicklungsstart in einer festen Reihenfolge:

- Frontend-Abhaengigkeiten werden installiert.
- Das Backend-Venv unter `Backend/venv_py312` wird bei Bedarf erstellt.
- Backend-Abhaengigkeiten aus `Backend/requirements.txt` werden installiert.
- Die festen Dev-Ports `8000` und `5173` werden vor dem Start bereinigt.
- Das Backend startet auf `http://localhost:8000`.
- Das Frontend startet auf `http://localhost:5173/`.

Damit bleibt die API-Basis fuer das Frontend stabil auf `http://localhost:8000/api/v1` und die UI laeuft nicht mehr versehentlich gegen einen anderen Port oder einen fremden Prozess.

### Einzelstarts

```bash
npm run dev:backend
npm run dev:frontend
```

### Backend

```bash
npm run setup
```

## Aktive Dokumentation

- [Dokumentationsuebersicht](docs/README.md)
- [Produktumfang](docs/PRODUCT_SCOPE.md)
- [Ist-Zustand](docs/CURRENT_STATE.md)
- [Zielarchitektur](docs/TARGET_ARCHITECTURE.md)

## Historische Dokumente

Fruehere SRS-, SAD-, Diagramm- und Experiment-Dokumente liegen unter [docs/archive](docs/archive/README.md).
Sie bleiben als Verlauf erhalten, sind aber nicht mehr die aktive Quelle der Wahrheit.
