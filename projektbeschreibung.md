# Projektbeschreibung Nimrag

## Kontext

Nimrag ist ein Software-Engineering-Projekt fuer einen Smart Mirror mit Raspberry Pi, Web-UI und optionaler Hardware-Integration.
Das Projekt dient sowohl als Produktprototyp als auch als Architektur- und Lernprojekt.

## Produktidee

Der Spiegel soll zentrale Alltagsinformationen sichtbar machen und spaeter mit Smart-Home- und Hardware-Funktionen erweitert werden.

## Realistischer Projektkern

- Uhr und Datum
- Wetter mit Cache und Fallback
- Kalender
- konfigurierbares Widget-Layout
- stabiles Frontend/Backend-Grundsystem

## Spaetere Erweiterungen

- LED-Steuerung
- MQTT-basierte Smart-Home-Integration
- Sprachsteuerung
- Gestensteuerung
- Mobile Remote

## Technische Leitplanken

- Vue 3 Frontend im Kiosk-Modus
- FastAPI Backend
- SQLite fuer Cache und Konfiguration
- WebSocket fuer Echtzeit-Updates
- Raspberry Pi als Zielplattform

## Weiterfuehrende Doku

- [Dokumentationsuebersicht](docs/README.md)
- [Produktumfang](docs/PRODUCT_SCOPE.md)
- [Zielarchitektur](docs/TARGET_ARCHITECTURE.md)
- [Umsetzungsplan](docs/IMPLEMENTATION_PLAN.md)
