<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Component, ComponentPublicInstance } from 'vue'

import { apiClient, ApiError } from '../../services/api'
import type { LayoutConfig, SystemConfig, WidgetConfig } from '../../types/config'
import { getWidgetDefinition } from '../../widgets/registry'
import GridBoard from './GridBoard.vue'
import ModuleShop from './ModuleShop.vue'

interface ModuleShopExposed {
  nextModule: () => void
  prevModule: () => void
}

type ActiveWidgetMap = Record<number, WidgetConfig>

const activeWidgets = ref<ActiveWidgetMap>({})
const configError = ref<string | null>(null)
const isConfigLoading = ref(true)
const isSavingLayout = ref(false)
const isShopOpen = ref(false)
const moduleShopRef = ref<ComponentPublicInstance<{}, ModuleShopExposed> | null>(null)
const systemConfig = ref<SystemConfig | null>(null)
let latestSaveRequest = 0

function formatErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return fallback
}

function normalizeWidget(widget: WidgetConfig): WidgetConfig | null {
  if (widget.cell_id < 1 || widget.cell_id > 16) {
    return null
  }

  return {
    ...widget,
    title: widget.title ?? getWidgetDefinition(widget.widget_type)?.defaultTitle ?? null,
    settings: widget.settings ?? {},
  }
}

function applyLoadedLayout(layout: LayoutConfig): void {
  const nextWidgets: ActiveWidgetMap = {}
  layout.widgets.forEach((widget) => {
    const normalizedWidget = normalizeWidget(widget)
    if (!normalizedWidget) {
      return
    }
    nextWidgets[normalizedWidget.cell_id] = normalizedWidget
  })
  activeWidgets.value = nextWidgets
}

function buildLayoutPayload(): LayoutConfig {
  const widgets = Object.values(activeWidgets.value).sort((left, right) => left.cell_id - right.cell_id)
  return {
    version: 1,
    widgets,
    updated_at: null,
  }
}

async function loadInitialState(): Promise<void> {
  isConfigLoading.value = true
  configError.value = null

  const failures: string[] = []

  try {
    const layoutEnvelope = await apiClient.getLayout()
    applyLoadedLayout(layoutEnvelope.config)
  } catch (error) {
    failures.push(`Layout konnte nicht geladen werden: ${formatErrorMessage(error, 'Unbekannter Fehler')}`)
  }

  try {
    const systemEnvelope = await apiClient.getSystemConfig()
    systemConfig.value = systemEnvelope.config
  } catch (error) {
    failures.push(`Systemkonfiguration konnte nicht geladen werden: ${formatErrorMessage(error, 'Unbekannter Fehler')}`)
  }

  configError.value = failures.length > 0 ? failures.join(' ') : null
  isConfigLoading.value = false
}

async function persistLayout(): Promise<void> {
  latestSaveRequest += 1
  const saveRequestId = latestSaveRequest
  isSavingLayout.value = true

  try {
    const layoutEnvelope = await apiClient.saveLayout(buildLayoutPayload())
    if (saveRequestId === latestSaveRequest) {
      applyLoadedLayout(layoutEnvelope.config)
    }
  } catch (error) {
    configError.value = `Layout konnte nicht gespeichert werden: ${formatErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    if (saveRequestId === latestSaveRequest) {
      isSavingLayout.value = false
    }
  }
}

const renderedWidgets = computed(() => {
  return Object.fromEntries(
    Object.values(activeWidgets.value).map((widget) => {
      const widgetDefinition = getWidgetDefinition(widget.widget_type)
      return [
        widget.cell_id,
        {
          ...widget,
          component: widgetDefinition?.component ?? null,
          widgetProps: widget.widget_type === 'weather'
            ? { initialSystemConfig: systemConfig.value }
            : undefined,
        },
      ]
    }),
  ) as Record<number, {
    component: Component | null
    widgetProps?: { initialSystemConfig?: SystemConfig | null }
  } & WidgetConfig>
})

const handleAddWidget = ({ cellId, widgetType }: { cellId: number; widgetType: string }) => {
  const widgetDefinition = getWidgetDefinition(widgetType)
  if (!widgetDefinition) {
    configError.value = `Unbekannter Widget-Typ: ${widgetType}`
    return
  }

  const existingWidget = activeWidgets.value[cellId]
  activeWidgets.value = {
    ...activeWidgets.value,
    [cellId]: {
      widget_id: existingWidget?.widget_id ?? `${widgetType}-${cellId}-${Date.now()}`,
      widget_type: widgetType,
      cell_id: cellId,
      title: widgetDefinition.defaultTitle,
      settings: existingWidget?.settings ?? {},
    },
  }

  void persistLayout()
}

const handleMoveWidget = ({ sourceCellId, targetCellId }: { sourceCellId: number; targetCellId: number }) => {
  const sourceWidget = activeWidgets.value[sourceCellId]
  if (!sourceWidget) {
    return
  }

  const targetWidget = activeWidgets.value[targetCellId]
  const nextWidgets: ActiveWidgetMap = { ...activeWidgets.value }

  if (targetWidget) {
    nextWidgets[sourceCellId] = { ...targetWidget, cell_id: sourceCellId }
  } else {
    delete nextWidgets[sourceCellId]
  }

  nextWidgets[targetCellId] = { ...sourceWidget, cell_id: targetCellId }
  activeWidgets.value = nextWidgets

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