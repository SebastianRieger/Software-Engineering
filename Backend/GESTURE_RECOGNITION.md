# Gesture Recognition System

## Overview

The gesture recognition system uses MediaPipe Pose and OpenCV to detect user movements from a camera feed and classify them as discrete gestures (swipe_left, swipe_right, swipe_down, circle). Recognized gestures are broadcast to connected WebSocket clients.

## Architecture

### Components

1. **GestureService** (`services/gestures.py`)
   - Main service: camera capture, pose detection, gesture recognition
   - Runs in background thread to avoid blocking
   - Smooths center-of-body position using exponential moving average (EMA)
   - Maintains trajectory buffer for gesture detection
   - Thread-safe state using locks

2. **WebSocketManager** (`services/ws_manager.py`)
   - Manages connected WebSocket clients
   - Broadcasts gesture events to all clients
   - Gracefully handles disconnections

3. **API Endpoints** (`api_v1/endpoints/gestures.py`)
   - `POST /gestures/start` — Start camera capture
   - `POST /gestures/stop` — Stop camera capture
   - `GET /gestures/status` — Get current movement/gesture state
   - `GET /gestures/frame` — Get latest camera frame (base64)
   - `WS /gestures/ws` — WebSocket for real-time gesture events

## Gesture Recognition Details

### Detected Gestures

| Gesture | Trigger | Description |
|---------|---------|-------------|
| **swipe_right** | Horizontal movement + | Body center moves right by >0.12 (normalized coords) |
| **swipe_left** | Horizontal movement − | Body center moves left by >0.12 |
| **swipe_down** | Vertical movement ↓ | Body center moves down by >0.12 |
| **circle** | Circular motion | Angular sweep >4.5 rad (~258°), radius variance <50% |

### Detection Process

1. **Pose Detection**: MediaPipe Pose detects body landmarks (nose, shoulders) each frame
2. **Smoothing**: Center point smoothed with EMA (α=0.6) to reduce noise
3. **Trajectory**: Last 64 positions stored in normalized coordinates
4. **Gesture Matching**: Trajectory analyzed for swipes/circles
5. **Cooldown**: Same gesture suppressed for 1.0 sec to prevent spam
6. **Broadcast**: Gesture events sent to all connected WebSocket clients

### Thresholds & Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `alpha` (EMA) | 0.6 | Smoothing factor; higher = more responsive |
| `max_traj` | 64 | Trajectory buffer size (frames) |
| `gesture_cooldown` | 1.0 sec | Min time between same gesture events |
| `swipe_thresh` | 0.12 | Min displacement for swipe (normalized) |
| `down_thresh` | 0.12 | Min displacement for swipe_down |
| `circle_sweep` | 4.5 rad | Min angular sweep for circle detection |
| `circle_cv` | 0.5 | Max radius coefficient of variation |

**Customization**: Edit these in `GestureService.__init__()` and `_detect_gesture()`.

## Usage

### Quick Start (Python)

```python
from services.gestures import gesture_service

# Start camera (camera must be available)
gesture_service.start()

# Fetch status (includes movement deltas and frame)
status = gesture_service.get_status()
print(status["movement"])  # {"dx": 0.01, "dy": 0.02}
print(status["flags"])      # {"down": False, "left": False, "right": True}

# Stop camera
gesture_service.stop()
```

### HTTP API Examples

**Start Camera**
```bash
curl -X POST "http://localhost:8000/api/v1/gestures/start?camera_index=0"
```

**Get Status**
```bash
curl "http://localhost:8000/api/v1/gestures/status"
```
Response:
```json
{
  "running": true,
  "movement": {"dx": -0.01, "dy": 0.05},
  "flags": {"down": true, "left": false, "right": false},
  "frame": "data:image/jpeg;base64,..."
}
```

**Get Frame Preview**
```bash
curl "http://localhost:8000/api/v1/gestures/frame" | jq -r '.image' > frame.jpg
```

**WebSocket Connection**
```bash
# Connect and listen for gesture events
wscat -c ws://localhost:8000/api/v1/gestures/ws

# Typical event:
# {"type": "gesture", "gesture": "swipe_right", "movement": {"dx": 0.15, "dy": -0.02}}
```

**Stop Camera**
```bash
curl -X POST "http://localhost:8000/api/v1/gestures/stop"
```

## Frontend Integration

### Example Vue.js Component

```vue
<template>
  <div class="gesture-monitor">
    <img v-if="frame" :src="frame" alt="Camera" class="preview" />
    <div class="info">
      <p>Last Gesture: {{ lastGesture }}</p>
      <p>Movement: dx={{ movement.dx.toFixed(3) }}, dy={{ movement.dy.toFixed(3) }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const frame = ref(null)
const lastGesture = ref('')
const movement = ref({ dx: 0, dy: 0 })
let ws = null

const connect = () => {
  ws = new WebSocket('ws://localhost:8000/api/v1/gestures/ws')
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.type === 'gesture') {
      lastGesture.value = data.gesture
      movement.value = data.movement
    }
  }
  ws.onclose = () => setTimeout(connect, 3000)
}

const startCamera = async () => {
  await fetch('http://localhost:8000/api/v1/gestures/start', { method: 'POST' })
  connect()
  pollFrame()
}

const pollFrame = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/v1/gestures/frame')
    const data = await res.json()
    frame.value = data.image
  } catch (e) {
    console.error(e)
  }
  setTimeout(pollFrame, 200)
}

onMounted(startCamera)

onUnmounted(async () => {
  if (ws) ws.close()
  await fetch('http://localhost:8000/api/v1/gestures/stop', { method: 'POST' })
})
</script>

<style scoped>
.preview { max-width: 300px; }
</style>
```

### Widget Movement Example

```javascript
// Listen for gestures and move widgets
const gestures = {
  'swipe_left': () => moveWidget('left'),
  'swipe_right': () => moveWidget('right'),
  'swipe_down': () => moveWidget('down'),
  'circle': () => playMusic(),
}

ws.onmessage = (e) => {
  const data = JSON.parse(e.data)
  if (data.type === 'gesture' && gestures[data.gesture]) {
    gestures[data.gesture]()
  }
}
```

## Testing

All gesture detection logic is tested with synthetic trajectories (no camera required):

```bash
cd Backend
source venv_py312/bin/activate
pip install -r requirements.txt
python -m pytest tests/test_gestures.py -v
```

**Test Coverage**:
- Gesture detection (swipe_left, swipe_right, swipe_down, circle)
- Noise rejection (small random movements)
- Service initialization and lifecycle
- Smoothing logic
- Cooldown mechanism

## Troubleshooting

### Camera Not Opening
- Verify camera device is available: `ls /dev/video*`
- Check permissions: `ls -l /dev/video0`
- Try different camera index: `?camera_index=1`

### Gestures Not Detected
- Ensure good lighting and full-body visibility
- Increase trajectory buffer: raise `max_traj`
- Lower thresholds: reduce `swipe_thresh`, `down_thresh`
- Check MediaPipe pose confidence: raise min_detection_confidence in `start()`

### High CPU Usage
- Reduce frame rate: increase sleep in `_run()` loop
- Lower MediaPipe processing: use `Lite` model variant (if available)
- Disable frame encoding: comment out JPEG encoding

### WebSocket Not Broadcasting
- Verify endpoint is registered in `api_v1/api.py`
- Check client connection: `ws://localhost:8000/api/v1/gestures/ws`
- Monitor logs for errors in `ws_manager.broadcast()`

## Future Enhancements

- [ ] Hand-based gestures (HandLandmark instead of Pose)
- [ ] Custom gesture training (e.g., user-specific swipe sensitivity)
- [ ] Gesture combination sequences (e.g., swipe_left + swipe_down = action)
- [ ] Performance optimization: async pose processing
- [ ] Multi-camera support
- [ ] Gesture recording & replay
