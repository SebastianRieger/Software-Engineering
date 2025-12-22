# 🎥 Gesture Recognition Demo für Zwischenpräsentation

## Quick Demo (< 2 Minuten)

### Schritt 1: Backend starten

```bash
cd Backend/src
uvicorn main:app --host 0.0.0.0 --port 8000
```

Warte bis: `Uvicorn running on http://0.0.0.0:8000`

### Schritt 2: Demo ausführen

In anderem Terminal:

```bash
cd Backend
bash DEMO.sh
```

**Expected Output:**
```
✓ SUCCESS! Circle gesture correctly detected!
  Gesture Detected:    circle
  Frames Processed:    79
  Trajectory Points:   79
```

---

## Was wurde implementiert

✅ **Video Processing Endpunkt**
- `POST /api/v1/gestures/process-video`
- Akzeptiert lokale Video-Datei (MKV, MP4, etc.)
- Verarbeitet alle Frames mit MediaPipe Pose
- Erkennt Gesten aus Körperbewegung

✅ **Circle Gesture Detection**
- Analysiert Trajektorie der Körperposition
- Erkennt Kreisbewegungen (Wellen, Drehungen)
- Angular sweep: ~223°
- Validiert Radius-Konsistenz

✅ **API Response**
```json
{
  "gestures": ["circle"],
  "frames_processed": 79,
  "trajectory_points": 79
}
```

---

## Video-Details

**Datei:** `video Kreisbewegung.mkv`
- **Größe:** 79 Frames @ 30 FPS ≈ 2.6 Sekunden
- **Inhalt:** Person zeigt Kreisbewegung mit Faust
- **Erkennung:** ✓ Circle gesture erfolgreich erkannt

---

## Technologie

| Komponente | Tech |
|---|---|
| Backend | FastAPI (Python) |
| Pose Detection | MediaPipe Pose |
| Video I/O | OpenCV |
| Gesture Recognition | Trajectory Analysis + Circle Detection |

---

## Für Präsentation verwenden

```bash
# Terminal 1: Backend starten
cd Backend/src && uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Demo laufen lassen (Live!)
cd Backend && bash DEMO.sh
```

Oder manuell mit curl:

```bash
curl -X POST "http://localhost:8000/api/v1/gestures/process-video?video_path=/path/to/video%20Kreisbewegung.mkv"
```

---

## Architektur

```
Video File (MKV)
    ↓
OpenCV VideoCapture
    ↓
MediaPipe Pose Detection (per frame)
    ↓
Smoothing + Trajectory Buffer
    ↓
Circle Detection Algorithm
    ↓
HTTP Response (JSON)
```

## Nächste Schritte

1. ✓ Video processing implementiert
2. ✓ Circle detection funktioniert
3. ⬜ Integration mit Frontend (GestureWidget.vue)
4. ⬜ Weitere Gesten (Swipe-Varianten)
5. ⬜ Live-Kamera integration
