# Umsetzungsplan

## Grundsatz

Der Weg zur Zielarchitektur erfolgt in kleinen vertikalen Schritten.
Erst stabile Kernfunktionen, dann Realtime und Hardware, zuletzt optionale High-Risk-Features.

## Phase 0: Scope und Dokumentation stabilisieren

### Ziel

Eine kleine, aktuelle und verbindliche Dokumentationsbasis schaffen.

### Ergebnis

- aktive Kernseiten statt vieler konkurrierender Dokumente
- Archiv fuer alte Artefakte
- klares Sollbild fuer Teamarbeit und Reviews

## Phase 1: Frontend-Grundstruktur reparieren

### Ziel

Das Frontend von imperativer DOM-Logik auf datengetriebenen Vue-State umstellen.

### Aufgaben

- Grid-State als Datenmodell einfuehren
- Widget-Instanzen sauber rendern
- `innerHTML`-Swap und manuelles `createApp()` entfernen
- Widget-Registry aufbauen
- Konfigurationsdialog vereinfachen

### Done-Kriterien

- Widgets werden rein ueber Vue-State verwaltet
- Drag-and-Drop oder Layout-Aenderungen zerstoeren keine Komponenteninstanzen
- Frontend baut lokal stabil

### Status

In Arbeit, aber der erste tragende Teil ist umgesetzt.
Das Grid rendert Widgets inzwischen ueber Vue-State, nutzt eine Widget-Registry und ist nicht mehr auf HTML-Swap plus `createApp()` fuer den Normalfall angewiesen.

## Phase 2: Backend als belastbare Basis aufbauen

### Ziel

Aus Platzhalter-API wird ein kleines, konsistentes Backend.

### Status

Weitgehend umgesetzt.
Die Basis fuer Wetter, Konfiguration, SQLite, Repository-Schicht und API-Tests steht.

### Aufgaben

- Request- und Response-Schemas vereinheitlichen
- `config`, `repositories` und `schemas` einfuehren
- SQLite fuer Konfiguration und Cache anbinden
- Logging und Fehlerbehandlung strukturieren
- Tests auf echte API-Contracts ausrichten

### Done-Kriterien

- Wetter- und Konfigurationsdaten sind persistierbar
- Tests passen zur echten API
- keine widerspruechlichen Endpunkte mehr

### Ergebnis

- Wetter-Endpunkte liefern typisierte Antworten und nutzen Cache plus Fallback
- Layout-Konfiguration kann gespeichert und wieder geladen werden
- Systemstatus spiegelt reale Backend-Metadaten
- Backend-Tests sind gruen
- offen bleiben vor allem Kalender, Smart-Home, echte Hardware-Adapter und Frontend-Anbindung

## Phase 3: Erste echte Verticals liefern

### Ziel

Wetter, Uhr und Kalender als zusammenhaengende Kernfunktionen fertigstellen.

### Aufgaben

- Wetter mit Cache, Timeout und Fallback
- Kalender mindestens mit klarer Mock- oder echter Integration
- Layout + Widget-Konfiguration speichern und laden
- Frontend an Backend anbinden

### Status

Teilweise umgesetzt.
Der erste B1/B2-Schnitt ist geliefert: Backend-Konfiguration deckt jetzt Layout plus Systemkonfiguration ab, das Frontend nutzt einen kleinen API-Client, das Wetter-Widget arbeitet gegen echte Backend-Daten und das Layout wird geladen und gespeichert.

### Done-Kriterien

- Anwendung startet mit gespeicherter Konfiguration
- Wetter und Kalender kommen aus echter Backend-Logik
- API-Ausfaelle blockieren die UI nicht

### Bereits geliefert in diesem Schnitt

- `GET/PUT /api/v1/config/layout` bleibt die Basis fuer Widget-Layout-Persistenz
- `GET/PUT /api/v1/config/system` liefert den ersten Vertrag fuer allgemeine Systemeinstellungen
- Frontend-API-Client fuer Wetter und Konfiguration ist vorhanden
- Weather-Widget hat Loading- und Fehlerzustand statt statischer Demo-Daten
- Frontend-Build ist mit dem neuen Integrationsschnitt validiert

### Offen in Phase 3

- Kalender weiter von Platzhalter auf echte oder klar gemockte Integration heben
- Systemkonfiguration im Frontend editierbar machen
- weitere Widgets auf denselben API- und State-Ansatz umstellen

## Phase 4: Realtime und optionale Hardware vorbereiten

### Ziel

WebSocket, LED und MQTT sauber, aber klein integrieren.

### Status

Teilweise umgesetzt.
Der gemeinsame WebSocket-Kanal existiert jetzt als kleiner Realtime-Hub und wird bereits fuer `GestureDetected`-Events genutzt.

### Aufgaben

- WebSocket-Nachrichtenformat definieren
- Backend-Status- und Update-Events einfuehren
- LED-Adapter mit Mock und echtem Adapter aufbauen
- MQTT nur fuer reale Hardware- oder Smart-Home-Faelle nutzen

### Done-Kriterien

- WebSocket uebertraegt fachliche Updates statt Echo-Text
- LED- und MQTT-Integration ist austauschbar und testbar

### Offene Punkte

- weitere fachliche Eventtypen definieren
- Frontend an den gemeinsamen WebSocket anbinden
- LED und MQTT auf echte Adapter heben

### Neues Arbeitspaket: Gestensteuerung haerten und erweitern

### Ziel

Die vorhandene Gestensteuerung backendseitig robuster, konfigurierbarer und fachlich praeziser machen, ohne dafuer auf teure Vollkoerpererkennung als Standardpfad umzusteigen.

### Aufgaben

- handzentrierte Tracking-Basis aus Wrist und palmnahen Landmarken statt reiner Wrist-Trajektorie etablieren
- die Basisschwellwerte gegen Handgroesse oder Palmspanne normalisieren, damit der Wochenstand nicht mehr von starren Bildkoordinaten abhaengt
- Runtime-Zustand und Fehlerverhalten im GestureService haerten
- Gestentuning ueber persistierbare Backend-Konfiguration statt nur ueber ENV-Defaults steuern
- Gestenstatus, Dev-Verarbeitung und Testfaelle erweitern
- Klassifikation in Features, Kandidaten und Metadaten zerlegen, damit weitere Gestentypen spaeter nicht wieder in monolithischer Heuristik enden

### Done-Kriterien

- bestehende Gestenerkennung bleibt regressionsfrei
- Status- und Fehlerverhalten des GestureService sind nachvollziehbar
- Gestenkonfiguration ist speicher- und ladbar
- Ereignisse und Status tragen fachlich brauchbare Metadaten wie Confidence und Tracking-Quelle
- die aktuelle Basiserkennung bleibt auch bei unterschiedlichen Handgroessen oder Kameraabstaenden fachlich plausibel
- es gibt eine dokumentierte manuelle Hardware-Checkliste fuer Kamera- und Raspberry-Pi-Verifikation
- aktive Dokumentation beschreibt den echten Reifegrad der Gestenarchitektur

## Phase 5: High-Risk-Features isoliert angehen

### Ziel

Voice, Gesture und weitere ambitionierte Features ohne Kernsystem-Risiko evaluieren.

### Status

Teilweise vorgezogen.
Im Backend existiert jetzt ein optionaler Gesten-Kern mit Hand-basierter Erkennung, Start/Stop-Sessionmodell und Dev-Videoverarbeitung.

### Aufgaben

- Voice- und Gesture-Adapter als separate Module
- Performance-Messung auf Raspberry Pi
- klare Fallbacks bei Ausfall oder Ueberlastung

### Done-Kriterien

- Kernsystem bleibt ohne diese Features stabil
- Zusatzfeatures koennen bei Bedarf deaktiviert werden

### Offene Punkte

- echte Hardware- und Kamera-Validierung auf Zielplattform
- Frontend-Nutzung der Gesture-Events
- moegliche spaetere Verfeinerung von Heuristiken oder Handlandmarks

## Prioritaeten fuer das Team

1. Frontend-State und Layout-Modell
2. Frontend an Wetter- und Konfigurations-API anbinden
3. Kalender als naechste echte Kernfunktion
4. Realtime
5. LED und MQTT
6. Voice und Gesture

## Was bewusst nicht zuerst gebaut werden sollte

- Mobile App
- Cloud-LLM
- komplexe Rechte- und Rollensysteme
- verteilte Event-Infrastruktur
- neue Features ohne stabile Kernbasis
