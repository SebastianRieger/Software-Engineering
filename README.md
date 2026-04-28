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

### Frontend

```bash
cd Frontend/nimrag-frontend
npm install
npm run dev
```

### Backend

```bash
cd Backend
pip install -r requirements.txt
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Aktive Dokumentation

- [Dokumentationsuebersicht](docs/README.md)
- [Produktumfang](docs/PRODUCT_SCOPE.md)
- [Ist-Zustand](docs/CURRENT_STATE.md)
- [Zielarchitektur](docs/TARGET_ARCHITECTURE.md)
- [Umsetzungsplan](docs/IMPLEMENTATION_PLAN.md)

## Historische Dokumente

Fruehere SRS-, SAD-, Diagramm- und Experiment-Dokumente liegen unter [docs/archive](docs/archive/README.md).
Sie bleiben als Verlauf erhalten, sind aber nicht mehr die aktive Quelle der Wahrheit.
