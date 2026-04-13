# Ist-Zustand

## Projektstatus

Die Codebasis ist aktuell ein Architektur- und UI-Prototyp.
Sie zeigt die Richtung des Projekts, aber noch nicht die geplante Systemreife.

## Frontend

### Vorhanden

- Vue 3 Grundsetup
- Grid-Board mit 16 Zellen und zustandsgetriebener Widget-Belegung
- Widget-Shop ueber gemeinsames Widget-Registry-Konzept
- Wetter-Widget mit echter Backend-Anbindung
- Layout-Laden und -Speichern gegen die Backend-Konfigurations-API
- kleiner typisierter Frontend-API-Client fuer Wetter und Konfiguration

### Hauptprobleme

- keine Frontend-Tests
- keine zentrale State- oder Store-Loesung fuer spaetere groeessere Frontend-Features
- Wetter- und Konfigurationsintegration decken bisher nur den ersten Verticalschnitt ab

## Backend

### Vorhanden

- FastAPI-App mit API-Router
- klare Request- und Response-Schemas fuer Wetter, LED, System und Layout-Konfiguration
- SQLite-basierte Persistenz fuer Layout-Konfiguration und Wetter-Cache
- Repository-Schicht fuer Konfiguration und Wetterdaten
- Wetter-Endpunkte mit Cache, Timeout-Konfiguration und Fallback auf gecachte Daten
- Konfigurations-Endpunkte fuer Layout und generische Systemkonfiguration
- System-Status-Endpunkt mit echten Backend-Metadaten
- Gesten-Backend mit MediaPipe-Hands-Adapter, handzentrierter Tracking-Basis, Start/Stop-Session und Dev-Videoverarbeitung
- gemeinsamer WebSocket-Kanal fuer Realtime-Events wie `GestureDetected`
- gruene Backend-Testbasis fuer Wetter, LED, Konfiguration und Gesten

### Hauptprobleme

- Kalender- und Smart-Home-Endpunkte sind weiter Platzhalter
- LED ist aktuell nur als in-memory Mock umgesetzt, nicht als echter Hardware-Adapter
- Gestenerkennung ist backendseitig vorhanden, aber noch nicht an Frontend-Consumer oder fachliche UI-Kommandos angebunden
- echte Kamera- und Raspberry-Pi-Verifikation fehlt in der automatisierten Testkette
- es gibt noch keine Authentifizierung, keine Rollen und keine produktionsreife Secret-Verwaltung
- Frontend deckt bisher nur Wetter und Konfiguration ab, nicht die restlichen Backend-Domaenen

## Aktueller Gestenstand

- Die Erkennung ist nicht mehr nur auf einen einzelnen Wrist-Punkt gedacht, sondern wird auf eine handzentrierte Tracking-Basis aus Wrist und palmnahen Handpunkten gehoben
- Swipe- und Circle-Schwellwerte werden jetzt zusaetzlich gegen eine geschaetzte Handgroesse beziehungsweise Palmspanne skaliert, damit Kameraabstand und Perspektive die Basisgesten weniger stark verzerren
- Tuningparameter fuer Gesten koennen ueber die bestehende Konfigurationspersistenz backendseitig gehalten werden
- Der Gestenservice liefert jetzt einen expliziteren Fehlerzustand fuer Laufzeitprobleme
- Start/Stop, Join-Timeout und transiente Adapter-Lesefehler sind im Backend robuster abgesichert und besser testbar gemacht
- Die Klassifikation ist in Richtung Feature- und Kandidatenlogik modularisiert und liefert Confidence- sowie Tracking-Metadaten
- Offene Kernluecken bleiben echte Hardwarevalidierung, weitere Gestentypen, optionale Arm-/Pose-Erweiterung und spaetere Frontend-Nutzung der Events

## Integration

Der groesste Bruch liegt zwischen Frontend und Backend:

- der gemeinsame WebSocket wird im Frontend noch nicht genutzt
- weitere Domaenen wie Kalender, Smart Home und Gesten sind im Frontend noch nicht angebunden

## Aktueller Integrationsstand B1/B2

- B1 ist als erster produktiver Schnitt umgesetzt: `GET/PUT /api/v1/config/layout` und `GET/PUT /api/v1/config/system`
- B1 nutzt weiter die bestehende `app_config`-Tabelle in SQLite und trennt Layout- und Systemdaten nur ueber Konfigurationskeys
- B2 ist im Frontend als kleiner fetch-basierter API-Client umgesetzt
- Das Grid rendert Widgets jetzt ueber Vue-State statt ueber HTML-Swaps
- Das Wetter-Widget laedt Wetterdaten ueber Backend plus Systemkonfiguration und zeigt Loading- oder Fehlerzustand statt statischer Platzhalterdaten

## Dokumentation

Die alte Dokumentation beschreibt eine viel groessere Zielwelt als die aktuelle Codebasis.
Sie ist wertvoll als Verlauf, aber bisher zu gross, mehrfach redundant und teilweise veraltet.

## Was erhalten bleiben sollte

- die modulare Widget-Idee
- FastAPI als Backend-Rahmen
- Vue 3 + TypeScript als Frontend-Basis
- die Fokussierung auf Erweiterbarkeit und Raspberry-Pi-Tauglichkeit
- die definierten Qualitaetsziele fuer Fallback, Reaktionszeit und Wartbarkeit
