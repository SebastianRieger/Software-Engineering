<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useHandTracking } from '../composables/useHandTracking'
import type { BackendCamera } from '../composables/useHomeScreen'

const props = defineProps<{
  cameras: BackendCamera[]
  currentIndex: number
  frameUrl: string | null
  error: string | null
  loading: boolean
  slideDirection: 'up' | 'down' | null
}>()

const emit = defineEmits<{
  swipeLeft: []
  swipeUp: []
  swipeDown: []
}>()

// --- Touch / Maus Wischgesten ---
const touchStart = ref<{ x: number; y: number } | null>(null)
const MIN_SWIPE_PX = 60

function onPointerDown(e: PointerEvent): void {
  touchStart.value = { x: e.clientX, y: e.clientY }
}

function onPointerUp(e: PointerEvent): void {
  if (!touchStart.value) return
  const dx = e.clientX - touchStart.value.x
  const dy = e.clientY - touchStart.value.y
  touchStart.value = null

  if (Math.max(Math.abs(dx), Math.abs(dy)) < MIN_SWIPE_PX) return

  if (Math.abs(dx) > Math.abs(dy)) {
    if (dx < 0) emit('swipeLeft')
  } else {
    if (dy < 0) emit('swipeUp')
    else emit('swipeDown')
  }
}

const currentCameraName = computed(() => {
  const camera = props.cameras[props.currentIndex]
  if (!camera) return 'Kamera'
  return camera.name || `Kamera ${props.currentIndex + 1}`
})

const slideClass = computed(() => {
  if (!props.slideDirection) return ''
  return props.slideDirection === 'down' ? 'slide-in-bottom' : 'slide-in-top'
})

// --- Hand landmark canvas ---
const canvasRef = ref<HTMLCanvasElement | null>(null)
const { trackedHands } = useHandTracking()

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
  const w = canvas.clientWidth || window.innerWidth
  const h = canvas.clientHeight || window.innerHeight
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

    // X gespiegelt weil Video gespiegelt ist
    const x = (pt: [number, number]) => (1 - pt[0]) * canvas.width
    const y = (pt: [number, number]) => pt[1] * canvas.height

    // Verbindungslinien
    ctx.strokeStyle = 'rgba(96, 165, 250, 0.85)'
    ctx.lineWidth = 2.5
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

    // Punkte
    for (const [name, pt] of Object.entries(lm)) {
      const isPalm = PALM_POINTS.has(name)
      const r = isPalm ? 7 : 5
      const px = x(pt)
      const py = y(pt)

      ctx.beginPath()
      ctx.arc(px, py, r, 0, Math.PI * 2)
      ctx.fillStyle = isPalm ? 'rgba(255, 255, 255, 0.95)' : 'rgba(96, 165, 250, 0.95)'
      ctx.fill()

      ctx.beginPath()
      ctx.arc(px, py, r + 1.5, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }
  }
}

const resizeObserver = new ResizeObserver(syncCanvasSize)

onMounted(() => {
  syncCanvasSize()
  if (canvasRef.value?.parentElement) {
    resizeObserver.observe(canvasRef.value.parentElement)
  }
})

onBeforeUnmount(() => {
  resizeObserver.disconnect()
})

watch(trackedHands, drawLandmarks, { deep: true })
</script>

<template>
  <div
    class="home-screen"
    @pointerdown="onPointerDown"
    @pointerup="onPointerUp"
  >

    <!-- Kamerabild vom Backend (gespiegelt) -->
    <div class="camera-feed" :class="slideClass">
      <img
        v-if="frameUrl"
        :src="frameUrl"
        class="camera-video"
        alt=""
        draggable="false"
      />
      <div v-if="loading || !frameUrl" class="camera-state">
        <div class="spinner" />
      </div>
      <div v-else-if="error" class="camera-state camera-state--error">{{ error }}</div>
    </div>

    <!-- Hand-Landmark-Canvas -->
    <canvas ref="canvasRef" class="landmark-canvas" />

    <!-- Top Bar: Branding -->
    <div class="top-bar">
      <div class="brand">
        <span class="brand-name">NIMRAG</span>
        <span class="brand-sub">Gesture Interface</span>
      </div>
      <div v-if="cameras.length > 0" class="cam-status">
        <span class="cam-count">{{ currentIndex + 1 }} / {{ cameras.length }}</span>
        <div class="cam-dot-strip">
          <span
            v-for="i in cameras.length"
            :key="i"
            class="strip-dot"
            :class="{ 'strip-dot--active': i - 1 === currentIndex }"
          />
        </div>
      </div>
    </div>

    <!-- Linke Seite: Wischgeste → Grid -->
    <div class="nav-hint nav-hint--left">
      <div class="nav-hint-card">
        <div class="swipe-demo swipe-demo--left">
          <div class="swipe-track swipe-track--h" />
          <div class="swipe-dot swipe-dot--left" />
        </div>
        <span class="swipe-label">Grid</span>
      </div>
    </div>

    <!-- Rechte Seite: Wischgeste ↕ Kamera -->
    <div v-if="cameras.length > 1" class="nav-hint nav-hint--right">
      <div class="nav-hint-card">
        <div class="swipe-demo swipe-demo--up">
          <div class="swipe-track swipe-track--v" />
          <div class="swipe-dot swipe-dot--up" />
        </div>
        <div class="camera-dots">
          <div
            v-for="i in cameras.length"
            :key="i"
            class="dot"
            :class="{ 'dot--active': i - 1 === currentIndex }"
          />
        </div>
        <div class="swipe-demo swipe-demo--down">
          <div class="swipe-track swipe-track--v" />
          <div class="swipe-dot swipe-dot--down" />
        </div>
        <span class="swipe-label">Kamera</span>
      </div>
    </div>

    <!-- Bottom Bar -->
    <div class="bottom-bar">
      <div class="bottom-gradient" />
      <div class="bottom-content">
        <div class="camera-info">
          <span class="camera-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M23 7l-7 5 7 5V7z"/>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
          </span>
          <span class="camera-name">{{ currentCameraName }}</span>
        </div>
        <div class="hints">
          <span class="hint-chip">
            <span class="hint-chip__gesture">←</span> Grid öffnen
          </span>
          <span v-if="cameras.length > 1" class="hint-chip">
            <span class="hint-chip__gesture">↑↓</span> Kamera wechseln
          </span>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.home-screen {
  position: fixed;
  inset: 0;
  background: #000;
  overflow: hidden;
}

/* ── Kamera (gespiegelt) ── */
.camera-feed {
  position: absolute;
  inset: 0;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transform: scaleX(-1);
  user-select: none;
}

@keyframes slideInFromBottom {
  from { transform: scaleX(-1) translateY(8%); opacity: 0; }
  to   { transform: scaleX(-1) translateY(0);  opacity: 1; }
}
@keyframes slideInFromTop {
  from { transform: scaleX(-1) translateY(-8%); opacity: 0; }
  to   { transform: scaleX(-1) translateY(0);   opacity: 1; }
}

.slide-in-bottom .camera-video { animation: slideInFromBottom 0.35s ease-out; }
.slide-in-top    .camera-video { animation: slideInFromTop    0.35s ease-out; }


.camera-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.6);
}
.camera-state--error { color: #fca5a5; font-size: 0.9rem; padding: 24px; text-align: center; }

.spinner {
  width: 36px; height: 36px;
  border: 3px solid rgba(255,255,255,0.2);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Canvas ── */
.landmark-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* ── Top Bar ── */
.top-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  padding: 18px 24px 32px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.75) 0%, transparent 100%);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  pointer-events: none;
}

.brand { display: flex; flex-direction: column; gap: 2px; }

.brand-name {
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #fff;
  text-shadow: 0 1px 8px rgba(0,0,0,0.6);
}

.brand-sub {
  font-size: 0.62rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.45);
}

.cam-status { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }

.cam-count { font-size: 0.72rem; color: rgba(255,255,255,0.55); letter-spacing: 0.06em; }

.cam-dot-strip { display: flex; gap: 5px; }

.strip-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  transition: all 0.25s ease;
}
.strip-dot--active { background: #fff; transform: scale(1.3); }

/* ── Nav hints ── */
.nav-hint {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}

.nav-hint--left  { left: 12px; }
.nav-hint--right { right: 12px; }

.nav-hint-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  padding: 16px 12px;
}

.swipe-label {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.65);
}

/* ── Swipe-Demos ── */
.swipe-demo {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Horizontal (links) */
.swipe-demo--left {
  width: 64px;
  height: 22px;
}

.swipe-track--h {
  position: absolute;
  inset: 0;
  border-radius: 11px;
  background: linear-gradient(to left, rgba(255,255,255,0.25), rgba(255,255,255,0.03));
}

.swipe-dot--left {
  position: absolute;
  right: 1px;
  width: 22px; height: 22px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #fff 0%, rgba(255,255,255,0.85) 100%);
  box-shadow: 0 0 14px rgba(255,255,255,0.8), 0 0 28px rgba(255,255,255,0.3), 0 0 0 3px rgba(255,255,255,0.15);
  animation: swipe-left 2.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes swipe-left {
  0%, 10%  { transform: translateX(0);    opacity: 0; }
  20%      { transform: translateX(0);    opacity: 1; }
  75%      { transform: translateX(-42px); opacity: 1; }
  90%, 100%{ transform: translateX(-42px); opacity: 0; }
}

/* Vertikal (hoch / runter) */
.swipe-demo--up,
.swipe-demo--down {
  width: 22px;
  height: 64px;
}

.swipe-track--v {
  position: absolute;
  inset: 0;
  border-radius: 11px;
}

.swipe-demo--up .swipe-track--v {
  background: linear-gradient(to top, rgba(255,255,255,0.25), rgba(255,255,255,0.03));
}

.swipe-demo--down .swipe-track--v {
  background: linear-gradient(to bottom, rgba(255,255,255,0.25), rgba(255,255,255,0.03));
}

.swipe-dot--up {
  position: absolute;
  bottom: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: 22px; height: 22px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #fff 0%, rgba(255,255,255,0.85) 100%);
  box-shadow: 0 0 14px rgba(255,255,255,0.8), 0 0 28px rgba(255,255,255,0.3), 0 0 0 3px rgba(255,255,255,0.15);
  animation: swipe-up 2.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes swipe-up {
  0%, 10%  { transform: translateX(-50%) translateY(0);    opacity: 0; }
  20%      { transform: translateX(-50%) translateY(0);    opacity: 1; }
  75%      { transform: translateX(-50%) translateY(-42px); opacity: 1; }
  90%, 100%{ transform: translateX(-50%) translateY(-42px); opacity: 0; }
}

.swipe-dot--down {
  position: absolute;
  top: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: 22px; height: 22px;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #fff 0%, rgba(255,255,255,0.85) 100%);
  box-shadow: 0 0 14px rgba(255,255,255,0.8), 0 0 28px rgba(255,255,255,0.3), 0 0 0 3px rgba(255,255,255,0.15);
  animation: swipe-down 2.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  animation-delay: 1.4s;
}

@keyframes swipe-down {
  0%, 10%  { transform: translateX(-50%) translateY(0);    opacity: 0; }
  20%      { transform: translateX(-50%) translateY(0);    opacity: 1; }
  75%      { transform: translateX(-50%) translateY(42px);  opacity: 1; }
  90%, 100%{ transform: translateX(-50%) translateY(42px);  opacity: 0; }
}

/* ── Camera dots (rechts) ── */
.camera-dots { display: flex; flex-direction: column; gap: 7px; }

.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  transition: all 0.25s ease;
}
.dot--active { background: #fff; transform: scale(1.5); }

/* ── Bottom Bar ── */
.bottom-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  pointer-events: none;
}

.bottom-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.82) 0%, transparent 100%);
}

.bottom-content {
  position: relative;
  padding: 36px 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.camera-info { display: flex; align-items: center; gap: 8px; }

.camera-icon { width: 18px; height: 18px; color: rgba(255,255,255,0.6); flex-shrink: 0; }
.camera-icon svg { width: 100%; height: 100%; }

.camera-name {
  font-size: 1.05rem;
  font-weight: 600;
  color: #fff;
  letter-spacing: 0.01em;
}

.hints { display: flex; gap: 10px; flex-wrap: wrap; }

.hint-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 20px;
  font-size: 0.75rem;
  color: rgba(255,255,255,0.8);
  letter-spacing: 0.02em;
}

.hint-chip__gesture {
  font-weight: 700;
  color: #fff;
  background: rgba(255,255,255,0.18);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.8rem;
}
</style>
