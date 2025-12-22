Sprech‑Stichpunkte zur Demo (kurz)

- Einleitung: Dieses Video zeigt die Backend‑Gestenerkennung; die `DEMO.sh` sendet eine Datei an den API‑Endpoint `/api/v1/gestures/process-video`.
- Was das Terminal zeigt: 1) Backend‑Check (Port 8000) 2) Pfad zur Video‑Datei 3) POST‑Request an den Endpoint 4) JSON‑Antwort mit erkannten Gesten.
- Frame‑Verarbeitung: Das Backend liest das Video frame‑weise mit OpenCV ein und extrahiert pro Frame Landmarken mit MediaPipe Pose.
- Wichtige Landmarken: Wir verwenden z. B. das Handgelenk, um die Handposition über die Zeit zu verfolgen (Trajektorie).
- Stabilisierung: Rohdaten werden geglättet (EMA) und in einem kurzen Sliding‑Buffer gehalten, damit Ruckler nicht zu Fehlalarmen führen.
- Erkennungslogik (Kurz): Für Kreise messen wir den Winkelumlauf (angular sweep) und prüfen die Radius‑Streuung; für Swipes messen wir große Verschiebungen entlang einer Achse.
- Entscheidung: Bei Erkennung sendet das Backend ein JSON wie `{"gestures": ["circle"], "frames_processed": 79}` zurück — das ist die sichtbare Bestätigung im Terminal/Log.
- Live vs. Demo‑Video: Im Live‑System ist der Ablauf identisch — statt Datei kommt ein Kamerastream (Webcam); Frames werden kontinuierlich verarbeitet und erkannte Gesten per WebSocket an Clients gesendet.
- Was die Teammitglieder zeigen sollten: kurz den POST‑Aufruf, das daraus resultierende JSON, und grafisch (falls möglich) die Hand‑Trajektorie / das erkannte Event erwähnen.
- Häufige Fragen vorbereiten: Warum kein False‑Positive? (Antwort: Smoothing und Schwellen/Buffer reduzieren Rauschen. Einstellungen sind konfigurierbar.)
- Tipp für Sprecher: Vor dem Video kurz sagen, dass dies ein aufgezeichnetes Beispiel ist, das identisch zur Live‑Erkennung funktioniert — somit demonstriert das Video das reale Verhalten.

Ein‑Folie‑Zusammenfassung (1–2 Sätze):
Das Backend verarbeitet Video‑Frames mit MediaPipe Pose, baut daraus eine geglättete Hand‑Trajektorie auf und erkennt Muster (Kreis, Swipe) über Winkel‑ und Verschiebungsmetriken; erkannte Gesten werden als JSON ausgegeben und im Live‑Betrieb per WebSocket an die UI verteilt.