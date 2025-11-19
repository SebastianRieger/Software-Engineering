<script setup lang="ts">
import { ref, onMounted, defineEmits, defineExpose, computed } from 'vue'

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

// Widget in Zelle einfügen
const addCurrentWidgetToCell = (cellId: number) => {
  if (!moduleList.value.length) return
  emit('addWidget', { cellId, component: moduleList.value[currentIndex.value]!.component })
}

// Navigation
const nextModule = () => {
  if (!moduleList.value.length) return
  currentIndex.value = (currentIndex.value + 1) % moduleList.value.length
}

const prevModule = () => {
  if (!moduleList.value.length) return
  currentIndex.value =
      (currentIndex.value - 1 + moduleList.value.length) % moduleList.value.length
}

// Drei sichtbare Karten: links – center – rechts
const displayedModules = computed<DisplayItem[]>(() => {
  const result: DisplayItem[] = []
  const len = moduleList.value.length
  if (!len) return result

  // Spezialfall: nur ein Modul -> nur Center anzeigen
  if (len === 1) {
    const base = moduleList.value[0]!
    result.push({
      name: base.name,
      path: base.path,
      component: base.component,
      position: 'center',
      index: 0
    })
    return result
  }

  const center = currentIndex.value
  const left = (center - 1 + len) % len
  const right = (center + 1) % len

  const leftBase = moduleList.value[left]!
  const centerBase = moduleList.value[center]!
  const rightBase = moduleList.value[right]!

  result.push({
    name: leftBase.name,
    path: leftBase.path,
    component: leftBase.component,
    position: 'left',
    index: left
  })

  result.push({
    name: centerBase.name,
    path: centerBase.path,
    component: centerBase.component,
    position: 'center',
    index: center
  })

  result.push({
    name: rightBase.name,
    path: rightBase.path,
    component: rightBase.component,
    position: 'right',
    index: right
  })

  return result
})

onMounted(async () => {
  for (const path in modules) {
    const fileName = path.split('/').pop()?.replace('.vue', '') || ''
    const moduleLoader = modules[path]
    if (!moduleLoader) continue

    const module = (await moduleLoader()) as any
    moduleList.value.push({
      name: fileName,
      path,
      component: module.default
    })
  }
})
const setCurrentModule = (index: number) => {
  if (!moduleList.value.length) return
  currentIndex.value = index
}

defineExpose({
  nextModule,
  prevModule,
  setCurrentModule
})
</script>

<template>
  <div class="module-shop">
    <h3 class="title">Widget Shop</h3>

    <div v-if="moduleList.length > 0" class="carousel">
      <!-- Navigation -->
      <button @click="prevModule" class="nav-btn nav-btn-left">‹</button>

      <!-- Track mit 3 Karten -->
      <div class="carousel-track">
        <div
            v-for="item in displayedModules"
            :key="item.index"
            class="module-card"
            :class="[
      `pos-${item.position}`,
      { 'is-active': item.index === currentIndex }
    ]"
        >
          <h4 class="module-name">{{ item.name }}</h4>

          <div class="preview-container">
            <component
                v-if="item.position === 'center'"
                :is="item.component"
            />
            <div v-else class="preview-placeholder">
              Vorschau
            </div>
          </div>
        </div>
      </div>

      <button @click="nextModule" class="nav-btn nav-btn-right">›</button>
    </div>

    <div v-else class="loading">
      Loading modules...
    </div>

    <!-- Cell-Auswahl bleibt unten drunter -->
    <div
        v-if="moduleList.length > 0"
        class="cell-selection"
    >
      <p>Add to cell:</p>
      <div class="cell-buttons">
        <button
            v-for="cellId in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]"
            :key="cellId"
            @click="addCurrentWidgetToCell(cellId)"
            class="cell-btn"
        >
          {{ cellId }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.module-shop {
  background: radial-gradient(circle at top, #333 0, #181818 40%, #050505 100%);
  color: #eee;
  padding: 15px 24px 15px;
  border-radius: 16px;
  width: min(900px, 100vw - 48px);
  max-height: 85vh;
  box-sizing: border-box;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.04);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.title {
  text-align: center;
  margin-bottom: 24px;
  font-size: 1.6rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #f5f5f5;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}

.carousel {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-inline: 60px;
  margin-bottom: 20px;
  max-width: 100%;
  box-sizing: border-box;
  overflow: visible;
  min-height: 280px;
  flex-shrink: 0;
}

.carousel-track {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  width: 100%;
  max-width: 320px;
  perspective: 1400px;
  perspective-origin: center center;
}

/*animation*/
@keyframes slideInFromLeft {
  0% {
    opacity: 0;
    transform: translateX(-180px) translateY(60px) scale(0.5) rotateY(35deg) rotateZ(-8deg);
    filter: blur(4px) brightness(0.6);
  }
  60% {
    opacity: 0.3;
    transform: translateX(-240px) translateY(28px) scale(0.72) rotateY(12deg) rotateZ(-2deg);
    filter: blur(1px) brightness(0.85);
  }
  100% {
    opacity: 0.25;
    transform: translateX(-240px) translateY(25px) scale(0.75) rotateY(10deg) rotateZ(0deg);
    filter: blur(0.75px) brightness(0.9);
  }
}

@keyframes slideInFromRight {
  0% {
    opacity: 0;
    transform: translateX(180px) translateY(60px) scale(0.5) rotateY(-35deg) rotateZ(8deg);
    filter: blur(4px) brightness(0.6);
  }
  60% {
    opacity: 0.3;
    transform: translateX(240px) translateY(28px) scale(0.72) rotateY(-12deg) rotateZ(2deg);
    filter: blur(1px) brightness(0.85);
  }
  100% {
    opacity: 0.25;
    transform: translateX(240px) translateY(25px) scale(0.75) rotateY(-10deg) rotateZ(0deg);
    filter: blur(0.75px) brightness(0.9);
  }
}

@keyframes slideToCenter {
  0% {
    opacity: 0.25;
    transform: scale(0.75) translateY(25px) rotateY(0deg);
    filter: blur(0.75px) brightness(0.9);
  }
  40% {
    opacity: 0.6;
    transform: scale(0.95) translateY(5px) rotateY(0deg);
    filter: blur(0.3px) brightness(0.95);
  }
  100% {
    opacity: 1;
    transform: scale(1.2) translateY(-8px) rotateY(0deg);
    filter: none;
  }
}

/*
@keyframes pulseGlow {

  0%, 100% {
    box-shadow:
        0 20px 60px rgba(0, 0, 0, 0.9),
        0 0 40px rgba(80, 160, 255, 0.3),
        inset 0 0 20px rgba(80, 160, 255, 0.1);
  }
  50% {
    box-shadow:
        0 28px 80px rgba(0, 0, 0, 0.95),
        0 0 70px rgba(80, 160, 255, 0.6),
        inset 0 0 35px rgba(80, 160, 255, 0.2);
  }
}
*/

@keyframes shimmer {
  0% {
    background-position: -200% center;
  }
  100% {
    background-position: 200% center;
  }
}
.module-card {
  position: absolute;
  width: 320px;
  min-width: 0;
  background: linear-gradient(145deg, #2a2a2a, #0f0f0f);
  border-radius: 16px;
  padding: 14px;
  overflow: hidden;
  opacity: 0.8;
  transform: scale(0.8) translateY(25px);
  filter: blur(0.75px) brightness(0.9);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition:
      transform 350ms cubic-bezier(0.34, 1.56, 0.64, 1),
      opacity 350ms ease,
      filter 350ms ease,
      box-shadow 350ms ease,
      border-color 350ms ease,
      background 350ms ease;
  cursor: pointer;
  z-index: 1;
  left: 50%;
  transform-origin: center center;
  margin-left: -160px;
}

/* glow Effect for active card */
.module-card::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  background: linear-gradient(
      135deg,
      rgba(80, 160, 255, 0.4) 0%,
      rgba(120, 80, 255, 0.2) 50%,
      rgba(80, 160, 255, 0.4) 100%
  );
  border-radius: 17px;
  opacity: 0;
  z-index: -1;
  transition: opacity 350ms ease;
  filter: blur(8px);
}

/* Titel */
.module-name {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
  letter-spacing: 0.02em;
  transition: color 350ms ease;
}

/* Preview */
.preview-container {
  background: linear-gradient(135deg, #0a0a0a 0%, #050505 100%);
  border-radius: 12px;
  padding: 12px;
  min-height: 140px;
  max-height: 180px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.03);
  transition: border-color 350ms ease;
}

.preview-placeholder {
  width: 100%;
  height: 140px;
  border-radius: 10px;
  border: 2px dashed rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  opacity: 0.5;
  transition: all 350ms ease;
  letter-spacing: 0.05em;
}

/* active card*/
.module-card.is-active {
  opacity: 1;
  transform: scale(1.2) translateY(-8px);
  filter: none;
  animation: pulseGlow 3s ease-in-out infinite;
  border-color: rgba(80, 160, 255, 0.6);
  background: linear-gradient(145deg, #2d2d2d, #121212);
  z-index: 10;
}

.module-card.is-active::before {
  opacity: 1;
}

.module-card.is-active .module-name {
  color: #90c8ff;
  text-shadow: 0 0 10px rgba(80, 160, 255, 0.5);
}

.module-card.is-active .preview-container {
  border-color: rgba(80, 160, 255, 0.3);
}

.module-card.is-active .preview-placeholder {
  border-color: rgba(80, 160, 255, 0.4);
  opacity: 0.8;
}

/* left card */
.module-card.pos-left {
  transform: translateX(-240px) translateY(25px) scale(0.75) rotateY(10deg);
  transform-origin: right center;
  z-index: 1;
}

/* right card */
.module-card.pos-right {
  transform: translateX(240px) translateY(25px) scale(0.75) rotateY(-10deg);
  transform-origin: left center;
  z-index: 1;
}

/* navigation buttons */
.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: linear-gradient(135deg, rgba(20, 20, 20, 0.95), rgba(10, 10, 10, 0.98));
  color: #d0d0d0;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  width: 44px;
  height: 44px;
  font-size: 30px;
  font-weight: 300;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
  transition:
      background 250ms ease,
      transform 250ms cubic-bezier(0.34, 1.56, 0.64, 1),
      box-shadow 250ms ease,
      border-color 250ms ease,
      color 250ms ease;
  z-index: 20;
}

.nav-btn-left {
  left: 8px;
}

.nav-btn-right {
  right: 8px;
}

.nav-btn:hover {
  background: linear-gradient(135deg, rgba(40, 40, 40, 0.98), rgba(20, 20, 20, 1));
  transform: translateY(-50%) scale(1.1);
  box-shadow:
      0 6px 30px rgba(0, 0, 0, 0.8),
      0 0 30px rgba(80, 160, 255, 0.4);
  border-color: rgba(80, 160, 255, 0.6);
  color: #90c8ff;
}

.nav-btn:active {
  transform: translateY(-50%) scale(0.95);
  box-shadow:
      0 2px 15px rgba(0, 0, 0, 0.9),
      0 0 20px rgba(80, 160, 255, 0.3);
}

/* Cell Selection */
.cell-selection {
  margin-top: 16px;
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.cell-selection p {
  margin-bottom: 10px;
  font-size: 0.95rem;
  letter-spacing: 0.05em;
  color: #b0b0b0;
}

.cell-buttons {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 8px;
}

.cell-btn {
  background: linear-gradient(135deg, #2a2a2a, #1a1a1a);
  color: #d0d0d0;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  width: 36px;
  height: 34px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition:
      background 200ms ease,
      transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1),
      box-shadow 200ms ease,
      border-color 200ms ease,
      color 200ms ease;
}

.cell-btn:hover {
  background: linear-gradient(135deg, #3a3a3a, #2a2a2a);
  transform: translateY(-2px);
  box-shadow:
      0 6px 20px rgba(0, 0, 0, 0.6),
      0 0 15px rgba(80, 160, 255, 0.2);
  border-color: rgba(80, 160, 255, 0.4);
  color: #90c8ff;
}

.cell-btn:active {
  transform: translateY(0px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}

.loading {
  text-align: center;
  color: #888;
  font-size: 0.95rem;
  letter-spacing: 0.05em;
}

/* Responsive Adjustments */
@media (max-width: 640px) {
  .carousel {
    padding-inline: 40px;
  }

  .carousel-track {
    max-width: 100%;
  }

  .module-card {
    flex: 0 0 35%;
  }

  .nav-btn {
    width: 38px;
    height: 38px;
    font-size: 20px;
  }
}
</style>