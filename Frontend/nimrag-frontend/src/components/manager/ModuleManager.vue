<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { apiClient } from '../../services/api'
import type { SystemConfig, WidgetSettings } from '../../types/config'
import type { ActiveWidgetMap, ModuleShopRef } from '../../types/widgets'
import {
  applyLoadedLayout,
  buildLayoutPayload,
  buildRenderedWidgets,
  formatApiErrorMessage,
  moveWidget,
  upsertWidget,
} from '../../utils/layout'
import GridBoard from './GridBoard.vue'
import ModuleShop from './ModuleShop.vue'

const activeWidgets = ref<ActiveWidgetMap>({})
const configError = ref<string | null>(null)
const isConfigLoading = ref(true)
const isSavingLayout = ref(false)
const isShopOpen = ref(false)
const moduleShopRef = ref<ModuleShopRef>(null)
const systemConfig = ref<SystemConfig | null>(null)
let latestSaveRequest = 0

function updateWidgetSettings(widgetId: string, nextSettingsPatch: WidgetSettings): void {
  const widgetEntry = Object.entries(activeWidgets.value).find(([, widget]) => widget.widget_id === widgetId)
  if (!widgetEntry) {
    return
  }

  const [cellId, widget] = widgetEntry
  activeWidgets.value = {
    ...activeWidgets.value,
    [Number(cellId)]: {
      ...widget,
      settings: {
        ...widget.settings,
        ...nextSettingsPatch,
      },
    },
  }

  void persistLayout()
}

async function loadInitialState(): Promise<void> {
  isConfigLoading.value = true
  configError.value = null

  const failures: string[] = []

  try {
    const layoutEnvelope = await apiClient.getLayout()
    activeWidgets.value = applyLoadedLayout(layoutEnvelope.config)
  } catch (error) {
    failures.push(`Layout konnte nicht geladen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`)
  }

  try {
    const systemEnvelope = await apiClient.getSystemConfig()
    systemConfig.value = systemEnvelope.config
  } catch (error) {
    failures.push(`Systemkonfiguration konnte nicht geladen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`)
  }

  configError.value = failures.length > 0 ? failures.join(' ') : null
  isConfigLoading.value = false
}

async function persistLayout(): Promise<void> {
  latestSaveRequest += 1
  const saveRequestId = latestSaveRequest
  isSavingLayout.value = true

  try {
    const layoutEnvelope = await apiClient.saveLayout(buildLayoutPayload(activeWidgets.value))
    if (saveRequestId === latestSaveRequest) {
      activeWidgets.value = applyLoadedLayout(layoutEnvelope.config)
    }
  } catch (error) {
    configError.value = `Layout konnte nicht gespeichert werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    if (saveRequestId === latestSaveRequest) {
      isSavingLayout.value = false
    }
  }
}

const renderedWidgets = computed(() => {
  return buildRenderedWidgets(activeWidgets.value, systemConfig.value, updateWidgetSettings)
})

const handleAddWidget = ({ cellId, widgetType }: { cellId: number; widgetType: string }) => {
  try {
    activeWidgets.value = upsertWidget(activeWidgets.value, cellId, widgetType)
  } catch (error) {
    configError.value = formatApiErrorMessage(error, `Unbekannter Widget-Typ: ${widgetType}`)
    return
  }

  void persistLayout()
}

const handleMoveWidget = ({ sourceCellId, targetCellId }: { sourceCellId: number; targetCellId: number }) => {
  activeWidgets.value = moveWidget(activeWidgets.value, sourceCellId, targetCellId)

  void persistLayout()
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'e') {
    isShopOpen.value = !isShopOpen.value
  } else if (event.key === 'Escape') {
    isShopOpen.value = false
  } else if (isShopOpen.value && moduleShopRef.value) {
    if (event.key === 'ArrowRight') {
      moduleShopRef.value.nextModule()
    } else if (event.key === 'ArrowLeft') {
      moduleShopRef.value.prevModule()
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  void loadInitialState()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div>
    <div v-if="isConfigLoading || configError || isSavingLayout" class="status-banner">
      <span v-if="isConfigLoading">Konfiguration wird geladen.</span>
      <span v-else-if="isSavingLayout">Layout wird gespeichert.</span>
      <span v-else>{{ configError }}</span>
    </div>

    <div v-if="isShopOpen" class="shop-overlay" @click.self="isShopOpen = false">
      <div class="shop-modal">
        <button class="close-btn" @click="isShopOpen = false">×</button>
        <ModuleShop ref="moduleShopRef" @addWidget="handleAddWidget" />
      </div>
    </div>

    <GridBoard :widgets="renderedWidgets" @moveWidget="handleMoveWidget" />
  </div>
</template>

<style scoped>
.status-banner {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1100;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(17, 24, 39, 0.92);
  color: #f5f5f5;
  font-size: 0.9rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.28);
}

.shop-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.shop-modal {
  position: relative;
  background: #222;
  border-radius: 8px;
  padding: 20px;
  max-width: 80%;
  max-height: 80%;
  overflow: auto;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
}
</style>