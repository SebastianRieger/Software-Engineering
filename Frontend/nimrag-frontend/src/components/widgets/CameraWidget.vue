<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useGestureFrameStream } from '../../services/gestureFrameStream'
import { buildApiUrl } from '../../services/apiConfig'
import { useHandTracking } from '../../composables/useHandTracking'

const { frameUrl, start, stop } = useGestureFrameStream()
const { trackedHands } = useHandTracking()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const captureStatus = ref<'idle' | 'running' | 'done' | 'error'>('idle')
const captureOutputDir = ref<string | null>(null)
const showDevCapture = import.meta.env.DEV
let captureStatusTimer: ReturnType<typeof window.setTimeout> | null = null
let resizeObserver: ResizeObserver | null = null

const CONNECTIONS: [string, string][] = [
  ['wrist', 'thumb_cmc'],
  ['thumb_cmc', 'thumb_mcp'],
  ['thumb_mcp', 'thumb_ip'],
  ['thumb_ip', 'thumb_tip'],
  ['index_mcp', 'middle_mcp'],
  ['middle_mcp', 'ring_mcp'],
  ['ring_mcp', 'pinky_mcp'],
  ['index_mcp', 'index_pip'],
  ['index_pip', 'index_dip'],
  ['index_dip', 'index_tip'],
  ['middle_mcp', 'middle_pip'],
  ['middle_pip', 'middle_dip'],
  ['middle_dip', 'middle_tip'],
  ['ring_mcp', 'ring_pip'],
  ['ring_pip', 'ring_dip'],
  ['ring_dip', 'ring_tip'],
  ['pinky_mcp', 'pinky_pip'],
  ['pinky_pip', 'pinky_dip'],
  ['pinky_dip', 'pinky_tip'],
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

async function startDevCapture(): Promise<void> {
  if (captureStatus.value === 'running') return

  if (captureStatusTimer !== null) {
    window.clearTimeout(captureStatusTimer)
    captureStatusTimer = null
  }

  captureStatus.value = 'running'
  captureOutputDir.value = null
  try {
    const res = await fetch(buildApiUrl('gestures/dev/capture'), { method: 'POST' })
    if (!res.ok) throw new Error(`capture failed: ${res.status}`)
    const data = (await res.json()) as { output_dir?: string }
    captureOutputDir.value = data.output_dir ?? null
    captureStatusTimer = window.setTimeout(() => {
      if (captureStatus.value === 'running') captureStatus.value = 'done'
    }, 3400)
  } catch {
    captureStatus.value = 'error'
  }
}

onMounted(() => {
  start()
  syncCanvasSize()
  if (typeof ResizeObserver !== 'undefined' && canvasRef.value?.parentElement) {
    resizeObserver = new ResizeObserver(syncCanvasSize)
    resizeObserver.observe(canvasRef.value.parentElement)
  }
})

onBeforeUnmount(() => {
  if (captureStatusTimer !== null) {
    window.clearTimeout(captureStatusTimer)
    captureStatusTimer = null
  }
  resizeObserver?.disconnect()
  resizeObserver = null
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
    <button
      v-if="showDevCapture"
      class="dev-capture-button"
      type="button"
      :disabled="captureStatus === 'running'"
      :title="captureOutputDir || 'Speichert 3 Sekunden Gestenframes nach pics/'"
      @click.stop="startDevCapture"
    >
      {{
        captureStatus === 'running'
          ? 'Capturing...'
          : captureStatus === 'done'
            ? 'Saved'
            : captureStatus === 'error'
              ? 'Error'
              : 'Capture 3s'
      }}
    </button>
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

.dev-capture-button {
  position: absolute;
  right: 8px;
  bottom: 8px;
  z-index: 2;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(0, 0, 0, 0.68);
  color: #fff;
  font-size: 12px;
  line-height: 1;
  padding: 7px 9px;
  cursor: pointer;
}

.dev-capture-button:disabled {
  cursor: wait;
  opacity: 0.7;
}

@media (prefers-reduced-motion: reduce) {
  .scan-ring,
  .scan-dot { animation: none; }
}
</style>
