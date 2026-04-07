# Ist-Zustand

## Projektstatus

Die Codebasis ist aktuell ein Architektur- und UI-Prototyp.
Sie zeigt die Richtung des Projekts, aber noch nicht die geplante Systemreife.

## Frontend

### Vorhanden

- Vue 3 Grundsetup
- Grid-Board mit 16 Zellen
- Widget-Shop mit dynamischem Laden von Widget-Komponenten
- einfache Beispiel-Widgets fuer Uhr und Wetter

### Hauptprobleme

- Widget-Verwaltung erfolgt imperativ ueber `document`, `innerHTML` und `createApp()`
- kein zentraler, reaktiver Layout-State
- keine echte Backend-Integration
- keine Persistenz der Konfiguration
- keine Frontend-Tests
- Build/Tooling aktuell inkonsistent

## Backend

### Vorhanden

- FastAPI-App mit API-Router
- klare Request- und Response-Schemas fuer Wetter, LED, System und Layout-Konfiguration
- SQLite-basierte Persistenz fuer Layout-Konfiguration und Wetter-Cache
- Repository-Schicht fuer Konfiguration und Wetterdaten
- Wetter-Endpunkte mit Cache, Timeout-Konfiguration und Fallback auf gecachte Daten
- Konfigurations-Endpunkte zum Laden und Speichern des Layouts
- System-Status-Endpunkt mit echten Backend-Metadaten
- optionale Gesten-Domaene mit Hand-basiertem Adapter, Start/Stop-Session und Dev-Videoverarbeitung
- gemeinsamer WebSocket-Kanal fuer Realtime-Events wie `GestureDetected`
- gruene Backend-Testbasis fuer Wetter, LED, Konfiguration und Gesten

### Hauptprobleme

- Kalender- und Smart-Home-Endpunkte sind weiter Platzhalter
- LED ist aktuell nur als in-memory Mock umgesetzt, nicht als echter Hardware-Adapter
- Gestenerkennung ist noch nicht an das Frontend angebunden
- echte Kamera- und Raspberry-Pi-Verifikation fehlt in der automatisierten Testkette
- es gibt noch keine Authentifizierung, keine Rollen und keine produktionsreife Secret-Verwaltung
- Frontend nutzt die neuen Backend-Funktionen noch nicht

## Integration

Der groesste Bruch liegt zwischen Frontend und Backend:

- das Frontend nutzt keine echten API-Calls
- das Wetter-Widget zeigt statische Daten
- der gemeinsame WebSocket wird im Frontend noch nicht genutzt
- die Konfigurationspersistenz existiert nur im Backend und ist im Frontend noch nicht angebunden

## Dokumentation

Die alte Dokumentation beschreibt eine viel groessere Zielwelt als die aktuelle Codebasis.
Sie ist wertvoll als Verlauf, aber bisher zu gross, mehrfach redundant und teilweise veraltet.

## Was erhalten bleiben sollte

- die modulare Widget-Idee
- FastAPI als Backend-Rahmen
- Vue 3 + TypeScript als Frontend-Basis
- die Fokussierung auf Erweiterbarkeit und Raspberry-Pi-Tauglichkeit
- die definierten Qualitaetsziele fuer Fallback, Reaktionszeit und Wartbarkeit
