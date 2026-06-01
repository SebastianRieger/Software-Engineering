<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

const emit = defineEmits(['addWidget'])
const modules = import.meta.glob("../widgets/*.vue")

type ModuleItem = {
  name: string
  path: string
  component: any
}

type DisplayItem = ModuleItem & {
  position: 'left' | 'center' | 'right'
  index: number
}

const moduleList = ref<ModuleItem[]>([])
const currentIndex = ref(0)

const addCurrentWidgetToCell = (cellId: number) => {
  if (!moduleList.value.length) return
  emit('addWidget', { cellId, component: moduleList.value[currentIndex.value]!.component })
}

const nextModule = () => {
  if (!moduleList.value.length) return
  currentIndex.value = (currentIndex.value + 1) % moduleList.value.length
}

const prevModule = () => {
  if (!moduleList.value.length) return
  currentIndex.value = (currentIndex.value - 1 + moduleList.value.length) % moduleList.value.length
}

const displayedModules = computed<DisplayItem[]>(() => {
  const result: DisplayItem[] = []
  const len = moduleList.value.length
  if (!len) return result

  if (len === 1) {
    const base = moduleList.value[0]!
    result.push({ name: base.name, path: base.path, component: base.component, position: 'center', index: 0 })
    return result
  }

  const center = currentIndex.value
  const left  = (center - 1 + len) % len
  const right = (center + 1) % len

  result.push({ ...moduleList.value[left]!,   position: 'left',   index: left })
  result.push({ ...moduleList.value[center]!, position: 'center', index: center })
  result.push({ ...moduleList.value[right]!,  position: 'right',  index: right })

  return result
})

onMounted(async () => {
  for (const path in modules) {
    const fileName = path.split('/').pop()?.replace('.vue', '') || ''
    const moduleLoader = modules[path]
    if (!moduleLoader) continue
    const module = (await moduleLoader()) as any
    moduleList.value.push({ name: fileName, path, component: module.default })
  }
})

const setCurrentModule = (index: number) => {
  if (!moduleList.value.length) return
  currentIndex.value = index
}

defineExpose({ addCurrentWidgetToCell, nextModule, prevModule, setCurrentModule })
</script>

<template>
  <div class="module-shop">

    <!-- Header -->
    <div class="shop-header">
      <h2 class="shop-title">WIDGET SHOP</h2>
      <div v-if="moduleList.length" class="shop-counter">
        <span class="counter-text">{{ currentIndex + 1 }} / {{ moduleList.length }}</span>
        <div class="counter-pips">
          <span
            v-for="i in moduleList.length"
            :key="i"
            class="pip"
            :class="{ 'pip--active': i - 1 === currentIndex }"
          />
        </div>
      </div>
    </div>

    <!-- Carousel -->
    <div v-if="moduleList.length > 0" class="carousel">
      <button @click="prevModule" class="nav-btn" aria-label="Vorheriges Widget">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15,18 9,12 15,6" />
        </svg>
      </button>

      <div class="carousel-stage">
        <div
          v-for="item in displayedModules"
          :key="item.index"
          class="module-card"
          :class="[`pos-${item.position}`, { 'is-active': item.index === currentIndex }]"
          @click="item.position === 'left' ? prevModule() : item.position === 'right' ? nextModule() : undefined"
        >
          <div class="card-top">
            <span class="card-index">{{ String(item.index + 1).padStart(2, '0') }}</span>
            <h4 class="module-name">{{ item.name }}</h4>
          </div>
          <div class="preview-wrap">
            <component v-if="item.position === 'center'" :is="item.component" />
            <div v-else class="preview-skeleton">
              <div class="skel-line" style="width:72%" />
              <div class="skel-line" style="width:52%" />
              <div class="skel-line" style="width:36%" />
            </div>
          </div>
        </div>
      </div>

      <button @click="nextModule" class="nav-btn" aria-label="Nächstes Widget">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
    </div>

    <!-- Loading -->
    <div v-else class="shop-loading">
      <div class="loading-ring" />
    </div>

    <!-- Gesture hint: confirm with push -->
    <div v-if="moduleList.length > 0" class="shop-confirm-hint">
      <span class="confirm-gesture-badge">▶</span>
      <span class="confirm-hint-text">Widget hinzufügen</span>
    </div>

  </div>
</template>

<style scoped>
/* ── Shell ── */
.module-shop {
  background: radial-gradient(ellipse at 50% 0%, #252525 0%, #111111 50%, #050505 100%);
  color: #eeeeee;
  padding: 22px 24px 20px;
  border-radius: 16px;
  height: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.65);
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

/* ── Header ── */
.shop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.shop-title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #ffffff;
}

.shop-counter {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.counter-text {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.35);
}

.counter-pips {
  display: flex;
  gap: 5px;
}

.pip {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  transition: background 0.25s ease, transform 0.25s ease;
}

.pip--active {
  background: #ffffff;
  transform: scale(1.35);
}

/* ── Carousel ── */
.carousel {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.carousel-stage {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1200px;
  min-height: 250px;
}

/* ── Module Card ── */
.module-card {
  position: absolute;
  width: 300px;
  left: 50%;
  margin-left: -150px;
  background: linear-gradient(145deg, #282828, #101010);
  border-radius: 16px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8);
  transition:
    transform 320ms cubic-bezier(0.4, 0, 0.2, 1),
    opacity 320ms ease,
    filter 320ms ease,
    border-color 320ms ease,
    background 320ms ease,
    box-shadow 320ms ease;
}

.module-card.pos-left {
  transform: translateX(-220px) translateY(18px) scale(0.75) rotateY(10deg);
  opacity: 0.28;
  filter: blur(0.5px);
  z-index: 1;
  cursor: pointer;
  transform-origin: right center;
}

.module-card.pos-right {
  transform: translateX(220px) translateY(18px) scale(0.75) rotateY(-10deg);
  opacity: 0.28;
  filter: blur(0.5px);
  z-index: 1;
  cursor: pointer;
  transform-origin: left center;
}

.module-card.pos-center {
  transform: none;
  opacity: 1;
  filter: none;
  z-index: 5;
}

.module-card.is-active {
  border-color: rgba(255, 255, 255, 0.55);
  background: linear-gradient(145deg, #2c2c2c, #131313);
  box-shadow:
    0 10px 40px rgba(0, 0, 0, 0.9),
    inset 0 1px 0 rgba(255, 255, 255, 0.07);
}

.card-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}

.card-index {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
}

.module-name {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 320ms ease;
}

.module-card.is-active .module-name {
  color: #ffffff;
}

.preview-wrap {
  background: #050505;
  border-radius: 10px;
  padding: 10px;
  min-height: 140px;
  max-height: 180px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.preview-skeleton {
  width: 100%;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skel-line {
  height: 9px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.07);
}

/* ── Nav Buttons ── */
.nav-btn {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  background: rgba(12, 12, 12, 0.95);
  color: #b0b0b0;
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
  transition:
    transform 200ms cubic-bezier(0.4, 0, 0.2, 1),
    border-color 200ms ease,
    color 200ms ease,
    box-shadow 200ms ease;
  z-index: 20;
}

.nav-btn svg { width: 20px; height: 20px; }

.nav-btn:hover {
  transform: scale(1.1);
  border-color: rgba(255, 255, 255, 0.50);
  color: #ffffff;
  box-shadow: 0 6px 28px rgba(0, 0, 0, 0.8);
}

.nav-btn:active {
  transform: scale(0.92);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.7);
}

/* ── Loading ── */
.shop-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-ring {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.12);
  border-top-color: rgba(255, 255, 255, 0.65);
  animation: spin 0.85s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Confirm hint ── */
.shop-confirm-hint {
  flex-shrink: 0;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.confirm-gesture-badge {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 0.78rem;
  font-weight: 700;
  color: #ffffff;
}

.confirm-hint-text {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.4);
}

/* ── Responsive ── */
@media (max-width: 700px) {
  .module-shop { padding: 16px 16px 14px; gap: 14px; }

  .shop-title { font-size: 1.1rem; letter-spacing: 0.1em; }

  .carousel-stage { min-height: 200px; }

  .module-card {
    width: 220px;
    margin-left: -110px;
  }
  .module-card.pos-left  { transform: translateX(-155px) translateY(14px) scale(0.73) rotateY(10deg); }
  .module-card.pos-right { transform: translateX(155px)  translateY(14px) scale(0.73) rotateY(-10deg); }

  .preview-wrap { min-height: 110px; max-height: 140px; }

  .nav-btn { width: 38px; height: 38px; }
  .nav-btn svg { width: 16px; height: 16px; }
}

@media (max-width: 480px) {
  .module-shop { padding: 14px 12px 12px; }
  .module-card { width: 190px; margin-left: -95px; }
  .module-card.pos-left  { transform: translateX(-130px) translateY(12px) scale(0.70) rotateY(8deg); }
  .module-card.pos-right { transform: translateX(130px)  translateY(12px) scale(0.70) rotateY(-8deg); }
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .module-card, .nav-btn, .cell-btn, .pip { transition: none; }
  .loading-ring { animation: none; border-top-color: rgba(255,255,255,0.4); }
}
</style>
