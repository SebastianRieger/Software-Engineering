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

const emit = defineEmits<{ goToGrid: [] }>()

// --- Camera display ---
const currentCameraName = computed(() => {
  const camera = props.cameras[props.currentIndex]
  if (!camera) return 'Kamera'
  return camera.name || `Kamera ${props.currentIndex + 1}`
})

const slideClass = computed(() => {
  if (!props.slideDirection) return ''
  return props.slideDirection === 'down' ? 'slide-from-bottom' : 'slide-from-top'
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
  <div class="home-screen">

    <!-- Kamerabild (gespiegelt) -->
    <div class="camera-feed" :class="slideClass">
      <img
        v-if="frameUrl"
        :src="frameUrl"
        class="camera-video"
        alt=""
        draggable="false"
      />
      <div v-if="loading || !frameUrl" class="camera-state">
        <div class="camera-state-inner">
          <div class="scan-ring" />
          <div class="scan-dot" />
        </div>
      </div>
      <div v-else-if="error" class="camera-state camera-state--error">
        <div class="error-inner">
          <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>{{ error }}</span>
        </div>
      </div>
    </div>

    <!-- Hand-Landmark-Canvas -->
    <canvas ref="canvasRef" class="landmark-canvas" />

    <!-- Top Bar -->
    <div class="top-bar">
      <div class="brand">
        <span class="brand-name">NIMRAG</span>
        <span class="brand-sub">Gesture Interface</span>
      </div>
      <div v-if="cameras.length > 0" class="cam-status">
        <span class="cam-count">{{ currentIndex + 1 }} / {{ cameras.length }}</span>
        <div class="cam-pips">
          <span
            v-for="i in cameras.length"
            :key="i"
            class="pip"
            :class="{ 'pip--active': i - 1 === currentIndex }"
          />
        </div>
      </div>
    </div>

    <!-- Linke Seite: nach links wischen → Grid -->
    <div class="nav-hint nav-hint--left">
      <div class="nav-hint-card">
        <div class="swipe-demo swipe-demo--left">
          <div class="swipe-track swipe-track--h" />
          <div class="swipe-dot swipe-dot--left" />
        </div>
        <div class="hint-label-group">
          <svg class="hint-dest-icon" viewBox="0 0 20 20" fill="none">
            <rect x="1" y="1" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            <rect x="11" y="1" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            <rect x="1" y="11" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            <rect x="11" y="11" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
          </svg>
          <div class="hint-label-text">
            <span class="hint-action">Wische links</span>
            <span class="hint-dest">Grid öffnen</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Rechte Seite: nach oben/unten wischen → Kamera -->
    <div v-if="cameras.length > 1" class="nav-hint nav-hint--right">
      <div class="nav-hint-card">

        <div class="cam-nav-row cam-nav-row--up">
          <span class="cam-nav-label">Vorherige</span>
          <div class="swipe-demo swipe-demo--up">
            <div class="swipe-track swipe-track--v" />
            <div class="swipe-dot swipe-dot--up" />
          </div>
        </div>

        <div class="camera-dots">
          <div
            v-for="i in cameras.length"
            :key="i"
            class="cdot"
            :class="{ 'cdot--active': i - 1 === currentIndex }"
          />
        </div>

        <div class="cam-nav-row cam-nav-row--down">
          <div class="swipe-demo swipe-demo--down">
            <div class="swipe-track swipe-track--v" />
            <div class="swipe-dot swipe-dot--down" />
          </div>
          <span class="cam-nav-label">Nächste</span>
        </div>

        <div class="hint-label-group hint-label-group--cam">
          <svg class="hint-dest-icon" viewBox="0 0 20 16" fill="none">
            <path d="M19 3.5l-5.5 3.5 5.5 3.5V3.5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <rect x="1" y="1" width="12" height="14" rx="2" stroke="currentColor" stroke-width="1.5"/>
          </svg>
          <div class="hint-label-text">
            <span class="hint-action">Wische auf/ab</span>
            <span class="hint-dest">Kamera wechseln</span>
          </div>
        </div>

      </div>
    </div>

    <!-- Bottom Bar -->
    <div class="bottom-bar">
      <div class="bottom-gradient" />
      <div class="bottom-content">
        <div class="cam-info">
          <svg class="cam-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round">
            <path d="M23 7l-7 5 7 5V7z"/>
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
          </svg>
          <span class="cam-name">{{ currentCameraName }}</span>
        </div>
        <div class="hint-chips">
          <span class="chip">
            <span class="chip-key">←</span> Grid öffnen
          </span>
          <span v-if="cameras.length > 1" class="chip">
            <span class="chip-key">↑↓</span> Kamera wechseln
          </span>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* ── Shell ── */
.home-screen {
  position: fixed;
  inset: 0;
  background: #000;
  overflow: hidden;
  cursor: default;
  user-select: none;
}

/* ── Kamera-Feed ── */
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
  pointer-events: none;
}

/* Slide-Animationen auf dem Container, nicht dem Bild */
@keyframes slideFromBottom {
  from { opacity: 0; transform: translateY(6%); }
  to   { opacity: 1; transform: translateY(0);   }
}
@keyframes slideFromTop {
  from { opacity: 0; transform: translateY(-6%); }
  to   { opacity: 1; transform: translateY(0);   }
}

.slide-from-bottom { animation: slideFromBottom 0.38s cubic-bezier(0.4, 0, 0.2, 1); }
.slide-from-top    { animation: slideFromTop    0.38s cubic-bezier(0.4, 0, 0.2, 1); }

/* ── Camera States ── */
.camera-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.55);
}

.camera-state-inner {
  position: relative;
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
}

.scan-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.18);
  border-top-color: rgba(255, 255, 255, 0.75);
  animation: spin 1s linear infinite;
}

.scan-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  animation: pulse 1s ease-in-out infinite alternate;
}

@keyframes spin   { to { transform: rotate(360deg); } }
@keyframes pulse  { from { opacity: 0.3; } to { opacity: 1; } }

.camera-state--error { background: rgba(0, 0, 0, 0.68); }

.error-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
}

.error-icon {
  width: 32px;
  height: 32px;
  color: #fca5a5;
  opacity: 0.8;
}

.camera-state--error span {
  color: #fca5a5;
  font-size: 0.88rem;
  max-width: 28ch;
  line-height: 1.5;
}

/* ── Landmark Canvas ── */
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
  top: 0;
  left: 0;
  right: 0;
  padding: 18px 24px 36px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.78) 0%, transparent 100%);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  pointer-events: none;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.brand-name {
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #fff;
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.7);
}

.brand-sub {
  font-size: 0.58rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.38);
}

.cam-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.cam-count {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.40);
}

.cam-pips {
  display: flex;
  gap: 5px;
}

.pip {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  transition: background 0.25s ease, transform 0.25s ease;
}

.pip--active {
  background: #fff;
  transform: scale(1.35);
}

/* ── Nav Hints ── */
.nav-hint {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

.nav-hint--left  { left: 14px; }
.nav-hint--right { right: 14px; }

.nav-hint-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.50);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 18px;
  padding: 14px 12px;
  width: 96px;
}

/* Shared label group below swipe animation */
.hint-label-group {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 2px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  width: 100%;
}

.hint-label-group--cam {
  padding-top: 4px;
  margin-top: 2px;
}

.hint-dest-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.35);
}

.hint-label-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.hint-action {
  font-size: 0.58rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.32);
  text-transform: uppercase;
}

.hint-dest {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.75);
}

/* Camera nav rows */
.cam-nav-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.cam-nav-row--up  { flex-direction: column; }
.cam-nav-row--down { flex-direction: column; }

.cam-nav-label {
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.38);
}

/* ── Swipe Demos ── */
.swipe-demo {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.swipe-demo--left { width: 60px; height: 20px; }

.swipe-track--h {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  background: linear-gradient(to left, rgba(255, 255, 255, 0.22), rgba(255, 255, 255, 0.02));
}

.swipe-dot--left {
  position: absolute;
  right: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 38%, #fff 0%, rgba(255,255,255,0.88) 100%);
  box-shadow:
    0 0 12px rgba(255, 255, 255, 0.75),
    0 0 0 2.5px rgba(255, 255, 255, 0.12);
  animation: swipeLeft 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes swipeLeft {
  0%, 12%  { transform: translateX(0);     opacity: 0; }
  22%      { transform: translateX(0);     opacity: 1; }
  74%      { transform: translateX(-40px); opacity: 1; }
  88%, 100%{ transform: translateX(-40px); opacity: 0; }
}

.swipe-demo--up,
.swipe-demo--down {
  width: 20px;
  height: 60px;
}

.swipe-track--v {
  position: absolute;
  inset: 0;
  border-radius: 10px;
}

.swipe-demo--up   .swipe-track--v { background: linear-gradient(to top,    rgba(255,255,255,0.22), rgba(255,255,255,0.02)); }
.swipe-demo--down .swipe-track--v { background: linear-gradient(to bottom, rgba(255,255,255,0.22), rgba(255,255,255,0.02)); }

.swipe-dot--up {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 38%, #fff 0%, rgba(255,255,255,0.88) 100%);
  box-shadow:
    0 0 12px rgba(255, 255, 255, 0.75),
    0 0 0 2.5px rgba(255, 255, 255, 0.12);
  animation: swipeUp 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes swipeUp {
  0%, 12%  { transform: translateX(-50%) translateY(0);    opacity: 0; }
  22%      { transform: translateX(-50%) translateY(0);    opacity: 1; }
  74%      { transform: translateX(-50%) translateY(-40px); opacity: 1; }
  88%, 100%{ transform: translateX(-50%) translateY(-40px); opacity: 0; }
}

.swipe-dot--down {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 38%, #fff 0%, rgba(255,255,255,0.88) 100%);
  box-shadow:
    0 0 12px rgba(255, 255, 255, 0.75),
    0 0 0 2.5px rgba(255, 255, 255, 0.12);
  animation: swipeDown 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  animation-delay: 1.5s;
}

@keyframes swipeDown {
  0%, 12%  { transform: translateX(-50%) translateY(0);    opacity: 0; }
  22%      { transform: translateX(-50%) translateY(0);    opacity: 1; }
  74%      { transform: translateX(-50%) translateY(40px);  opacity: 1; }
  88%, 100%{ transform: translateX(-50%) translateY(40px);  opacity: 0; }
}

/* Camera position dots */
.camera-dots { display: flex; flex-direction: column; gap: 6px; }

.cdot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  transition: background 0.25s ease, transform 0.25s ease;
}

.cdot--active {
  background: #fff;
  transform: scale(1.5);
}

/* ── Bottom Bar ── */
.bottom-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  pointer-events: none;
}

.bottom-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.85) 0%, transparent 100%);
}

.bottom-content {
  position: relative;
  padding: 40px 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cam-info {
  display: flex;
  align-items: center;
  gap: 9px;
}

.cam-icon {
  width: 17px;
  height: 17px;
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.55);
}

.cam-name {
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: #fff;
}

.hint-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  background: rgba(255, 255, 255, 0.09);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.72);
  letter-spacing: 0.02em;
}

.chip-key {
  font-weight: 700;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.78rem;
}

/* ── Reduced Motion ── */
@media (prefers-reduced-motion: reduce) {
  .slide-from-bottom,
  .slide-from-top {
    animation: none;
    opacity: 1;
    transform: none;
  }

  .swipe-dot--left,
  .swipe-dot--up,
  .swipe-dot--down {
    animation: none;
    opacity: 0.6;
    transform: translateX(-50%);
  }

  .swipe-dot--left {
    transform: translateX(-20px);
  }

  .scan-ring,
  .scan-dot {
    animation: none;
    border-top-color: rgba(255, 255, 255, 0.5);
    opacity: 0.7;
  }

  .pip,
  .cdot {
    transition: none;
  }
}
</style>
