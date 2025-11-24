| Qualitätsattribut | Verfeinerung            | Szenario (6-Part-Form)                                                                                                                                                                                                                                                            | Business Value | Technical Risk |
| ----------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | -------------- |
| Performance       | Response Time           | Source: Benutzer
Stimulus: Touch-Interaktion auf Widget
Artifact: Frontend UI
Environment: Normalbetrieb
Response: Widget öffnet Detailansicht
Measure: Reaktion erfolgt in < 200ms                                                                                               | H              | M              |
| Performance       | Startup Time            | Source: System
Stimulus: Raspberry Pi bootet
Artifact: Gesamtsystem
Environment: Kaltstart
Response: System ist vollständig einsatzbereit
Measure: Boot in < 60 Sekunden                                                                                                          | H              | H              |
| Performance       | Real-time Processing    | Source: Benutzer
Stimulus: Sprachkommando 'Spiegel, zeige Wetter'
Artifact: Vosk ASR + Backend
Environment: Normalbetrieb
Response: Wetter-Widget wird angezeigt
Measure: Latenz < 500ms                                                                                          | H              | H              |
| Usability         | Ease of Use             | Source: Neuer Benutzer
Stimulus: Erste Nutzung des Spiegels
Artifact: Frontend UI
Environment: Ohne Schulung
Response: Benutzer navigiert erfolgreich zu Kalender-Widget
Measure: Innerhalb von 2 Minuten ohne Anleitung                                                          | H              | L              |
| Usability         | Multi-modal Interaction | Source: Benutzer
Stimulus: Gestensteuerung (Swipe nach links)
Artifact: MediaPipe + Frontend
Environment: 2m Entfernung zum Spiegel
Response: Widget wechselt zum nächsten
Measure: Geste erkannt und ausgeführt in < 500ms                                                       | M              | H              |
| Reliability       | Availability            | Source: Externe API
Stimulus: OpenWeatherMap API ist nicht erreichbar
Artifact: Backend Weather Service
Environment: Normalbetrieb
Response: System zeigt gecachte Wetterdaten
Measure: Keine Unterbrechung, 99.9% Verfügbarkeit                                                  | H              | M              |
| Reliability       | Fault Tolerance         | Source: System
Stimulus: USB-Kamera für Gestensteuerung trennt Verbindung
Artifact: Gesture Recognition Service
Environment: Laufender Betrieb
Response: System deaktiviert Gestensteuerung, andere Funktionen bleiben verfügbar
Measure: Auto-Erkennung in < 5 Sek, kein Absturz | M              | M              |
| Modifiability     | Extensibility           | Source: Entwickler
Stimulus: Neues Widget (z.B. News-Feed) hinzufügen
Artifact: Frontend + Backend
Environment: Entwicklungszeit
Response: Widget wird implementiert und integriert
Measure: Integration in < 4h ohne Änderung bestehender Widgets                                | H              | M              |
| Modifiability     | Configurability         | Source: Benutzer
Stimulus: Layout-Konfiguration ändern (Drag & Drop)
Artifact: Configuration Interface
Environment: Laufzeit
Response: Layout gespeichert & sofort angewendet
Measure: Änderung persistiert in < 2s mit Live-Vorschau                                             | M              | L              |
| Security          | Confidentiality         | Source: Angreifer
Stimulus: Versuch, auf Kalender-API-Credentials zuzugreifen
Artifact: Backend Credential Storage
Environment: Laufzeit
Response: Zugriff verweigert, Credentials verschlüsselt
Measure: Keine Credentials im Klartext                                           | H              | M              |