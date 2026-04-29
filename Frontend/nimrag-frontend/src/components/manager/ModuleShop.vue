<script setup lang="ts">
import { computed, ref } from 'vue'

import { buildDisplayedModules, getModuleItems, moveModuleIndex } from '../../utils/moduleShop'

const props = defineProps<{
  targetLabel: string
  canAdd: boolean
}>()

const emit = defineEmits<{
  addWidget: [payload: { widgetType: string }]
}>()

const moduleList = ref(getModuleItems())
const currentIndex = ref(0)

const displayedModules = computed(() => buildDisplayedModules(moduleList.value, currentIndex.value))

const nextModule = () => {
  currentIndex.value = moveModuleIndex(currentIndex.value, 1, moduleList.value.length)
}

const prevModule = () => {
  currentIndex.value = moveModuleIndex(currentIndex.value, -1, moduleList.value.length)
}

const setCurrentModule = (index: number) => {
  if (!moduleList.value.length) {
    return
  }

  currentIndex.value = index
}

const addCurrentWidget = () => {
  const currentModule = moduleList.value[currentIndex.value]
  if (!currentModule) {
    return
  }

  emit('addWidget', { widgetType: currentModule.type })
}

const handleModuleCardClick = (index: number) => {
  const isActiveCard = index === currentIndex.value
  setCurrentModule(index)

  if (isActiveCard && props.canAdd) {
    addCurrentWidget()
  }
}

defineExpose({
  nextModule,
  prevModule,
  setCurrentModule,
  getCurrentModuleType: () => moduleList.value[currentIndex.value]?.type ?? null,
})
</script>

<template>
  <div class="module-shop">
    <h3 class="title">Widget Shop</h3>

    <div v-if="moduleList.length > 0" class="carousel">
      <button @click="prevModule" class="nav-btn nav-btn-left">‹</button>

      <div class="carousel-track">
        <div
          v-for="item in displayedModules"
          :key="item.index"
          class="module-card"
          :class="[`pos-${item.position}`, { 'is-active': item.index === currentIndex }]"
          @click="handleModuleCardClick(item.index)"
        >
          <h4 class="module-name">{{ item.name }}</h4>

          <div class="preview-container">
            <component v-if="item.position === 'center'" :is="item.component" />
            <div v-else class="preview-placeholder">Vorschau</div>
          </div>
        </div>
      </div>

      <button @click="nextModule" class="nav-btn nav-btn-right">›</button>
    </div>

    <div v-else class="loading">Loading modules...</div>

    <div v-if="moduleList.length > 0" class="target-selection">
      <p class="target-copy">Ziel: {{ props.targetLabel }}</p>
      <button class="confirm-btn" :disabled="!props.canAdd" @click="addCurrentWidget">
        Ausgewaehltes Widget platzieren
      </button>
    </div>
  </div>
</template>

<style scoped>
.module-shop {
  background: radial-gradient(circle at top, #243244 0, #111827 46%, #030712 100%);
  color: #eee;
  padding: 15px 24px 18px;
  border-radius: 16px;
  width: min(900px, 100vw - 48px);
  max-height: 85vh;
  box-sizing: border-box;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.06);
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
}

.carousel {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-inline: 60px;
  margin-bottom: 20px;
  min-height: 280px;
}

.carousel-track {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 320px;
  perspective: 1400px;
}

.module-card {
  position: absolute;
  width: 320px;
  background: linear-gradient(145deg, #203042, #0f172a);
  border-radius: 16px;
  padding: 14px;
  overflow: hidden;
  opacity: 0.8;
  transform: scale(0.8) translateY(25px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: transform 350ms cubic-bezier(0.34, 1.56, 0.64, 1), opacity 350ms ease, box-shadow 350ms ease, border-color 350ms ease;
  cursor: pointer;
  z-index: 1;
  left: 50%;
  margin-left: -160px;
}

.module-card.is-active {
  opacity: 1;
  transform: scale(1.2) translateY(-8px);
  border-color: rgba(56, 189, 248, 0.6);
  z-index: 10;
}

.module-card.pos-left {
  transform: translateX(-240px) translateY(25px) scale(0.75) rotateY(10deg);
}

.module-card.pos-right {
  transform: translateX(240px) translateY(25px) scale(0.75) rotateY(-10deg);
}

.module-name {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 8px;
  text-align: center;
}

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
}

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
  line-height: 1;
  cursor: pointer;
}

.nav-btn-left {
  left: 4px;
}

.nav-btn-right {
  right: 4px;
}

.target-selection {
  margin-top: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.target-copy {
  margin: 0;
  font-size: 0.95rem;
  color: rgba(226, 232, 240, 0.86);
}

.confirm-btn {
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #22c55e, #06b6d4);
  color: #04111f;
  font-weight: 700;
  cursor: pointer;
}

.confirm-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 700px) {
  .module-shop {
    width: min(100vw - 24px, 900px);
    padding: 16px;
  }

  .carousel {
    min-height: 220px;
    padding-inline: 34px;
  }

  .module-card {
    width: min(250px, calc(100vw - 120px));
    margin-left: calc(min(250px, calc(100vw - 120px)) / -2);
  }

  .module-card.pos-left {
    transform: translateX(-130px) translateY(20px) scale(0.72);
  }

  .module-card.pos-right {
    transform: translateX(130px) translateY(20px) scale(0.72);
  }

  .target-selection {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
