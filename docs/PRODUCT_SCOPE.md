# Produktumfang

## Ziel

Nimrag soll ein modularer Smart Mirror fuer den Raspberry Pi sein, der alltagsrelevante Informationen stabil, lesbar und erweiterbar anzeigt.

## Projektkern

Der realistische Kern des Projekts ist:

- ein stabiles Widget-Board im Browser/Kiosk-Modus
- Uhr und Datum
- Wetter mit lokalem Cache und Fallback
- Kalender
- speicherbare Layout- und Widget-Konfiguration
- klares Frontend/Backend-Vertragsmodell

## Primarer Nutzwert

- Informationen auf einen Blick
- einfache visuelle Orientierung
- spaetere Erweiterbarkeit statt hart verdrahteter Einzelfunktionen

## In Scope fuer die naechste belastbare Version

- Vue-Frontend mit reaktivem Widget-State
- Drag-and-Drop oder klarer Layout-Editor
- Wetterdaten aus echter API mit Cache
- Kalenderdaten aus echter oder klar gemockter Quelle
- Konfigurationsspeicherung in SQLite
- WebSocket fuer echte Push-Updates nur dort, wo es Mehrwert bringt
- einfache LED- und MQTT-Schnittstellen als vorbereitete Adapter

## Bewusst nach hinten verschoben

- verteilte Event-Driven-Architektur mit Redis oder Event Sourcing
- vollwertige Mobile App
- cloudbasierte LLM-Sprachverarbeitung
- Gesichtserkennung und Profile
- komplexe Multi-User- und Rollenlogik

## Nicht als MVP behandeln

- Voice und Gesture als produktkritische Kernfunktion
- universelle Smart-Home-Plattform
- Microservice-Landschaft

## Technische Leitplanken

- Zielplattform: Raspberry Pi 4/5 im Kiosk-Modus
- Frontend: Vue 3, TypeScript, Vite
- Backend: FastAPI
- Persistenz: SQLite
- Realtime: WebSocket
- Hardware/IoT: GPIO und MQTT nur ueber entkoppelte Adapter

## Erfolgsdefinition

Das Projekt ist technisch auf Kurs, wenn:

- Frontend und Backend sauber integriert sind
- Wetter und Kalender als echte vertikale Features funktionieren
- Konfiguration speicherbar und reproduzierbar ist
- Ausfaelle externer APIs die UI nicht blockieren
- neue Widgets ohne Umbau des Kerns ergaenzt werden koennen
