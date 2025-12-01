<!--
Minimal Vue.js component example: Listen to gesture events and move widgets.
This can be integrated into the nimrag-frontend project.

Usage:
  <GestureWidget />

Features:
- Connects to gesture WebSocket
- Polls camera frame every 200ms
- Moves widgets based on gestures
- Displays live camera preview
-->

<template>
  <div class="gesture-control">
    <!-- Camera Preview -->
    <div class="camera-section">
      <h3>Camera Feed</h3>
      <img v-if="frame" :src="frame" alt="Camera" class="camera-preview" />
      <p v-else class="loading">Loading camera...</p>
    </div>

    <!-- Status & Gesture Info -->
    <div class="info-section">
      <div class="status">
        <span :class="{ active: isRunning }" class="status-light"></span>
        {{ isRunning ? 'Camera Running' : 'Stopped' }}
      </div>
      <div class="last-gesture">
        Last Gesture: <strong>{{ lastGesture || 'none' }}</strong>
      </div>
      <div class="movement-info">
        Movement: dx={{ movement.dx.toFixed(3) }} | dy={{ movement.dy.toFixed(3) }}
      </div>
    </div>

    <!-- Control Buttons -->
    <div class="controls">
      <button @click="startCamera" :disabled="isRunning" class="btn-primary">
        Start Camera
      </button>
      <button @click="stopCamera" :disabled="!isRunning" class="btn-danger">
        Stop Camera
      </button>
    </div>

    <!-- Demo Widgets (Move by Gestures) -->
    <div class="widgets-demo">
      <h3>Demo Widgets (Move with Gestures)</h3>
      <div
        v-for="(widget, idx) in widgets"
        :key="idx"
        :style="{ transform: `translate(${widget.x}px, ${widget.y}px)` }"
        class="widget"
        @click="widget.color = getRandomColor()"
      >
        {{ widget.label }}
      </div>
    </div>

    <!-- Gesture Binding Editor (Optional) -->
    <div class="bindings-section">
      <h3>Gesture → Action Bindings</h3>
      <div v-for="(action, gesture) in gestureBindings" :key="gesture" class="binding">
        <label>
          <strong>{{ gesture }}</strong>:
          <select v-model="gestureBindings[gesture]">
            <option value="move_left">Move Widget Left</option>
            <option value="move_right">Move Widget Right</option>
            <option value="move_down">Move Widget Down</option>
            <option value="play_music">Play Music</option>
            <option value="change_color">Change Color</option>
            <option value="none">None</option>
          </select>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const frame = ref<string | null>(null)
const lastGesture = ref<string>('')
const isRunning = ref(false)
const movement = ref({ dx: 0, dy: 0 })

let ws: WebSocket | null = null
let framePolling: number | null = null

// Demo widgets to move
const widgets = ref([
  { label: 'Widget 1', x: 50, y: 50, color: '#FF6B6B' },
  { label: 'Widget 2', x: 200, y: 50, color: '#4ECDC4' },
  { label: 'Widget 3', x: 350, y: 50, color: '#45B7D1' },
])

// Gesture bindings: what action each gesture triggers
const gestureBindings = ref({
  swipe_left: 'move_left',
  swipe_right: 'move_right',
  swipe_down: 'move_down',
  circle: 'play_music',
})

// Connect to WebSocket
const connectWebSocket = () => {
  ws = new WebSocket('ws://localhost:8000/api/v1/gestures/ws')

  ws.onopen = () => {
    console.log('[GestureWidget] WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'gesture') {
        handleGesture(data.gesture, data.movement)
      }
    } catch (e) {
      console.error('[GestureWidget] Message parse error:', e)
    }
  }

  ws.onerror = (err) => {
    console.error('[GestureWidget] WebSocket error:', err)
  }

  ws.onclose = () => {
    console.warn('[GestureWidget] WebSocket closed, reconnecting...')
    setTimeout(connectWebSocket, 3000)
  }
}

// Handle gesture and execute bound action
const handleGesture = (gesture: string, mov: { dx: number; dy: number }) => {
  lastGesture.value = gesture
  movement.value = mov

  const action = gestureBindings.value[gesture as keyof typeof gestureBindings.value]
  if (!action || action === 'none') return

  console.log(`[Gesture] ${gesture} → ${action}`)

  const step = 30
  switch (action) {
    case 'move_left':
      widgets.value.forEach((w) => (w.x = Math.max(0, w.x - step)))
      break
    case 'move_right':
      widgets.value.forEach((w) => (w.x = Math.min(800 - 100, w.x + step)))
      break
    case 'move_down':
      widgets.value.forEach((w) => (w.y = Math.min(400 - 50, w.y + step)))
      break
    case 'play_music':
      playAudio()
      break
    case 'change_color':
      widgets.value.forEach((w) => (w.color = getRandomColor()))
      break
  }
}

// Start camera and polling
const startCamera = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/v1/gestures/start', {
      method: 'POST',
    })
    if (res.ok) {
      isRunning.value = true
      connectWebSocket()
      pollFrame()
      console.log('[GestureWidget] Camera started')
    }
  } catch (e) {
    console.error('[GestureWidget] Failed to start camera:', e)
  }
}

// Stop camera
const stopCamera = async () => {
  try {
    await fetch('http://localhost:8000/api/v1/gestures/stop', {
      method: 'POST',
    })
    isRunning.value = false
    if (ws) ws.close()
    if (framePolling) clearTimeout(framePolling)
    console.log('[GestureWidget] Camera stopped')
  } catch (e) {
    console.error('[GestureWidget] Failed to stop camera:', e)
  }
}

// Poll for frames
const pollFrame = async () => {
  if (!isRunning.value) return

  try {
    const res = await fetch('http://localhost:8000/api/v1/gestures/frame')
    if (res.ok) {
      const data = await res.json()
      frame.value = data.image
    }
  } catch (e) {
    console.error('[GestureWidget] Frame poll error:', e)
  }

  framePolling = window.setTimeout(pollFrame, 200)
}

const getRandomColor = (): string => {
  const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA502', '#95E1D3', '#F38181']
  return colors[Math.floor(Math.random() * colors.length)]
}

const playAudio = (): void => {
  // Example: play a simple beep
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
  const osc = audioContext.createOscillator()
  const gain = audioContext.createGain()
  osc.connect(gain)
  gain.connect(audioContext.destination)
  osc.frequency.value = 440
  gain.gain.setValueAtTime(0.1, audioContext.currentTime)
  gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)
  osc.start(audioContext.currentTime)
  osc.stop(audioContext.currentTime + 0.5)
}

// Lifecycle
onMounted(() => {
  console.log('[GestureWidget] Component mounted')
  startCamera()
})

onUnmounted(() => {
  console.log('[GestureWidget] Component unmounted')
  stopCamera()
})
</script>

<style scoped>
.gesture-control {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.camera-section {
  margin-bottom: 20px;
}

.camera-preview {
  max-width: 400px;
  border: 2px solid #ddd;
  border-radius: 8px;
  display: block;
}

.loading {
  color: #999;
}

.info-section {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.info-section > div {
  margin: 5px 0;
}

.status-light {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ccc;
  margin-right: 8px;
}

.status-light.active {
  background: #4caf50;
}

.controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.btn-primary,
.btn-danger {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
}

.btn-primary {
  background: #2196f3;
  color: white;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.widgets-demo {
  margin: 30px 0;
  border: 2px dashed #ddd;
  padding: 20px;
  border-radius: 8px;
  position: relative;
  height: 300px;
  background: #fafafa;
}

.widget {
  position: absolute;
  width: 100px;
  height: 50px;
  background: #4ecdc4;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.widget:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.bindings-section {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
  margin-top: 20px;
}

.binding {
  margin: 10px 0;
}

.binding label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.binding select {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}
</style>
