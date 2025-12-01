# Backend Gesture Recognition - Quick Start

## Setup (First Time)

### 1. Create/Activate Virtual Environment

```bash
cd Backend
python3.12 -m venv venv_py312_fresh
source venv_py312_fresh/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Tests (No Camera Required)

```bash
python -m pytest tests/test_gestures.py -v
```

Expected: 12 tests PASS ✓

## Start Backend Server

```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit Swagger docs: http://localhost:8000/docs

## Test Gesture Endpoints

### 1. Start Camera

```bash
curl -X POST "http://localhost:8000/api/v1/gestures/start"
```

Response:
```json
{"status": "started"}
```

### 2. Get Status (Raw Movement Data)

```bash
curl "http://localhost:8000/api/v1/gestures/status"
```

Response:
```json
{
  "running": true,
  "movement": {"dx": -0.015, "dy": 0.032},
  "flags": {"down": true, "left": false, "right": false},
  "frame": "data:image/jpeg;base64,..."
}
```

### 3. Get Camera Frame (Base64)

```bash
curl "http://localhost:8000/api/v1/gestures/frame" | jq -r '.image' | base64 -d > frame.jpg
```

### 4. Listen for Gesture Events (WebSocket)

```bash
# Install wscat if needed: npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/gestures/ws"
```

Make a gesture (swipe left/right/down or circle) in front of camera. You should see events like:

```
> {"type": "gesture", "gesture": "swipe_right", "movement": {"dx": 0.18, "dy": -0.02}}
> {"type": "gesture", "gesture": "circle", "movement": {"dx": 0.01, "dy": 0.02}}
```

### 5. Stop Camera

```bash
curl -X POST "http://localhost:8000/api/v1/gestures/stop"
```

## Architecture

```
Camera (OpenCV)
    ↓
Pose Detection (MediaPipe)
    ↓
Center Smoothing (EMA)
    ↓
Trajectory Buffer
    ↓
Gesture Detection (swipes, circle)
    ↓
WebSocket Broadcast
    ↓
Frontend (Vue.js)
    ↓
Widget Movement / Action Triggers
```

## Configurable Parameters

Edit `src/services/gestures.py` constructor to tune:

- `alpha` — smoothing intensity (0.6 default)
- `swipe_thresh` — min displacement for swipe (0.12)
- `circle_sweep_min` — min angle for circle (4.5 rad)
- `gesture_cooldown` — event spam prevention (1.0 sec)

See `GESTURE_RECOGNITION.md` for full documentation.

## Troubleshooting

**"Kamera konnte nicht geöffnet werden"**
- Check camera: `ls /dev/video*`
- Try different index: `?camera_index=1`

**Gestures not detected**
- Ensure full-body visibility
- Try lower threshold: edit `swipe_thresh` in `__init__`

**WebSocket not connecting**
- Verify server is running on port 8000
- Check client URL: `ws://localhost:8000/api/v1/gestures/ws`

## Files Modified/Created

```
Backend/
├── src/
│   ├── services/
│   │   ├── gestures.py (new) — Main gesture service
│   │   └── ws_manager.py (new) — WebSocket broadcaster
│   └── api/api_v1/
│       ├── endpoints/gestures.py (new) — API + WebSocket routes
│       └── api.py (updated) — Router registration
├── tests/
│   └── test_gestures.py (new) — Unit tests (12 tests)
└── GESTURE_RECOGNITION.md (new) — Full documentation
```

## Next Steps

1. **Frontend Integration**: Listen to `/api/v1/gestures/ws` and move widgets on gesture events
2. **Custom Actions**: Map gestures to specific actions (e.g., circle → play music)
3. **Gesture Training**: Allow users to record custom gesture templates
4. **Performance**: Optimize with async processing or lower frame rate
