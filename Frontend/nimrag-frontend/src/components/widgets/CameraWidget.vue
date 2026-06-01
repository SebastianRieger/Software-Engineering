<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useGestureFrameStream } from '../../services/gestureFrameStream'
import { useHandTracking } from '../../composables/useHandTracking'

const { frameUrl, start, stop } = useGestureFrameStream()
const { trackedHands } = useHandTracking()

const canvasRef = ref<HTMLCanvasElement | null>(null)

const CONNECTIONS: [string, string][] = [
  ['wrist', 'index_mcp'],
  ['wrist', 'middle_mcp'],
  ['wrist', 'ring_mcp'],
  ['wrist', 'pinky_mcp'],
  ['index_mcp', 'middle_mcp'],
  ['middle_mcp', 'ring_mcp'],
  ['ring_mcp', 'pinky_mcp'],
  ['index_mcp', 'index_tip'],
  ['middle_mcp', 'middle_tip'],
  ['ring_mcp', 'ring_tip'],
  ['pinky_mcp', 'pinky_tip'],
  ['wrist', 'thumb_tip'],
]

const PALM_POINTS = new Set(['wrist', 'index_mcp', 'middle_mcp', 'ring_mcp', 'pinky_mcp'])

function syncCanvasSize(): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const parent = canvas.parentElement
  const w = parent?.clientWidth || 320
  const h = parent?.clientHeight || 240
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w
    canvas.height = h
  }
}

function drawLandmarks(): void {
  syncCanvasSize()
  const canvas = canvasRef.value
  if (!canvas || canvas.width === 0 || canvas.height === 0) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (const hand of trackedHands.value) {
    const lm = hand.landmarks
    if (!lm) continue

    // X gespiegelt wie das Videobild
    const x = (pt: [number, number]) => (1 - pt[0]) * canvas.width
    const y = (pt: [number, number]) => pt[1] * canvas.height

    ctx.strokeStyle = 'rgba(96, 165, 250, 0.85)'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    for (const [a, b] of CONNECTIONS) {
      const ptA = lm[a]
      const ptB = lm[b]
      if (!ptA || !ptB) continue
      ctx.beginPath()
      ctx.moveTo(x(ptA), y(ptA))
      ctx.lineTo(x(ptB), y(ptB))
      ctx.stroke()
    }

    for (const [name, pt] of Object.entries(lm)) {
      const isPalm = PALM_POINTS.has(name)
      const r = isPalm ? 5 : 3.5
      const px = x(pt)
      const py = y(pt)

      ctx.beginPath()
      ctx.arc(px, py, r, 0, Math.PI * 2)
      ctx.fillStyle = isPalm ? 'rgba(255,255,255,0.95)' : 'rgba(96,165,250,0.95)'
      ctx.fill()

      ctx.beginPath()
      ctx.arc(px, py, r + 1.2, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(0,0,0,0.30)'
      ctx.lineWidth = 1.2
      ctx.stroke()
    }
  }
}

const resizeObserver = new ResizeObserver(syncCanvasSize)

onMounted(() => {
  start()
  syncCanvasSize()
  if (canvasRef.value?.parentElement) {
    resizeObserver.observe(canvasRef.value.parentElement)
  }
})

onBeforeUnmount(() => {
  resizeObserver.disconnect()
  stop()
})

watch(trackedHands, drawLandmarks, { deep: true })
</script>

<template>
  <div class="camera-widget">
    <img
      v-if="frameUrl"
      :src="frameUrl"
      class="camera-feed"
      alt=""
      draggable="false"
    />
    <div v-else class="camera-placeholder">
      <div class="scan-ring" />
      <div class="scan-dot" />
    </div>
    <canvas ref="canvasRef" class="landmark-canvas" />
  </div>
</template>

<style scoped>
.camera-widget {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  overflow: hidden;
}

.camera-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transform: scaleX(-1);
  pointer-events: none;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: #000;
}

.scan-ring {
  position: absolute;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.18);
  border-top-color: rgba(255, 255, 255, 0.75);
  animation: spin 1s linear infinite;
}

.scan-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  animation: pulse 1s ease-in-out infinite alternate;
}

@keyframes spin  { to { transform: rotate(360deg); } }
@keyframes pulse { from { opacity: 0.3; } to { opacity: 1; } }

.landmark-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .scan-ring,
  .scan-dot { animation: none; }
}
</style>
