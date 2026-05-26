# Nimrag Backend

FastAPI-Backend fuer den Nimrag Smart Mirror.

## Status

Das Backend ist jetzt eine kleine, konsistente Basis statt nur eines reinen Prototyps.
Die Kernpfade fuer Wetter, Konfiguration, Systemstatus und einen optionalen Gesten-Backend-Kern sind umgesetzt, weitere Bereiche sind noch bewusst reduziert oder Platzhalter.

## Derzeit vorhanden

- flacher API-Router unter `src/api/` mit `system_endpoints.py`, `device_endpoints.py` und `data_endpoints.py`
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
- breitere Frontend-Anbindung ueber Wetter, Konfiguration und den aktuellen Hardware-Status-Slice hinaus
- weitergehende Frontend-Nutzung der Gesture- und WebSocket-Events
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
cd ..
npm run setup:backend
npm run dev:backend
```

Falls auch das Frontend vorbereitet werden soll:

```bash
cd ..
npm run setup
```

Der Root-Bootstrapper erstellt bei Bedarf `Backend/.venv`, installiert `requirements.txt` mit einem unterstuetzten Python-Interpreter und startet das Backend anschliessend ohne manuelle Venv-Aktivierung. Unterstuetzt sind Python 3.11 bis 3.13, bevorzugt wird 3.12. Fuer Linux zieht das Setup `numpy<2` vor, baut `aubio` separat ohne Build-Isolation und installiert danach die restlichen Requirements.

## Native Abhaengigkeiten

Der Musical-Audio-Pfad nutzt aubio bewusst als Pflichtkomponente fuer Live-Pitch- und Onset-Erkennung. Auf Fedora muss vor der Python-Installation der Requirements mindestens Folgendes vorhanden sein:

```bash
sudo dnf install -y python3.12-devel aubio-devel aubio-lib
```

`python3.12-devel` liefert `Python.h` fuer native Builds, `aubio-devel` liefert `aubio.pc` fuer `pkg-config`, und `aubio-lib` stellt die Laufzeitbibliothek bereit. Unter Windows sollte Python 3.12 inklusive Python Launcher installiert sein, damit `py -3.12` vom Root-Bootstrapper gefunden wird. Der Root-Bootstrapper ueberspringt `aubio` auf Windows bewusst, wenn keine nativen Build-Werkzeuge vorhanden sind; das Backend startet trotzdem, waehrend der optionale Musical-Audio-Pfad dann als nicht verfuegbar markiert bleibt. Falls die automatische Interpreter-Erkennung nicht greift, kann der Pfad ueber `SMART_MIRROR_PYTHON` gesetzt werden.

## Tests

```bash
./.venv/bin/python -m pytest -q tests
```

Unter Windows entspricht das `./.venv/Scripts/python.exe -m pytest -q tests`.

## Quality-Metriken

Der repo-weite Quality-Lauf wird am Root des Repos gestartet:

```bash
npm run quality
```

Einzelne Teilketten lassen sich separat ausfuehren:

```bash
npm run quality:backend
npm run quality:frontend
npm run quality:duplication
npm run quality:aggregate
```

Die erzeugten Artefakte landen unter `reports/quality/`. Die erste Ausbaustufe arbeitet bewusst report-only: Test-, Coverage-, Lint-, Typecheck-, Complexity- und Duplication-Daten werden gesammelt und aggregiert, aber noch nicht als harte Merge-Gates verwendet.

## Relevante aktive Doku

- [Ist-Zustand](../docs/CURRENT_STATE.md)
- [Zielarchitektur](../docs/TARGET_ARCHITECTURE.md)
