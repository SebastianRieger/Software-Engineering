<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { apiClient } from '../../services/api'
import { realtimeClient } from '../../services/realtime'
import type {
  CalibrationDefinitionsResponse,
  CalibrationRealtimeEvent,
  CalibrationSessionCreateRequest,
  CalibrationSessionRecord,
} from '../../types/calibration'
import type {
  CommandProfilesConfig,
  MusicalAudioConfig,
  MusicalAudioTrainingArtifact,
} from '../../types/commands'
import type { SystemConfig, WidgetSettings } from '../../types/config'
import type {
  GestureCameraDevice,
  GestureStatusResponse,
  MusicalAudioInputDevice,
  MusicalAudioStatusResponse,
  VoiceInputDevice,
} from '../../types/hardware'
import type {
  CommandMatchEvaluatedPayload,
  FocusState,
  UIActionRequestedPayload,
  UIActionType,
} from '../../types/interactions'
import type { RealtimeEvent } from '../../types/realtime'
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
  patchWidgetSettings,
  removeWidget,
  resizeWidget,
  upsertWidget,
} from '../../utils/layout'
import {
  getModuleItems,
} from '../../utils/moduleShop'
import {
  reduceInteractionState,
  type InteractionReducerEffect,
  type InteractionState,
} from '../../utils/interactionReducer'
import GridBoard from './GridBoard.vue'
import CalibrationWizard from './CalibrationWizard.vue'
import CommandSettingsPanel from './CommandSettingsPanel.vue'
import InteractionOverlay from './InteractionOverlay.vue'
import ModuleShop from './ModuleShop.vue'

type CalibrationPreviewState = 'warming_up' | 'live' | 'stale' | 'unavailable' | 'error'

const activeWidgets = ref<ActiveWidgetMap>({})
const configError = ref<string | null>(null)
const isConfigLoading = ref(true)
const isSavingLayout = ref(false)
const shopVisible = ref(false)
const focusedState = ref<FocusState>({ row: 1, col: 1, widgetId: null })
const selectedWidgetId = ref<string | null>(null)
const isArrangeMode = ref(false)
const lastRawInput = ref<string | null>(null)
const lastCommandMatch = ref<string | null>(null)
const lastUIAction = ref<UIActionType | null>(null)
const isGestureCoolingDown = ref(false)
const moduleShopRef = ref<ModuleShopRef>(null)
const systemConfig = ref<SystemConfig | null>(null)
const calibrationDefinitions = ref<CalibrationDefinitionsResponse | null>(null)
const calibrationSession = ref<CalibrationSessionRecord | null>(null)
const calibrationError = ref<string | null>(null)
const calibrationEventMessage = ref<string | null>(null)
const calibrationProfileName = ref('default')
const calibrationGestureDevices = ref<GestureCameraDevice[]>([])
const calibrationGestureStatus = ref<GestureStatusResponse | null>(null)
const calibrationCameraIndex = ref(0)
const calibrationSelectedTargets = ref<string[]>([])
const calibrationTargetRepetitions = ref(12)
const calibrationPreviewImage = ref<string | null>(null)
const calibrationPreviewState = ref<CalibrationPreviewState>('warming_up')
const calibrationPreviewMessage = ref<string | null>(null)
const calibrationCountdownSeconds = ref<number | null>(null)
const isCalibrationMode = ref(false)
const isCalibrationLoading = ref(false)
const isCalibrationBusy = ref(false)
const isCommandSettingsMode = ref(false)
const isCommandSettingsLoading = ref(false)
const isCommandSettingsSaving = ref(false)
const commandSettingsError = ref<string | null>(null)
const commandProfilesConfig = ref<CommandProfilesConfig | null>(null)
const commandGestureDevices = ref<GestureCameraDevice[]>([])
const commandVoiceDevices = ref<VoiceInputDevice[]>([])
const commandMusicalAudioDevices = ref<MusicalAudioInputDevice[]>([])
const musicalAudioStatus = ref<MusicalAudioStatusResponse | null>(null)
const musicalAudioConfig = ref<MusicalAudioConfig | null>(null)
const musicalAudioArtifacts = ref<MusicalAudioTrainingArtifact[]>([])
let latestSaveRequest = 0
let unsubscribeRealtime: (() => void) | null = null
let gestureCooldownTimer: number | null = null
let initialLoadRetryTimer: number | null = null
let calibrationPreviewTimer: number | null = null
let calibrationCountdownTimer: number | null = null
let calibrationPreviewRequestInFlight = false
let calibrationLastPreviewSuccessAt: number | null = null
let calibrationAutoStartTakeId: string | null = null
let calibrationAutoStartLastAttemptAt: number | null = null

const calibrationEventTypes = new Set([
  'CalibrationSessionStarted',
  'CalibrationTargetArmed',
  'CalibrationTakePrepared',
  'CalibrationRecordingStarted',
  'CalibrationRecordingStopped',
  'CalibrationTakeAccepted',
  'CalibrationTakeDiscarded',
  'CalibrationSampleAccepted',
  'CalibrationSampleRejected',
  'CalibrationTargetCompleted',
  'CalibrationAnalysisReady',
  'CalibrationProfileApplied',
  'CalibrationProfileRolledBack',
])

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

function exitArrangeMode(): void {
  isArrangeMode.value = false
  selectedWidgetId.value = null
}

function updateWidgetSettings(widgetId: string, nextSettingsPatch: WidgetSettings): void {
  activeWidgets.value = patchWidgetSettings(activeWidgets.value, widgetId, nextSettingsPatch)
  void persistLayout()
}

async function loadInitialState(): Promise<void> {
  if (initialLoadRetryTimer !== null) {
    window.clearTimeout(initialLoadRetryTimer)
    initialLoadRetryTimer = null
  }

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

  if (failures.length > 0) {
    initialLoadRetryTimer = window.setTimeout(() => {
      initialLoadRetryTimer = null
      void loadInitialState()
    }, 1500)
  }
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
    return 'Swipes verschieben das selektierte Widget, Zoom skaliert es. Die Kartenbuttons vergroessern, verkleinern oder entfernen Widgets direkt.'
  }
  if (shopVisible.value) {
    return 'Mit Enter oder der Klick-Geste wird das aktuell gewaehlte Shop-Widget in die leere Fokuszelle gesetzt.'
  }
  if (focusedWidget.value) {
    return 'Langklick aktiviert den ArrangeMode fuer das fokussierte Widget. Die Kartenbuttons skalieren oder entfernen das Widget, Circle oeffnet oder schliesst den Shop.'
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

function getInteractionState(): InteractionState {
  return {
    activeWidgets: activeWidgets.value,
    focusedState: focusedState.value,
    selectedWidgetId: selectedWidgetId.value,
    isArrangeMode: isArrangeMode.value,
    shopVisible: shopVisible.value,
    isCalibrationMode: isCalibrationMode.value,
  }
}

function applyInteractionState(nextState: InteractionState): void {
  activeWidgets.value = nextState.activeWidgets
  focusedState.value = nextState.focusedState
  selectedWidgetId.value = nextState.selectedWidgetId
  isArrangeMode.value = nextState.isArrangeMode
  shopVisible.value = nextState.shopVisible
}

function applyInteractionEffects(effects: InteractionReducerEffect[]): void {
  effects.forEach((effect) => {
    if (effect.type === 'persist-layout') {
      void persistLayout()
      return
    }

    if (effect.type === 'shop-select-widget-type') {
      if (!moduleShopRef.value) {
        return
      }

      const targetIndex = getModuleItems().findIndex((item) => item.type === effect.widgetType)
      if (targetIndex >= 0) {
        moduleShopRef.value.setCurrentModule(targetIndex)
      }
      return
    }

    if (!moduleShopRef.value) {
      return
    }

    if (effect.direction === 'prev') {
      moduleShopRef.value.prevModule()
      return
    }

    moduleShopRef.value.nextModule()
  })
}

function dispatchUIActionPayload(payload: UIActionRequestedPayload): void {
  lastRawInput.value = payload.raw_input
  lastUIAction.value = payload.action
  setLocalCooldown()

  const result = reduceInteractionState(getInteractionState(), payload.action, {
    shopCurrentWidgetType: moduleShopRef.value?.getCurrentModuleType() ?? null,
  }, payload.action_args)

  applyInteractionState(result.state)
  if (result.error) {
    configError.value = result.error
  }
  applyInteractionEffects(result.effects)
}

function formatCommandMatch(payload: CommandMatchEvaluatedPayload): string {
  const source = payload.input_source.replace('_', ' ')
  if (payload.outcome === 'accepted') {
    return `${source}: ${payload.action ?? payload.raw_input}`
  }

  const reason = payload.reason ? ` (${payload.reason})` : ''
  return `${source}: ${payload.outcome}${reason}`
}

async function ensureCalibrationDefinitions(): Promise<void> {
  if (calibrationDefinitions.value) {
    return
  }

  isCalibrationLoading.value = true
  calibrationError.value = null
  try {
    const definitions = await apiClient.getCalibrationDefinitions()
    calibrationDefinitions.value = definitions
    if (calibrationSelectedTargets.value.length === 0) {
      calibrationSelectedTargets.value = definitions.targets
        .filter((target) => target.modality === 'gesture' && target.supported)
        .slice(0, 1)
        .map((target) => target.id)
    }
  } catch (error) {
    calibrationError.value = `Kalibrierungsziele konnten nicht geladen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationLoading.value = false
  }
}

function stopCalibrationPreviewLoop(): void {
  if (calibrationPreviewTimer !== null) {
    window.clearInterval(calibrationPreviewTimer)
    calibrationPreviewTimer = null
  }
}

function stopCalibrationCountdownLoop(): void {
  if (calibrationCountdownTimer !== null) {
    window.clearInterval(calibrationCountdownTimer)
    calibrationCountdownTimer = null
  }
  calibrationCountdownSeconds.value = null
  calibrationAutoStartTakeId = null
  calibrationAutoStartLastAttemptAt = null
}

function hasLiveCalibrationPreview(): boolean {
  return calibrationPreviewState.value === 'live' && calibrationGestureStatus.value?.running === true
}

function normalizeCalibrationPreviewImage(image: string): string {
  return image.startsWith('data:') ? image : `data:image/jpeg;base64,${image}`
}

async function refreshCalibrationPreview(): Promise<void> {
  if (!isCalibrationMode.value || calibrationPreviewRequestInFlight) {
    return
  }

  calibrationPreviewRequestInFlight = true
  try {
    const gestureStatus = await apiClient.getGestureStatus()
    calibrationGestureStatus.value = gestureStatus

    if (!gestureStatus.available || !gestureStatus.running) {
      calibrationPreviewImage.value = null
      calibrationPreviewState.value = 'unavailable'
      calibrationPreviewMessage.value = gestureStatus.last_error ?? 'Gestenerkennung laeuft nicht.'
      return
    }

    try {
      const frame = await apiClient.getGestureFrame()
      calibrationPreviewImage.value = normalizeCalibrationPreviewImage(frame.image)
      calibrationLastPreviewSuccessAt = Date.now()
      const frameAgeMs = frame.frame_age_ms ?? 0
      if (frameAgeMs > 1800) {
        calibrationPreviewState.value = 'stale'
        calibrationPreviewMessage.value = 'Vorschau ist veraltet. Warte auf einen frischen Kameraframe.'
      } else {
        calibrationPreviewState.value = 'live'
        calibrationPreviewMessage.value = null
      }
    } catch (error) {
      calibrationPreviewImage.value = null
      if (calibrationLastPreviewSuccessAt !== null && Date.now() - calibrationLastPreviewSuccessAt < 2500) {
        calibrationPreviewState.value = 'stale'
        calibrationPreviewMessage.value = 'Vorschau aktualisiert sich nicht mehr.'
      } else {
        calibrationPreviewState.value = 'warming_up'
        calibrationPreviewMessage.value = formatApiErrorMessage(error, 'Vorschau waermt noch auf.')
      }
    }
  } catch (error) {
    calibrationPreviewState.value = 'error'
    calibrationPreviewMessage.value = `Preview konnte nicht geladen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    calibrationPreviewRequestInFlight = false
  }
}

function getCalibrationPreparedTake(): CalibrationSessionRecord['active_take'] {
  const activeTake = calibrationSession.value?.active_take
  if (!activeTake || activeTake.status !== 'prepared') {
    return null
  }
  return activeTake
}

function scheduleCalibrationPreviewLoop(): void {
  stopCalibrationPreviewLoop()
  if (!isCalibrationMode.value) {
    return
  }

  const activeTakeStatus = calibrationSession.value?.active_take?.status
  const intervalMs = activeTakeStatus === 'prepared' || activeTakeStatus === 'recording' ? 333 : 1000
  void refreshCalibrationPreview()
  calibrationPreviewTimer = window.setInterval(() => {
    void refreshCalibrationPreview()
  }, intervalMs)
}

function syncCalibrationCountdown(): void {
  stopCalibrationCountdownLoop()

  const activeTake = getCalibrationPreparedTake()
  if (!isCalibrationMode.value || !activeTake || !activeTake.ready_at) {
    return
  }

  const readyAtMs = Date.parse(activeTake.ready_at)
  const takeId = activeTake.take_id
  const update = () => {
    if (calibrationSession.value?.active_take?.take_id !== takeId || calibrationSession.value?.active_take?.status !== 'prepared') {
      stopCalibrationCountdownLoop()
      return
    }

    const remainingMs = readyAtMs - Date.now()
    calibrationCountdownSeconds.value = Math.max(0, Math.ceil(remainingMs / 1000))
    if (remainingMs <= 0) {
      calibrationCountdownSeconds.value = 0
      if (!hasLiveCalibrationPreview() || isCalibrationBusy.value) {
        return
      }

      const now = Date.now()
      if (calibrationAutoStartTakeId === takeId && calibrationAutoStartLastAttemptAt !== null && now - calibrationAutoStartLastAttemptAt < 1000) {
        return
      }

      calibrationAutoStartTakeId = takeId
      calibrationAutoStartLastAttemptAt = now
      void startCalibrationTake()
    }
  }

  update()
  calibrationCountdownTimer = window.setInterval(update, 200)
}

async function openCalibrationWizard(): Promise<void> {
  isCommandSettingsMode.value = false
  shopVisible.value = false
  exitArrangeMode()
  selectedWidgetId.value = null
  calibrationEventMessage.value = null
  calibrationError.value = null
  isCalibrationMode.value = true
  await Promise.all([ensureCalibrationDefinitions(), loadCalibrationCameraContext()])
  scheduleCalibrationPreviewLoop()
  syncCalibrationCountdown()
}

function closeCalibrationWizard(): void {
  stopCalibrationPreviewLoop()
  stopCalibrationCountdownLoop()
  isCalibrationMode.value = false
  calibrationEventMessage.value = null
  calibrationError.value = null
  calibrationSession.value = null
  calibrationPreviewImage.value = null
  calibrationPreviewMessage.value = null
  calibrationPreviewState.value = 'warming_up'
}

async function loadCommandSettings(): Promise<void> {
  isCommandSettingsLoading.value = true
  commandSettingsError.value = null

  try {
    const [
      commandProfilesEnvelope,
      musicalAudioEnvelope,
      gestureDeviceList,
      voiceDeviceList,
      musicalAudioDeviceList,
      musicalAudioRuntimeStatus,
      musicalAudioArtifactList,
    ] = await Promise.all([
      apiClient.getCommandProfilesConfig(),
      apiClient.getMusicalAudioConfig(),
      apiClient.getGestureDevices(),
      apiClient.getVoiceDevices(),
      apiClient.getMusicalAudioDevices(),
      apiClient.getMusicalAudioStatus(),
      apiClient.listMusicalAudioArtifacts(),
    ])

    commandProfilesConfig.value = commandProfilesEnvelope.config
    musicalAudioConfig.value = musicalAudioEnvelope.config
    commandGestureDevices.value = gestureDeviceList.devices
    commandVoiceDevices.value = voiceDeviceList.devices
    commandMusicalAudioDevices.value = musicalAudioDeviceList.devices
    musicalAudioStatus.value = musicalAudioRuntimeStatus
    musicalAudioArtifacts.value = musicalAudioArtifactList.artifacts
  } catch (error) {
    commandSettingsError.value = `Command Settings konnten nicht geladen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCommandSettingsLoading.value = false
  }
}

async function openCommandSettings(): Promise<void> {
  isCalibrationMode.value = false
  shopVisible.value = false
  exitArrangeMode()
  selectedWidgetId.value = null
  isCommandSettingsMode.value = true
  await loadCommandSettings()
}

async function refreshMusicalAudioSurface(profileId = commandProfilesConfig.value?.active_profile_id ?? 'default'): Promise<void> {
  const [musicalAudioEnvelope, musicalAudioRuntimeStatus, musicalAudioArtifactList] = await Promise.all([
    apiClient.getMusicalAudioConfig(),
    apiClient.getMusicalAudioStatus(),
    apiClient.listMusicalAudioArtifacts(profileId),
  ])

  musicalAudioConfig.value = musicalAudioEnvelope.config
  musicalAudioStatus.value = musicalAudioRuntimeStatus
  musicalAudioArtifacts.value = musicalAudioArtifactList.artifacts
}

function closeCommandSettings(): void {
  isCommandSettingsMode.value = false
}

async function saveCommandProfiles(nextConfig: CommandProfilesConfig): Promise<void> {
  isCommandSettingsSaving.value = true
  commandSettingsError.value = null
  try {
    const response = await apiClient.saveCommandProfilesConfig(nextConfig)
    commandProfilesConfig.value = response.config
    await refreshMusicalAudioSurface(response.config.active_profile_id)
  } catch (error) {
    commandSettingsError.value = `Command-Profil konnte nicht gespeichert werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCommandSettingsSaving.value = false
  }
}

async function saveMusicalAudioConfigDraft(nextConfig: MusicalAudioConfig): Promise<void> {
  isCommandSettingsSaving.value = true
  commandSettingsError.value = null
  try {
    const response = await apiClient.saveMusicalAudioConfig(nextConfig)
    musicalAudioConfig.value = response.config
    const commandProfilesEnvelope = await apiClient.getCommandProfilesConfig()
    commandProfilesConfig.value = commandProfilesEnvelope.config
    await refreshMusicalAudioSurface(commandProfilesEnvelope.config.active_profile_id)
  } catch (error) {
    commandSettingsError.value = `Musical-Audio-Config konnte nicht gespeichert werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCommandSettingsSaving.value = false
  }
}

async function saveMusicalAudioArtifact(artifact: MusicalAudioTrainingArtifact): Promise<void> {
  isCommandSettingsSaving.value = true
  commandSettingsError.value = null
  try {
    await apiClient.saveMusicalAudioArtifact(artifact)
    await refreshMusicalAudioSurface(artifact.profile_id)
  } catch (error) {
    commandSettingsError.value = `Musical-Audio-Artefakt konnte nicht gespeichert werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCommandSettingsSaving.value = false
  }
}

async function deleteMusicalAudioArtifact(payload: { artifactId: string; profileId: string }): Promise<void> {
  isCommandSettingsSaving.value = true
  commandSettingsError.value = null
  try {
    await apiClient.deleteMusicalAudioArtifact(payload.artifactId, payload.profileId)
    await refreshMusicalAudioSurface(payload.profileId)
  } catch (error) {
    commandSettingsError.value = `Musical-Audio-Artefakt konnte nicht geloescht werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCommandSettingsSaving.value = false
  }
}

async function startMusicalAudioRuntime(deviceIndex: number): Promise<void> {
  commandSettingsError.value = null
  try {
    musicalAudioStatus.value = await apiClient.startMusicalAudio(deviceIndex)
  } catch (error) {
    commandSettingsError.value = `Musical-Audio-Runtime konnte nicht gestartet werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  }
}

async function stopMusicalAudioRuntime(): Promise<void> {
  commandSettingsError.value = null
  try {
    musicalAudioStatus.value = await apiClient.stopMusicalAudio()
  } catch (error) {
    commandSettingsError.value = `Musical-Audio-Runtime konnte nicht gestoppt werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  }
}

async function refreshCalibrationSession(sessionId: string): Promise<void> {
  try {
    const response = await apiClient.getCalibrationSession(sessionId)
    calibrationSession.value = response.session
  } catch (error) {
    calibrationError.value = `Kalibrierungssitzung konnte nicht aktualisiert werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  }
}

async function startCalibrationSession(): Promise<void> {
  if (!hasLiveCalibrationPreview()) {
    calibrationError.value = 'Kalibrierung startet erst mit frischer Live-Vorschau und laufender Gestenerkennung.'
    return
  }

  calibrationError.value = null
  calibrationEventMessage.value = null
  isCalibrationBusy.value = true

  const payload: CalibrationSessionCreateRequest = {
    modality: 'gesture',
    selected_targets: calibrationSelectedTargets.value.slice(),
    target_repetitions: calibrationTargetRepetitions.value,
    profile: calibrationProfileName.value.trim() || 'default',
    camera_index: calibrationCameraIndex.value,
  }

  try {
    const response = await apiClient.startCalibrationSession(payload)
    calibrationSession.value = response.session
    const preparedTake = await apiClient.prepareCalibrationTake(response.session.session_id)
    calibrationSession.value = preparedTake.session
  } catch (error) {
    calibrationError.value = `Kalibrierung konnte nicht gestartet werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function loadCalibrationCameraContext(): Promise<void> {
  calibrationError.value = null

  try {
    const gestureStatus = await apiClient.getGestureStatus()
    calibrationGestureStatus.value = gestureStatus

    if (gestureStatus.camera_index !== null) {
      calibrationCameraIndex.value = gestureStatus.camera_index
    }

    try {
      const gestureDeviceList = await apiClient.getGestureDevices()
      calibrationGestureDevices.value = gestureDeviceList.devices
      if (gestureStatus.camera_index === null) {
        const firstAvailableDevice = gestureDeviceList.devices.find((device) => device.available)
        if (firstAvailableDevice) {
          calibrationCameraIndex.value = firstAvailableDevice.index
        }
      }
    } catch (error) {
      calibrationGestureDevices.value = gestureStatus.camera_index !== null
        ? [{ index: gestureStatus.camera_index, name: gestureStatus.camera_name ?? `Camera ${gestureStatus.camera_index}`, available: true, backend: null }]
        : []
      calibrationError.value = `Kameraliste konnte nicht vollstaendig geladen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
    }

    if (gestureStatus.available && !gestureStatus.running) {
      try {
        calibrationGestureStatus.value = await apiClient.startGestures(calibrationCameraIndex.value)
      } catch (error) {
        calibrationPreviewImage.value = null
        calibrationPreviewState.value = 'error'
        calibrationPreviewMessage.value = formatApiErrorMessage(error, 'Gestenerkennung konnte nicht gestartet werden.')
        calibrationError.value = `Gestenerkennung konnte nicht gestartet werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
        return
      }
    }

    await refreshCalibrationPreview()
  } catch (error) {
    calibrationGestureDevices.value = calibrationGestureDevices.value.length > 0 ? calibrationGestureDevices.value : []
    calibrationError.value = `Kalibrierungs-Kamerakontext konnte nicht geladen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
    calibrationPreviewState.value = 'error'
  }
}

async function prepareCalibrationTake(): Promise<void> {
  if (!calibrationSession.value) {
    return
  }
  if (!hasLiveCalibrationPreview()) {
    calibrationError.value = 'Ein neuer Take wird blockiert, bis die Vorschau live und frisch ist.'
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.prepareCalibrationTake(calibrationSession.value.session_id)
    calibrationSession.value = response.session
  } catch (error) {
    calibrationError.value = `Take konnte nicht vorbereitet werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function startCalibrationTake(): Promise<void> {
  const preparedTake = getCalibrationPreparedTake()
  if (!calibrationSession.value || !preparedTake) {
    return
  }
  if (!hasLiveCalibrationPreview()) {
    calibrationError.value = 'Recording startet erst mit frischer Live-Vorschau.'
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.startCalibrationTake(calibrationSession.value.session_id)
    calibrationSession.value = response.session
    calibrationAutoStartTakeId = null
    calibrationAutoStartLastAttemptAt = null
  } catch (error) {
    calibrationError.value = `Recording konnte nicht gestartet werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function stopCalibrationTake(): Promise<void> {
  if (!calibrationSession.value) {
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.stopCalibrationTake(calibrationSession.value.session_id)
    calibrationSession.value = response.session
  } catch (error) {
    calibrationError.value = `Recording konnte nicht gestoppt werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

function sessionHasIncompleteTargets(): boolean {
  return calibrationSession.value?.progress.some((entry) => !entry.completed) ?? false
}

async function acceptCalibrationTake(): Promise<void> {
  if (!calibrationSession.value) {
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.acceptCalibrationTake(calibrationSession.value.session_id)
    calibrationSession.value = response.session
    if (response.session.status === 'collecting' && sessionHasIncompleteTargets()) {
      const preparedTake = await apiClient.prepareCalibrationTake(response.session.session_id)
      calibrationSession.value = preparedTake.session
    }
  } catch (error) {
    calibrationError.value = `Take konnte nicht akzeptiert werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function discardCalibrationTake(): Promise<void> {
  if (!calibrationSession.value) {
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.discardCalibrationTake(calibrationSession.value.session_id)
    calibrationSession.value = response.session
    if (response.session.status === 'collecting' && sessionHasIncompleteTargets()) {
      const preparedTake = await apiClient.prepareCalibrationTake(response.session.session_id)
      calibrationSession.value = preparedTake.session
    }
  } catch (error) {
    calibrationError.value = `Take konnte nicht verworfen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function completeCalibrationSession(): Promise<void> {
  if (!calibrationSession.value) {
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.completeCalibrationSession(calibrationSession.value.session_id)
    calibrationSession.value = response.session
  } catch (error) {
    calibrationError.value = `Analyse konnte nicht erzeugt werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function applyCalibrationSession(): Promise<void> {
  if (!calibrationSession.value) {
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.applyCalibrationSession(calibrationSession.value.session_id)
    calibrationSession.value = response.session
    calibrationEventMessage.value = `Profil ${response.applied_profile.profile} wurde angewendet.`
  } catch (error) {
    calibrationError.value = `Profil konnte nicht angewendet werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function rollbackCalibrationSession(): Promise<void> {
  if (!calibrationSession.value) {
    return
  }

  isCalibrationBusy.value = true
  calibrationError.value = null
  try {
    const response = await apiClient.rollbackCalibrationSession(calibrationSession.value.session_id)
    calibrationSession.value = response.session
    calibrationEventMessage.value = 'Das zuvor angewendete Profil wurde zurueckgesetzt.'
  } catch (error) {
    calibrationError.value = `Rollback konnte nicht ausgefuehrt werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
  } finally {
    isCalibrationBusy.value = false
  }
}

async function discardCalibrationSession(): Promise<void> {
  if (!calibrationSession.value) {
    closeCalibrationWizard()
    return
  }

  const sessionStatus = calibrationSession.value.status
  if (sessionStatus === 'collecting' || sessionStatus === 'analysis_ready') {
    isCalibrationBusy.value = true
    calibrationError.value = null
    try {
      const response = await apiClient.cancelCalibrationSession(calibrationSession.value.session_id)
      calibrationSession.value = response.session
    } catch (error) {
      calibrationError.value = `Kalibrierung konnte nicht verworfen werden: ${formatApiErrorMessage(error, 'Unbekannter Fehler')}`
      isCalibrationBusy.value = false
      return
    }
    isCalibrationBusy.value = false
  }

  closeCalibrationWizard()
}

function handleRealtimeEvent(event: RealtimeEvent): void {
  if (calibrationEventTypes.has(event.eventType)) {
    const payload = event.payload as CalibrationRealtimeEvent['payload']
    if (calibrationSession.value && payload.session_id !== calibrationSession.value.session_id) {
      return
    }

    calibrationEventMessage.value = payload.message
    if (calibrationSession.value) {
      void refreshCalibrationSession(calibrationSession.value.session_id)
    }
    return
  }

  if (isCalibrationMode.value) {
    return
  }

  if (event.eventType === 'RawInputDetected') {
    lastRawInput.value = event.payload.raw_input
    return
  }

  if (event.eventType === 'CommandMatchEvaluated') {
    lastRawInput.value = event.payload.raw_input
    lastCommandMatch.value = formatCommandMatch(event.payload)
    return
  }

  if (event.eventType === 'GestureDetected') {
    lastRawInput.value = event.payload.gesture
    return
  }

  if (event.eventType === 'VoiceCommandDetected') {
    lastRawInput.value = event.payload.raw_input
    return
  }

  if (event.eventType === 'UIActionRequested') {
    dispatchUIActionPayload(event.payload)
  }
}

function handleFocusCell(payload: { row: number; col: number }): void {
  if (isCalibrationMode.value) {
    return
  }

  if (isCommandSettingsMode.value) {
    return
  }

  focusedState.value = createFocusState(payload.row, payload.col, activeWidgets.value)
  if (!isArrangeMode.value) {
    selectedWidgetId.value = focusedState.value.widgetId
  }
}

function handleFocusWidget(payload: { widgetId: string; row: number; col: number }): void {
  if (isCalibrationMode.value) {
    return
  }

  if (isCommandSettingsMode.value) {
    return
  }

  selectedWidgetId.value = payload.widgetId
  focusedState.value = createFocusState(payload.row, payload.col, activeWidgets.value)
}

function handleResizeWidget(payload: { widgetId: string; mode: 'expand' | 'shrink' }): void {
  if (isCalibrationMode.value || isCommandSettingsMode.value) {
    return
  }

  const nextWidgets = resizeWidget(activeWidgets.value, payload.widgetId, payload.mode)
  if (nextWidgets === activeWidgets.value) {
    return
  }

  activeWidgets.value = nextWidgets
  selectedWidgetId.value = payload.widgetId
  focusedState.value = getFocusStateForWidget(activeWidgets.value, payload.widgetId)
  void persistLayout()
}

function handleDeleteWidget(payload: { widgetId: string }): void {
  if (isCalibrationMode.value || isCommandSettingsMode.value) {
    return
  }

  const nextWidgets = removeWidget(activeWidgets.value, payload.widgetId)
  if (nextWidgets === activeWidgets.value) {
    return
  }

  activeWidgets.value = nextWidgets
  syncFocus()
  void persistLayout()
}

const handleAddWidget = ({ widgetType }: { widgetType: string }) => {
  if (isCalibrationMode.value) {
    return
  }

  if (isCommandSettingsMode.value) {
    return
  }

  addFocusedWidget(widgetType)
}

const handleKeydown = (event: KeyboardEvent) => {
  if (isCalibrationMode.value) {
    return
  }

  if (isCommandSettingsMode.value) {
    return
  }

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
  dispatchUIActionPayload({
    action,
    input_source: 'keyboard',
    raw_input: `keyboard.${event.key.toLowerCase().replace(/\s+/g, '_')}`,
    timestamp: new Date().toISOString(),
    metadata: { key: event.key },
  })
}

watch(
  () => [
    isCalibrationMode.value,
    calibrationSession.value?.active_take?.status,
    calibrationSession.value?.active_take?.take_id,
    calibrationSession.value?.active_take?.ready_at,
    calibrationSession.value?.pending_take?.take_id,
  ],
  () => {
    scheduleCalibrationPreviewLoop()
    syncCalibrationCountdown()
  },
)

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  unsubscribeRealtime = realtimeClient.subscribe(handleRealtimeEvent)
  void loadInitialState()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  unsubscribeRealtime?.()
  stopCalibrationPreviewLoop()
  stopCalibrationCountdownLoop()
  if (gestureCooldownTimer !== null) {
    window.clearTimeout(gestureCooldownTimer)
  }
  if (initialLoadRetryTimer !== null) {
    window.clearTimeout(initialLoadRetryTimer)
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

    <div class="launcher-stack">
      <button class="command-launch" type="button" @click="void openCommandSettings()">
        Command Settings
      </button>

      <button class="calibration-launch" type="button" @click="void openCalibrationWizard()">
        Kalibrieren
      </button>
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
      v-if="!isCalibrationMode && !isCommandSettingsMode"
      :last-raw-input="lastRawInput"
      :last-command-match="lastCommandMatch"
      :last-u-i-action="lastUIAction"
      :focused-label="focusedLabel"
      :is-arrange-mode="isArrangeMode"
      :selected-widget-title="selectedWidget ? getWidgetDisplayTitle(selectedWidget) : null"
      :shop-visible="shopVisible"
      :cooldown-active="isGestureCoolingDown"
      :next-hint="nextHint"
    />

    <CalibrationWizard
      v-if="isCalibrationMode"
      :definitions="calibrationDefinitions"
      :session="calibrationSession"
      :loading="isCalibrationLoading"
      :busy="isCalibrationBusy"
      :error="calibrationError"
      :profile-name="calibrationProfileName"
      :gesture-devices="calibrationGestureDevices"
      :camera-index="calibrationCameraIndex"
      :selected-targets="calibrationSelectedTargets"
      :target-repetitions="calibrationTargetRepetitions"
      :last-event-message="calibrationEventMessage"
      :gesture-status="calibrationGestureStatus"
      :preview-image="calibrationPreviewImage"
      :preview-state="calibrationPreviewState"
      :preview-message="calibrationPreviewMessage"
      :countdown-seconds="calibrationCountdownSeconds"
      @update:profile-name="calibrationProfileName = $event"
      @update:camera-index="calibrationCameraIndex = $event"
      @update:selected-targets="calibrationSelectedTargets = $event"
      @update:target-repetitions="calibrationTargetRepetitions = $event"
      @start="void startCalibrationSession()"
      @prepare-take="void prepareCalibrationTake()"
      @start-take="void startCalibrationTake()"
      @stop-take="void stopCalibrationTake()"
      @accept-take="void acceptCalibrationTake()"
      @discard-take="void discardCalibrationTake()"
      @complete="void completeCalibrationSession()"
      @apply="void applyCalibrationSession()"
      @rollback="void rollbackCalibrationSession()"
      @discard="void discardCalibrationSession()"
      @close="void discardCalibrationSession()"
    />

    <CommandSettingsPanel
      v-if="isCommandSettingsMode"
      :command-profiles="commandProfilesConfig"
      :musical-audio-config="musicalAudioConfig"
      :artifacts="musicalAudioArtifacts"
      :gesture-devices="commandGestureDevices"
      :voice-devices="commandVoiceDevices"
      :musical-audio-devices="commandMusicalAudioDevices"
      :musical-audio-status="musicalAudioStatus"
      :loading="isCommandSettingsLoading"
      :saving="isCommandSettingsSaving"
      :error="commandSettingsError"
      @close="closeCommandSettings"
      @save-command-profiles="void saveCommandProfiles($event)"
      @save-musical-audio-config="void saveMusicalAudioConfigDraft($event)"
      @save-artifact="void saveMusicalAudioArtifact($event)"
      @delete-artifact="void deleteMusicalAudioArtifact($event)"
      @start-musical-audio="void startMusicalAudioRuntime($event)"
      @stop-musical-audio="void stopMusicalAudioRuntime()"
    />

    <GridBoard
      :widgets="renderedWidgets"
      :focused-cell="focusedState"
      :selected-widget-id="selectedWidgetId"
      :is-arrange-mode="isArrangeMode"
      @focus-cell="handleFocusCell"
      @focus-widget="handleFocusWidget"
      @resize-widget="handleResizeWidget"
      @delete-widget="handleDeleteWidget"
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

.launcher-stack {
  position: fixed;
  top: 16px;
  right: 18px;
  z-index: 1110;
  display: grid;
  gap: 10px;
}

.command-launch,
.calibration-launch {
  padding: 11px 16px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
}

.command-launch {
  border: 1px solid rgba(56, 189, 248, 0.42);
  background: rgba(7, 89, 133, 0.88);
  color: #e0f2fe;
  box-shadow: 0 14px 34px rgba(7, 89, 133, 0.28);
}

.calibration-launch {
  border: 1px solid rgba(245, 158, 11, 0.42);
  background: rgba(120, 53, 15, 0.88);
  color: #fef3c7;
  box-shadow: 0 14px 34px rgba(120, 53, 15, 0.35);
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
