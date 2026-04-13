# Nimrag Backend

FastAPI-Backend fuer den Nimrag Smart Mirror.

## Status

Das Backend ist jetzt eine kleine, konsistente Basis statt nur eines reinen Prototyps.
Die Kernpfade fuer Wetter, Konfiguration, Systemstatus und einen optionalen Gesten-Backend-Kern sind umgesetzt, weitere Bereiche sind noch bewusst reduziert oder Platzhalter.

## Derzeit vorhanden

- API-Router unter `src/api/api_v1`
- Wetter-Service mit OpenWeatherMap-Anbindung
- SQLite fuer Wetter-Cache und Layout-Konfiguration
- Repository- und Schema-Schicht fuer zentrale Backend-Daten
- Konfigurations-Endpunkte unter `/api/v1/config/layout`, `/api/v1/config/system` und `/api/v1/config/gestures`
- System-Status-Endpunkt mit Datenbank- und Cache-Metadaten
- Gesten-Endpunkte unter `/api/v1/gestures` mit Start, Stop, Status, Debug-Frame, handzentrierter Tracking-Basis, handgroessenbasierter Schwellen-Normalisierung und Confidence-/Tracking-Metadaten
- gemeinsamer WebSocket-Endpunkt `/ws` fuer Realtime-Events wie `GestureDetected`
- Testbasis fuer Wetter, LED, Konfiguration und Gesten

## Noch nicht stabil umgesetzt

- belastbare Kalenderintegration
- echte LED-Steuerung ueber GPIO oder Hardware-Adapter
- MQTT-Integration fuer reale Smart-Home-Faelle
- Frontend-Anbindung an Wetter- und Konfigurations-API
- Frontend-Anbindung an Gesture- und WebSocket-Events
- echte Kamera-Validierung auf Zielhardware
- Authentifizierung und produktionsreife Secret-Verwaltung

## Gesten-Konfiguration

Die Gestenbasis bleibt ueber `/api/v1/config/gestures` konfigurierbar. Dort liegen neben Glättung, Cooldown und Schwellenwerten jetzt auch die Parameter fuer die Handgroessen-Normalisierung. ENV-Werte in `src/core/config.py` bleiben die Defaults; die eigentliche Laufzeitabstimmung erfolgt ueber die bestehende SQLite-basierte Konfigurationsstrategie.

Eine manuelle Zielplattform-Pruefung ist weiterhin noetig. Die aktuelle Checkliste dafuer steht in [docs/GESTURE_VALIDATION.md](../docs/GESTURE_VALIDATION.md).

## Wochenstand Gesten

Der aktuelle Zwischenstand ist bewusst backendzentriert:

- handzentrierte Tracking-Basis statt Wrist-only
- modularisierte Klassifikation mit Features, Kandidaten und Confidence
- persistierbare GestureConfig inklusive Handgroessen-Skalierung
- robusterer Start/Stop- und Fehlerpfad fuer Sessions
- vorbereitete, aber noch nicht implementierte Erweiterungspfade fuer Arm-/Pose-Kontext

## Starten

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
.venv/bin/pytest -q tests
```

## Relevante aktive Doku

- [Ist-Zustand](../docs/CURRENT_STATE.md)
- [Zielarchitektur](../docs/TARGET_ARCHITECTURE.md)
- [Umsetzungsplan](../docs/IMPLEMENTATION_PLAN.md)
