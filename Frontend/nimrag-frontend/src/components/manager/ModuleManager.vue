<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { apiClient } from '../../services/api'
import { realtimeClient } from '../../services/realtime'
import type { SystemConfig, WidgetSettings } from '../../types/config'
import type { FocusState, GestureDetectedPayload, UIActionRequestedPayload, UIActionType } from '../../types/interactions'
import type { ActiveWidgetMap, ModuleShopRef } from '../../types/widgets'
import {
  applyLoadedLayout,
  buildLayoutPayload,
  buildRenderedWidgets,
  createFocusState,
  findWidgetAtCell,
  formatApiErrorMessage,
  getDefaultFocus,
  getFocusStateForWidget,
  getWidgetDisplayTitle,
  moveFocus,
  moveWidgetByOffset,
  patchWidgetSettings,
  resizeWidget,
  upsertWidget,
} from '../../utils/layout'
import GridBoard from './GridBoard.vue'
import InteractionOverlay from './InteractionOverlay.vue'
import ModuleShop from './ModuleShop.vue'

const activeWidgets = ref<ActiveWidgetMap>({})
const configError = ref<string | null>(null)
const isConfigLoading = ref(true)
const isSavingLayout = ref(false)
const shopVisible = ref(false)
const focusedState = ref<FocusState>({ row: 1, col: 1, widgetId: null })
const selectedWidgetId = ref<string | null>(null)
const isArrangeMode = ref(false)
const lastRawInput = ref<string | null>(null)
const lastUIAction = ref<UIActionType | null>(null)
const isGestureCoolingDown = ref(false)
const moduleShopRef = ref<ModuleShopRef>(null)
const systemConfig = ref<SystemConfig | null>(null)
let latestSaveRequest = 0
let unsubscribeRealtime: (() => void) | null = null
let gestureCooldownTimer: number | null = null

function setLocalCooldown(): void {
  isGestureCoolingDown.value = true
  if (gestureCooldownTimer !== null) {
    window.clearTimeout(gestureCooldownTimer)
  }
  gestureCooldownTimer = window.setTimeout(() => {
    isGestureCoolingDown.value = false
    gestureCooldownTimer = null
  }, 320)
}

function syncFocus(target?: { row: number; col: number }): void {
  const row = target?.row ?? focusedState.value.row
  const col = target?.col ?? focusedState.value.col
  focusedState.value = createFocusState(row, col, activeWidgets.value)

  if (selectedWidgetId.value && !activeWidgets.value[selectedWidgetId.value]) {
    selectedWidgetId.value = null
    isArrangeMode.value = false
  }
}

function enterArrangeMode(widgetId: string): void {
  const widget = activeWidgets.value[widgetId]
  if (!widget) {
    return
  }

  selectedWidgetId.value = widgetId
  isArrangeMode.value = true
  shopVisible.value = false
  syncFocus({ row: widget.row, col: widget.col })
}

function exitArrangeMode(): void {
  isArrangeMode.value = false
  selectedWidgetId.value = null
}

function updateWidgetSettings(widgetId: string, nextSettingsPatch: WidgetSettings): void {
  activeWidgets.value = patchWidgetSettings(activeWidgets.value, widgetId, nextSettingsPatch)
  void persistLayout()
}

async function loadInitialState(): Promise<void> {
  isConfigLoading.value = true
  configError.value = null

  const failures: string[] = []

  try {
    const layoutEnvelope = await apiClient.getLayout()
    activeWidgets.value = applyLoadedLayout(layoutEnvelope.config)
    focusedState.value = getDefaultFocus(activeWidgets.value)
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
      syncFocus()
    }
  } catch (error) {
    configError.value = `Layout konnte nicht gespeichert werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    if (saveRequestId === latestSaveRequest) {
      isSavingLayout.value = false
    }
  }
}

const renderedWidgets = computed(() => buildRenderedWidgets(activeWidgets.value, systemConfig.value, updateWidgetSettings))

const focusedWidget = computed(() => {
  return focusedState.value.widgetId
    ? activeWidgets.value[focusedState.value.widgetId] ?? null
    : findWidgetAtCell(activeWidgets.value, focusedState.value.row, focusedState.value.col)
})

const selectedWidget = computed(() => {
  return selectedWidgetId.value ? activeWidgets.value[selectedWidgetId.value] ?? null : null
})

const focusedLabel = computed(() => {
  if (focusedWidget.value) {
    return `${getWidgetDisplayTitle(focusedWidget.value)} @ ${focusedWidget.value.row}/${focusedWidget.value.col}`
  }
  return `Zelle ${focusedState.value.row}/${focusedState.value.col}`
})

const nextHint = computed(() => {
  if (isArrangeMode.value) {
    return 'Swipes verschieben das selektierte Widget, Zoom skaliert es, Circle oder Langklick beendet den ArrangeMode.'
  }
  if (shopVisible.value) {
    return 'Mit Enter oder der Klick-Geste wird das aktuell gewaehlte Shop-Widget in die leere Fokuszelle gesetzt.'
  }
  if (focusedWidget.value) {
    return 'Langklick aktiviert den ArrangeMode fuer das fokussierte Widget. Circle oeffnet oder schliesst den Shop.'
  }
  return 'Swipes bewegen den Fokus. Klick oeffnet fuer leere Felder den Shop.'
})

function addFocusedWidget(widgetType: string): void {
  try {
    activeWidgets.value = upsertWidget(activeWidgets.value, focusedState.value, widgetType)
  } catch (error) {
    configError.value = formatApiErrorMessage(error, `Widget konnte nicht platziert werden: ${widgetType}`)
    return
  }

  shopVisible.value = false
  syncFocus()
  void persistLayout()
}

function moveSelectedWidget(rowOffset: number, colOffset: number): void {
  if (!selectedWidgetId.value) {
    return
  }

  const nextWidgets = moveWidgetByOffset(activeWidgets.value, selectedWidgetId.value, rowOffset, colOffset)
  if (nextWidgets === activeWidgets.value) {
    return
  }

  activeWidgets.value = nextWidgets
  syncFocus()
  void persistLayout()
}

function resizeSelectedWidget(mode: 'expand' | 'shrink'): void {
  if (!selectedWidgetId.value) {
    return
  }

  const nextWidgets = resizeWidget(activeWidgets.value, selectedWidgetId.value, mode)
  if (nextWidgets === activeWidgets.value) {
    return
  }

  activeWidgets.value = nextWidgets
  syncFocus()
  void persistLayout()
}

function applyUIAction(action: UIActionType): void {
  lastUIAction.value = action
  setLocalCooldown()

  if (isArrangeMode.value && selectedWidgetId.value) {
    if (action === 'move_focus_left') {
      moveSelectedWidget(0, -1)
      return
    }
    if (action === 'move_focus_right') {
      moveSelectedWidget(0, 1)
      return
    }
    if (action === 'move_focus_up') {
      moveSelectedWidget(-1, 0)
      return
    }
    if (action === 'move_focus_down') {
      moveSelectedWidget(1, 0)
      return
    }
  }

  switch (action) {
    case 'move_focus_left':
      focusedState.value = moveFocus(activeWidgets.value, focusedState.value, 0, -1)
      return
    case 'move_focus_right':
      focusedState.value = moveFocus(activeWidgets.value, focusedState.value, 0, 1)
      return
    case 'move_focus_up':
      focusedState.value = moveFocus(activeWidgets.value, focusedState.value, -1, 0)
      return
    case 'move_focus_down':
      focusedState.value = moveFocus(activeWidgets.value, focusedState.value, 1, 0)
      return
    case 'toggle_shop':
      if (isArrangeMode.value) {
        exitArrangeMode()
      } else {
        shopVisible.value = !shopVisible.value
      }
      return
    case 'primary_click':
      if (shopVisible.value) {
        const widgetType = moduleShopRef.value?.getCurrentModuleType()
        if (widgetType) {
          addFocusedWidget(widgetType)
        }
        return
      }

      if (focusedWidget.value) {
        selectedWidgetId.value = focusedWidget.value.widget_id
        focusedState.value = getFocusStateForWidget(activeWidgets.value, focusedWidget.value.widget_id)
        return
      }

      shopVisible.value = true
      return
    case 'secondary_select':
      if (isArrangeMode.value) {
        exitArrangeMode()
        return
      }
      if (focusedWidget.value) {
        enterArrangeMode(focusedWidget.value.widget_id)
      }
      return
    case 'resize_expand':
      if (isArrangeMode.value) {
        resizeSelectedWidget('expand')
      }
      return
    case 'resize_shrink':
      if (isArrangeMode.value) {
        resizeSelectedWidget('shrink')
      }
      return
    case 'cancel_selection':
      exitArrangeMode()
      shopVisible.value = false
      return
    case 'move_selected_widget':
      return
  }
}

function handleRealtimeEvent(event: { eventType: string; payload: unknown }): void {
  if (event.eventType === 'GestureDetected') {
    const payload = event.payload as GestureDetectedPayload
    lastRawInput.value = payload.gesture
    return
  }

  if (event.eventType === 'UIActionRequested') {
    const payload = event.payload as UIActionRequestedPayload
    lastRawInput.value = payload.raw_input
    applyUIAction(payload.action)
  }
}

function handleFocusCell(payload: { row: number; col: number }): void {
  focusedState.value = createFocusState(payload.row, payload.col, activeWidgets.value)
  if (!isArrangeMode.value) {
    selectedWidgetId.value = focusedState.value.widgetId
  }
}

function handleFocusWidget(payload: { widgetId: string; row: number; col: number }): void {
  selectedWidgetId.value = payload.widgetId
  focusedState.value = createFocusState(payload.row, payload.col, activeWidgets.value)
}

const handleAddWidget = ({ widgetType }: { widgetType: string }) => {
  addFocusedWidget(widgetType)
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === '[' && moduleShopRef.value) {
    moduleShopRef.value.prevModule()
    return
  }

  if (event.key === ']' && moduleShopRef.value) {
    moduleShopRef.value.nextModule()
    return
  }

  const actionByKey: Record<string, UIActionType> = {
    ArrowLeft: 'move_focus_left',
    ArrowRight: 'move_focus_right',
    ArrowUp: 'move_focus_up',
    ArrowDown: 'move_focus_down',
    Enter: 'primary_click',
    ' ': 'secondary_select',
    e: 'toggle_shop',
    Escape: 'cancel_selection',
    '+': 'resize_expand',
    '=': 'resize_expand',
    '-': 'resize_shrink',
    _: 'resize_shrink',
  }

  const action = actionByKey[event.key]
  if (!action) {
    return
  }

  event.preventDefault()
  applyUIAction(action)
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  unsubscribeRealtime = realtimeClient.subscribe(handleRealtimeEvent)
  void loadInitialState()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  unsubscribeRealtime?.()
  if (gestureCooldownTimer !== null) {
    window.clearTimeout(gestureCooldownTimer)
  }
})
</script>

<template>
  <div>
    <div v-if="isConfigLoading || configError || isSavingLayout" class="status-banner">
      <span v-if="isConfigLoading">Konfiguration wird geladen.</span>
      <span v-else-if="isSavingLayout">Layout wird gespeichert.</span>
      <span v-else>{{ configError }}</span>
    </div>

    <div v-if="shopVisible" class="shop-overlay" @click.self="shopVisible = false">
      <div class="shop-modal">
        <button class="close-btn" @click="shopVisible = false">×</button>
        <ModuleShop
          ref="moduleShopRef"
          :target-label="focusedLabel"
          :can-add="!focusedWidget"
          @add-widget="handleAddWidget"
        />
      </div>
    </div>

    <InteractionOverlay
      :last-raw-input="lastRawInput"
      :last-u-i-action="lastUIAction"
      :focused-label="focusedLabel"
      :is-arrange-mode="isArrangeMode"
      :selected-widget-title="selectedWidget ? getWidgetDisplayTitle(selectedWidget) : null"
      :shop-visible="shopVisible"
      :cooldown-active="isGestureCoolingDown"
      :next-hint="nextHint"
    />

    <GridBoard
      :widgets="renderedWidgets"
      :focused-cell="focusedState"
      :selected-widget-id="selectedWidgetId"
      :is-arrange-mode="isArrangeMode"
      @focus-cell="handleFocusCell"
      @focus-widget="handleFocusWidget"
    />
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
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.shop-modal {
  position: relative;
  background: rgba(3, 7, 18, 0.94);
  border-radius: 20px;
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
