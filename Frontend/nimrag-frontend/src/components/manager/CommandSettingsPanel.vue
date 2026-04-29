<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type {
  CommandProfilesConfig,
  MusicalAudioConfig,
  MusicalAudioNoteEvent,
  MusicalAudioTrainingArtifact,
} from '../../types/commands'
import type {
  GestureCameraDevice,
  MusicalAudioInputDevice,
  MusicalAudioStatusResponse,
  VoiceInputDevice,
} from '../../types/hardware'
import {
  buildContourPolyline,
  buildTemplateFromAcceptedTakes,
  extractNoteEventsFromSamples,
  type MusicalTrainingTake,
} from '../../utils/musicalTraining'
import {
  classifyMusicalTrainingCaptureError,
  evaluateMusicalTrainingEnvironment,
  type MusicalTrainingDiagnostic,
  type MusicalTrainingPermissionState,
} from '../../utils/musicalTrainingDiagnostics'

const props = defineProps<{
  commandProfiles: CommandProfilesConfig | null
  musicalAudioConfig: MusicalAudioConfig | null
  artifacts: MusicalAudioTrainingArtifact[]
  gestureDevices: GestureCameraDevice[]
  voiceDevices: VoiceInputDevice[]
  musicalAudioDevices: MusicalAudioInputDevice[]
  musicalAudioStatus: MusicalAudioStatusResponse | null
  loading: boolean
  saving: boolean
  error: string | null
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'save-command-profiles', value: CommandProfilesConfig): void
  (event: 'save-musical-audio-config', value: MusicalAudioConfig): void
  (event: 'save-artifact', value: MusicalAudioTrainingArtifact): void
  (event: 'delete-artifact', value: { artifactId: string; profileId: string }): void
  (event: 'start-musical-audio', value: number): void
  (event: 'stop-musical-audio'): void
}>()

type CommandSettingsPane = 'profiles' | 'mappings' | 'runtime' | 'training'
type TrainingTakeStatus = 'pending' | 'accepted' | 'rejected'
type BrowserTrainingState = 'ready' | 'recording' | 'processing' | 'error'

interface TrainingTakeRecord extends MusicalTrainingTake {
  status: TrainingTakeStatus
}

interface RecordingSession {
  stream: MediaStream
  audioContext: AudioContext
  analyser: AnalyserNode
  sampleTimerId: number
  timeoutId: number
  startedAt: number
  chunks: Float32Array[]
  peakLevel: number
}

interface BrowserAudioInputOption {
  deviceId: string
  label: string
}

const paneItems: Array<{ id: CommandSettingsPane; label: string; eyebrow: string }> = [
  { id: 'profiles', label: 'Profiles', eyebrow: 'Command setup' },
  { id: 'mappings', label: 'Mappings', eyebrow: 'Action routing' },
  { id: 'runtime', label: 'Runtime', eyebrow: 'Backend live capture' },
  { id: 'training', label: 'Training', eyebrow: 'Browser capture workspace' },
]

const runtimeStatusMeta: Record<MusicalAudioStatusResponse['status_code'], { label: string; tone: string; description: string }> = {
  unavailable: {
    label: 'Nicht verfuegbar',
    tone: 'muted',
    description: 'Backend-Abhaengigkeiten fehlen oder die Laufzeit kann in dieser Umgebung nicht gestartet werden.',
  },
  ready: {
    label: 'Bereit',
    tone: 'ok',
    description: 'Profil, aktives Artefakt und Geraetekontext sind fuer den Backend-Start aufgeloest.',
  },
  running: {
    label: 'Laeuft',
    tone: 'ok',
    description: 'Backend-Runtime lauscht auf dem konfigurierten Eingabegeraet.',
  },
  configuration_disabled: {
    label: 'Per Profil deaktiviert',
    tone: 'warning',
    description: 'Aktivierung wird aus dem aktiven Command-Profil abgeleitet, nicht aus dem Runtime-Tuning.',
  },
  no_active_artifact: {
    label: 'Kein aktives Artefakt',
    tone: 'warning',
    description: 'Backend-Live-Runtime startet erst, wenn ein aktives Training-Artefakt im Profil gesetzt ist.',
  },
  device_missing: {
    label: 'Backend-Geraet fehlt',
    tone: 'warning',
    description: 'Das PortAudio/sounddevice-Geraet aus dem aktiven Profil ist derzeit nicht verfuegbar.',
  },
  invalid_sample_rate: {
    label: 'Sample-Rate ungueltig',
    tone: 'warning',
    description: 'Die Backend-Runtime konnte keine gueltige Geraet-/Sample-Rate-Kombination validieren.',
  },
  permission_blocked: {
    label: 'Backend-Zugriff blockiert',
    tone: 'danger',
    description: 'Das Betriebssystem oder der Audiotreiber blockiert aktuell die Backend-Audioaufnahme.',
  },
  runtime_start_failed: {
    label: 'Start fehlgeschlagen',
    tone: 'danger',
    description: 'Der synchrone Preflight oder der Capture-Start wurde vom Backend abgebrochen.',
  },
  runtime_running_no_matchable_artifacts: {
    label: 'Laeuft ohne matchbare Artefakte',
    tone: 'warning',
    description: 'Die Runtime ist aktiv, aber derzeit sind keine matchbaren Templates geladen.',
  },
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function buildDefaultArtifact(profileId: string): MusicalAudioTrainingArtifact {
  return {
    artifact_id: `whistle-${Date.now()}`,
    profile_id: profileId,
    raw_input: 'melody.new_pattern',
    display_name: 'Neues Pfeifmuster',
    source_hint: 'whistle',
    notes: [
      { relative_pitch_semitones: 0, relative_time_seconds: 0, duration_seconds: 0.25, confidence: 0.9 },
      { relative_pitch_semitones: 2, relative_time_seconds: 0.3, duration_seconds: 0.2, confidence: 0.9 },
      { relative_pitch_semitones: 4, relative_time_seconds: 0.6, duration_seconds: 0.2, confidence: 0.9 },
    ],
    match_threshold: 3,
    minimum_confidence: 0.6,
    sample_count: 0,
    enabled: true,
    created_at: null,
    updated_at: null,
    metadata: {},
  }
}

function mergeTrainingChunks(chunks: Float32Array[]): Float32Array {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const merged = new Float32Array(totalLength)
  let offset = 0

  for (const chunk of chunks) {
    merged.set(chunk, offset)
    offset += chunk.length
  }

  return merged
}

async function getMicrophonePermissionState(): Promise<MusicalTrainingPermissionState> {
  if (!navigator.permissions?.query) {
    return 'unsupported'
  }

  try {
    const result = await navigator.permissions.query({ name: 'microphone' as PermissionName })
    return result.state
  } catch {
    return 'unsupported'
  }
}

const activePane = ref<CommandSettingsPane>('runtime')
const commandProfilesDraft = ref<CommandProfilesConfig | null>(null)
const musicalAudioConfigDraft = ref<MusicalAudioConfig | null>(null)
const artifactDraft = ref<MusicalAudioTrainingArtifact | null>(null)
const selectedArtifactId = ref<string | null>(null)
const trainingTakes = ref<TrainingTakeRecord[]>([])
const selectedTakeId = ref<string | null>(null)
const trainingState = ref<BrowserTrainingState>('ready')
const trainingMessage = ref<string | null>(null)
const recordingElapsedSeconds = ref(0)
const browserAudioDevices = ref<BrowserAudioInputOption[]>([])
const selectedBrowserDeviceId = ref<string | null>(null)
const trainingDiagnostics = ref<MusicalTrainingDiagnostic[]>([])

let recordingSession: RecordingSession | null = null

watch(
  () => props.commandProfiles,
  (value) => {
    commandProfilesDraft.value = value ? clone(value) : null
  },
  { immediate: true },
)

watch(
  () => props.musicalAudioConfig,
  (value) => {
    musicalAudioConfigDraft.value = value ? clone(value) : null
  },
  { immediate: true },
)

const activeProfile = computed(() => {
  const draft = commandProfilesDraft.value
  if (!draft) {
    return null
  }
  return draft.profiles.find((profile) => profile.profile_id === draft.active_profile_id) ?? draft.profiles[0] ?? null
})

watch(
  activeProfile,
  (profile) => {
    if (!profile || !musicalAudioConfigDraft.value) {
      return
    }

    musicalAudioConfigDraft.value.enabled = profile.modality_settings.musical_audio.enabled
    musicalAudioConfigDraft.value.device_index = profile.device_preferences.musical_audio_device_index ?? -1
    musicalAudioConfigDraft.value.active_artifact_id = profile.modality_settings.musical_audio.active_training_artifact_id
  },
  { immediate: true, deep: true },
)

watch(
  () => props.artifacts,
  (value) => {
    if (value.length === 0) {
      const activeProfileId = commandProfilesDraft.value?.active_profile_id ?? 'default'
      artifactDraft.value = buildDefaultArtifact(activeProfileId)
      selectedArtifactId.value = artifactDraft.value.artifact_id
      trainingTakes.value = []
      selectedTakeId.value = null
      return
    }

    const currentArtifact = value.find((artifact) => artifact.artifact_id === selectedArtifactId.value) ?? value[0] ?? null
    if (!currentArtifact) {
      return
    }

    selectedArtifactId.value = currentArtifact.artifact_id
    artifactDraft.value = clone(currentArtifact)
    trainingTakes.value = []
    selectedTakeId.value = null
  },
  { immediate: true },
)

const artifactOptions = computed(() => {
  const base = props.artifacts.map((artifact) => ({
    label: artifact.display_name,
    value: artifact.artifact_id,
  }))

  if (artifactDraft.value && !base.some((option) => option.value === artifactDraft.value?.artifact_id)) {
    return [{ label: artifactDraft.value.display_name, value: artifactDraft.value.artifact_id }, ...base]
  }

  return base
})

const acceptedTrainingTakes = computed(() => trainingTakes.value.filter((take) => take.status === 'accepted'))
const activeArtifactId = computed(() => activeProfile.value?.modality_settings.musical_audio.active_training_artifact_id ?? null)
const activeArtifactLabel = computed(() => {
  const artifactId = activeArtifactId.value
  if (!artifactId) {
    return 'Kein aktives Artefakt'
  }
  return props.artifacts.find((artifact) => artifact.artifact_id === artifactId)?.display_name ?? artifactId
})
const derivedTemplatePreview = computed(() => buildContourPolyline(artifactDraft.value?.notes ?? []))
const trainingSummary = computed(() => {
  const accepted = acceptedTrainingTakes.value.length
  const total = trainingTakes.value.length
  if (accepted >= 10 && accepted <= 20) {
    return `${accepted}/${total} freigegeben, bereit fuer Few-Shot-Aktivierung`
  }
  return `${accepted}/${total} freigegeben, Zielbereich 10-20 Takes`
})
const trainingPrimaryDiagnostic = computed(() => {
  return trainingDiagnostics.value.find((diagnostic) => diagnostic.severity === 'error')
    ?? trainingDiagnostics.value.find((diagnostic) => diagnostic.severity === 'warning')
    ?? trainingDiagnostics.value[0]
    ?? null
})
const runtimeDeviceIndex = computed(() => activeProfile.value?.device_preferences.musical_audio_device_index ?? -1)
const runtimeDeviceLabel = computed(() => {
  if (runtimeDeviceIndex.value < 0) {
    return 'Automatische Backend-Auswahl'
  }
  return props.musicalAudioDevices.find((device) => device.index === runtimeDeviceIndex.value)?.name
    ?? `Backend-Geraet ${runtimeDeviceIndex.value}`
})
const runtimeStatus = computed(() => {
  const code = props.musicalAudioStatus?.status_code ?? 'unavailable'
  return runtimeStatusMeta[code]
})
const trainingStateLabel = computed(() => {
  if (trainingState.value === 'recording') {
    return `recording · ${recordingElapsedSeconds.value.toFixed(1)}s`
  }
  if (trainingState.value === 'processing') {
    return 'processing'
  }
  if (trainingState.value === 'error') {
    return 'error'
  }
  return 'ready'
})

function updateMappingField(index: number, field: 'input_source' | 'raw_input' | 'action', value: string): void {
  if (!activeProfile.value) {
    return
  }

  const mapping = activeProfile.value.input_action_config.mappings[index]
  if (!mapping) {
    return
  }

  activeProfile.value.input_action_config.mappings[index] = { ...mapping, [field]: value }
}

function updateMappingEnabled(index: number, enabled: boolean): void {
  if (!activeProfile.value) {
    return
  }

  const mapping = activeProfile.value.input_action_config.mappings[index]
  if (!mapping) {
    return
  }

  activeProfile.value.input_action_config.mappings[index] = { ...mapping, enabled }
}

function removeMapping(index: number): void {
  activeProfile.value?.input_action_config.mappings.splice(index, 1)
}

function addMapping(): void {
  if (!activeProfile.value) {
    return
  }

  activeProfile.value.input_action_config.mappings.push({
    input_source: 'musical_audio',
    raw_input: 'melody.new_pattern',
    action: 'toggle_shop',
    enabled: true,
    metadata: {},
  })
}

function updateModalityEnabled(modality: keyof NonNullable<typeof activeProfile.value>['modality_settings'], enabled: boolean): void {
  if (!activeProfile.value) {
    return
  }
  activeProfile.value.modality_settings[modality] = {
    ...activeProfile.value.modality_settings[modality],
    enabled,
  }
}

function updateDevicePreference(field: 'gesture_camera_index' | 'voice_device_index' | 'musical_audio_device_index', value: number | null): void {
  if (!activeProfile.value) {
    return
  }
  activeProfile.value.device_preferences[field] = value
}

function handleDevicePreferenceChange(
  field: 'gesture_camera_index' | 'voice_device_index' | 'musical_audio_device_index',
  event: Event,
): void {
  const target = event.target as HTMLSelectElement | null
  if (!target) {
    return
  }
  updateDevicePreference(field, target.value === '' ? null : Number(target.value))
}

function saveCommandProfiles(): void {
  if (!commandProfilesDraft.value) {
    return
  }
  emit('save-command-profiles', clone(commandProfilesDraft.value))
}

function saveMusicalAudioConfig(): void {
  if (!musicalAudioConfigDraft.value) {
    return
  }
  emit('save-musical-audio-config', clone(musicalAudioConfigDraft.value))
}

function selectArtifact(artifactId: string): void {
  selectedArtifactId.value = artifactId
  const artifact = props.artifacts.find((entry) => entry.artifact_id === artifactId)
  artifactDraft.value = artifact ? clone(artifact) : artifactDraft.value
  trainingTakes.value = []
  selectedTakeId.value = null
}

function createArtifact(): void {
  const profileId = commandProfilesDraft.value?.active_profile_id ?? 'default'
  const nextArtifact = buildDefaultArtifact(profileId)
  selectedArtifactId.value = nextArtifact.artifact_id
  artifactDraft.value = nextArtifact
  trainingTakes.value = []
  selectedTakeId.value = null
  trainingMessage.value = 'Neues Artefakt angelegt. Speichere Profil und Artefakt getrennt, damit Runtime und Browser-Training nicht vermischt werden.'
}

function saveArtifact(): void {
  if (!artifactDraft.value) {
    return
  }
  emit('save-artifact', clone(artifactDraft.value))
}

function deleteArtifact(): void {
  if (!artifactDraft.value) {
    return
  }
  emit('delete-artifact', {
    artifactId: artifactDraft.value.artifact_id,
    profileId: artifactDraft.value.profile_id,
  })
}

function activateArtifactDraft(): void {
  if (!artifactDraft.value || !activeProfile.value) {
    return
  }

  activeProfile.value.modality_settings.musical_audio = {
    ...activeProfile.value.modality_settings.musical_audio,
    active_training_artifact_id: artifactDraft.value.artifact_id,
  }
  trainingMessage.value = `${artifactDraft.value.display_name} als aktives Runtime-Artefakt im Profil markiert. Profil jetzt speichern.`
}

function addNote(): void {
  if (!artifactDraft.value) {
    return
  }
  const lastNote = artifactDraft.value.notes[artifactDraft.value.notes.length - 1]
  const nextTime = artifactDraft.value.notes.length === 0 ? 0 : ((lastNote?.relative_time_seconds ?? 0) + 0.3)
  artifactDraft.value.notes.push({
    relative_pitch_semitones: 0,
    relative_time_seconds: Number(nextTime.toFixed(2)),
    duration_seconds: 0.2,
    confidence: 0.9,
  })
}

function removeNote(index: number): void {
  artifactDraft.value?.notes.splice(index, 1)
}

function updateNote(index: number, patch: Partial<MusicalAudioNoteEvent>): void {
  if (!artifactDraft.value) {
    return
  }

  const currentNote = artifactDraft.value.notes[index]
  if (!currentNote) {
    return
  }

  artifactDraft.value.notes[index] = { ...currentNote, ...patch }
}

function clearRecordingSession(session: RecordingSession): void {
  window.clearInterval(session.sampleTimerId)
  window.clearTimeout(session.timeoutId)
  session.stream.getTracks().forEach((track) => track.stop())
  void session.audioContext.close().catch(() => undefined)
}

async function refreshTrainingDiagnostics(): Promise<void> {
  const hasMediaDevices = Boolean(navigator.mediaDevices)
  const hasGetUserMedia = Boolean(navigator.mediaDevices?.getUserMedia)
  const hasAudioContext = typeof window.AudioContext !== 'undefined'
  const permissionState = await getMicrophonePermissionState()

  let topLevel = true
  try {
    topLevel = window.top === window.self
  } catch {
    topLevel = false
  }

  let devices: MediaDeviceInfo[] = []
  if (navigator.mediaDevices?.enumerateDevices) {
    try {
      devices = await navigator.mediaDevices.enumerateDevices()
    } catch {
      devices = []
    }
  }

  const inputDevices = devices
    .filter((device) => device.kind === 'audioinput')
    .map((device, index) => ({
      deviceId: device.deviceId,
      label: device.label || `Browser-Mikrofon ${index + 1}`,
    }))

  browserAudioDevices.value = inputDevices
  if (selectedBrowserDeviceId.value && !inputDevices.some((device) => device.deviceId === selectedBrowserDeviceId.value)) {
    selectedBrowserDeviceId.value = null
  }

  const result = evaluateMusicalTrainingEnvironment({
    isSecureContext: window.isSecureContext,
    hostname: window.location.hostname,
    topLevel,
    hasMediaDevices,
    hasGetUserMedia,
    hasAudioContext,
    permissionState,
    inputDeviceCount: inputDevices.length,
  })

  trainingDiagnostics.value = result.diagnostics
  if (trainingState.value !== 'recording' && trainingState.value !== 'processing') {
    trainingState.value = result.ready ? 'ready' : 'error'
  }
}

async function startTrainingRecording(): Promise<void> {
  if (trainingState.value === 'recording') {
    return
  }

  if (!artifactDraft.value || !musicalAudioConfigDraft.value) {
    trainingState.value = 'error'
    trainingMessage.value = 'Waehle zuerst ein Trainingsartefakt aus.'
    return
  }

  await refreshTrainingDiagnostics()
  const blockingDiagnostic = trainingDiagnostics.value.find((diagnostic) => diagnostic.severity === 'error')
  if (blockingDiagnostic) {
    trainingState.value = 'error'
    trainingMessage.value = blockingDiagnostic.message
    return
  }

  const audioConstraints: MediaTrackConstraints = {
    channelCount: 1,
    echoCancellation: false,
    noiseSuppression: false,
    autoGainControl: false,
  }

  if (selectedBrowserDeviceId.value) {
    audioConstraints.deviceId = { exact: selectedBrowserDeviceId.value }
  }

  trainingMessage.value = null

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints })
    const audioContext = new window.AudioContext()
    const source = audioContext.createMediaStreamSource(stream)
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 2048
    analyser.smoothingTimeConstant = 0.1
    source.connect(analyser)

    const chunks: Float32Array[] = []
    const sampleBuffer = new Float32Array(analyser.fftSize)
    const startedAt = performance.now()
    recordingElapsedSeconds.value = 0

    const sampleTimerId = window.setInterval(() => {
      analyser.getFloatTimeDomainData(sampleBuffer)
      const snapshot = sampleBuffer.slice()
      chunks.push(snapshot)
      recordingElapsedSeconds.value = (performance.now() - startedAt) / 1000
      const peakLevel = snapshot.reduce((peak, value) => Math.max(peak, Math.abs(value)), 0)
      if (recordingSession) {
        recordingSession.peakLevel = Math.max(recordingSession.peakLevel, peakLevel)
      }
    }, 50)

    const timeoutId = window.setTimeout(() => {
      void stopTrainingRecording()
    }, Math.max(1000, musicalAudioConfigDraft.value.max_pattern_window_seconds * 1000))

    recordingSession = {
      stream,
      audioContext,
      analyser,
      sampleTimerId,
      timeoutId,
      startedAt,
      chunks,
      peakLevel: 0,
    }

    trainingState.value = 'recording'
    await refreshTrainingDiagnostics()
  } catch (error) {
    const diagnostic = classifyMusicalTrainingCaptureError(error)
    trainingState.value = 'error'
    trainingMessage.value = diagnostic.message
  }
}

async function stopTrainingRecording(): Promise<void> {
  if (!recordingSession || !musicalAudioConfigDraft.value) {
    return
  }

  const session = recordingSession
  recordingSession = null
  trainingState.value = 'processing'
  recordingElapsedSeconds.value = (performance.now() - session.startedAt) / 1000
  const sampleRate = session.audioContext.sampleRate
  clearRecordingSession(session)

  const mergedSamples = mergeTrainingChunks(session.chunks)
  const extractedNotes = extractNoteEventsFromSamples(mergedSamples, sampleRate, {
    minAmplitude: Math.max(0.0025, musicalAudioConfigDraft.value.silence_threshold),
    minConfidence: Math.max(0.55, musicalAudioConfigDraft.value.pitch_confidence_threshold),
    minNoteDurationSeconds: 0.07,
  })

  if (extractedNotes.length < musicalAudioConfigDraft.value.min_pattern_notes) {
    trainingState.value = 'error'
    trainingMessage.value = `Zu wenig stabile Noten erkannt (${extractedNotes.length}). Browser-Training und Backend-Runtime sind getrennt; pruefe Mikrofon, Pegel und Kontext erneut.`
    return
  }

  const nextTake: TrainingTakeRecord = {
    takeId: `take-${Date.now()}`,
    label: `Take ${trainingTakes.value.length + 1}`,
    notes: extractedNotes,
    durationSeconds: Number(recordingElapsedSeconds.value.toFixed(2)),
    peakLevel: Number(session.peakLevel.toFixed(3)),
    capturedAt: new Date().toISOString(),
    status: 'pending',
  }

  trainingTakes.value = [nextTake, ...trainingTakes.value]
  selectedTakeId.value = nextTake.takeId
  trainingState.value = 'ready'
  trainingMessage.value = `${nextTake.label} analysiert. Kontur pruefen, freigeben und bei Bedarf in das Artefakt laden.`
}

function setTakeStatus(takeId: string, status: TrainingTakeStatus): void {
  trainingTakes.value = trainingTakes.value.map((take) => take.takeId === takeId ? { ...take, status } : take)
}

function removeTrainingTake(takeId: string): void {
  const remainingTakes = trainingTakes.value.filter((take) => take.takeId !== takeId)
  trainingTakes.value = remainingTakes
  if (selectedTakeId.value === takeId) {
    selectedTakeId.value = remainingTakes[0]?.takeId ?? null
  }
}

function loadTakeIntoArtifact(takeId: string): void {
  if (!artifactDraft.value) {
    return
  }

  const take = trainingTakes.value.find((entry) => entry.takeId === takeId)
  if (!take) {
    return
  }

  artifactDraft.value.notes = clone(take.notes)
  artifactDraft.value.sample_count = 1
  selectedTakeId.value = takeId
  trainingMessage.value = `${take.label} als Kontur-Entwurf in das Artefakt geladen.`
}

function applyAcceptedTrainingTakes(): void {
  if (!artifactDraft.value) {
    return
  }

  const accepted: MusicalTrainingTake[] = acceptedTrainingTakes.value.map((take) => ({
    takeId: take.takeId,
    label: take.label,
    notes: take.notes,
    durationSeconds: take.durationSeconds,
    peakLevel: take.peakLevel,
    capturedAt: take.capturedAt,
  }))
  const templateNotes = buildTemplateFromAcceptedTakes(accepted)

  if (templateNotes.length === 0) {
    trainingMessage.value = 'Es gibt noch keine freigegebenen Takes zum Ableiten.'
    return
  }

  artifactDraft.value.notes = templateNotes
  artifactDraft.value.sample_count = accepted.length
  artifactDraft.value.metadata = {
    ...artifactDraft.value.metadata,
    training_take_count: accepted.length,
    last_training_update_at: new Date().toISOString(),
  }
  trainingMessage.value = `${accepted.length} freigegebene Browser-Takes zu einem Template verdichtet.`
}

function isTakeActive(takeId: string): boolean {
  return selectedTakeId.value === takeId
}

onMounted(() => {
  void refreshTrainingDiagnostics()
})

watch(activePane, (pane) => {
  if (pane === 'training') {
    void refreshTrainingDiagnostics()
  }
})

onBeforeUnmount(() => {
  if (recordingSession) {
    clearRecordingSession(recordingSession)
    recordingSession = null
  }
})
</script>

<template>
  <div class="command-settings-backdrop" @click.self="emit('close')">
    <section class="command-settings-shell">
      <header class="shell-header">
        <div>
          <p class="eyebrow">Command Settings</p>
          <h2>Profiles, Runtime und Browser-Training</h2>
          <p class="subcopy">Backend-Live-Runtime und Browser-Training sind getrennte Betriebsarten mit eigener Geraete- und Fehlerlogik.</p>
        </div>
        <div class="toolbar-row">
          <span class="status-pill" :data-tone="runtimeStatus.tone">{{ runtimeStatus.label }}</span>
          <button class="ghost-button" type="button" @click="emit('close')">Schliessen</button>
        </div>
      </header>

      <p v-if="error" class="error-banner">{{ error }}</p>

      <div v-if="loading || !commandProfilesDraft || !musicalAudioConfigDraft" class="empty-state">
        <strong>Command Settings werden geladen.</strong>
      </div>

      <template v-else>
        <div class="shell-layout">
          <aside class="pane-nav">
            <button
              v-for="item in paneItems"
              :key="item.id"
              class="pane-nav-button"
              :class="{ active: activePane === item.id }"
              type="button"
              @click="activePane = item.id"
            >
              <span class="eyebrow">{{ item.eyebrow }}</span>
              <strong>{{ item.label }}</strong>
            </button>
          </aside>

          <div class="pane-body">
            <section v-if="activePane === 'profiles'" class="pane-content">
              <article class="surface-card hero-card">
                <div class="section-header wide">
                  <div>
                    <p class="eyebrow">Active Profile</p>
                    <h3>{{ activeProfile?.display_name ?? 'n/a' }}</h3>
                    <p class="subcopy">Aktivierung, Backend-Geraeteauswahl und aktives Runtime-Artefakt werden vom aktiven Command-Profil abgeleitet.</p>
                  </div>
                  <button class="primary-button" type="button" :disabled="saving" @click="saveCommandProfiles">
                    {{ saving ? 'Speichert...' : 'Profil speichern' }}
                  </button>
                </div>
                <div v-if="activeProfile" class="field-grid two-col">
                  <label class="field-label">
                    Anzeigename
                    <input v-model="activeProfile.display_name" class="field-input" />
                  </label>
                  <label class="field-label">
                    Beschreibung
                    <input v-model="activeProfile.description" class="field-input" />
                  </label>
                </div>
              </article>

              <article v-if="activeProfile" class="surface-card">
                <div class="section-header wide">
                  <div>
                    <p class="eyebrow">Modalities</p>
                    <strong>Aktivierung und Backend-Praeferenzen</strong>
                  </div>
                </div>

                <div class="toggle-grid">
                  <label class="toggle-row">
                    <span>Gestures</span>
                    <input type="checkbox" :checked="activeProfile.modality_settings.gesture.enabled" @change="updateModalityEnabled('gesture', ($event.target as HTMLInputElement).checked)" />
                  </label>
                  <label class="toggle-row">
                    <span>Voice</span>
                    <input type="checkbox" :checked="activeProfile.modality_settings.voice.enabled" @change="updateModalityEnabled('voice', ($event.target as HTMLInputElement).checked)" />
                  </label>
                  <label class="toggle-row">
                    <span>Musical Audio</span>
                    <input type="checkbox" :checked="activeProfile.modality_settings.musical_audio.enabled" @change="updateModalityEnabled('musical_audio', ($event.target as HTMLInputElement).checked)" />
                  </label>
                </div>

                <div class="field-grid three-col">
                  <label class="field-label">
                    Geste Kamera
                    <select class="field-input" :value="activeProfile.device_preferences.gesture_camera_index ?? ''" @change="handleDevicePreferenceChange('gesture_camera_index', $event)">
                      <option value="">Automatisch</option>
                      <option v-for="device in gestureDevices" :key="device.index" :value="device.index">{{ device.name }}</option>
                    </select>
                  </label>

                  <label class="field-label">
                    Voice Geraet
                    <select class="field-input" :value="activeProfile.device_preferences.voice_device_index ?? ''" @change="handleDevicePreferenceChange('voice_device_index', $event)">
                      <option value="">Automatisch</option>
                      <option v-for="device in voiceDevices" :key="device.index" :value="device.index">{{ device.name }}</option>
                    </select>
                  </label>

                  <label class="field-label">
                    Backend-Musical-Audio-Geraet
                    <select class="field-input" :value="activeProfile.device_preferences.musical_audio_device_index ?? ''" @change="handleDevicePreferenceChange('musical_audio_device_index', $event)">
                      <option value="">Automatisch</option>
                      <option v-for="device in musicalAudioDevices" :key="device.index" :value="device.index">{{ device.name }}</option>
                    </select>
                  </label>
                </div>
              </article>
            </section>

            <section v-else-if="activePane === 'mappings'" class="pane-content">
              <article class="surface-card">
                <div class="section-header wide">
                  <div>
                    <p class="eyebrow">Mappings</p>
                    <strong>{{ activeProfile?.input_action_config.mappings.length ?? 0 }} Regeln</strong>
                  </div>
                  <button class="ghost-button" type="button" @click="addMapping">Mapping hinzufuegen</button>
                </div>

                <div v-if="activeProfile" class="mapping-list">
                  <div v-for="(mapping, index) in activeProfile.input_action_config.mappings" :key="`${mapping.raw_input}-${index}`" class="mapping-row">
                    <select class="field-input" :value="mapping.input_source" @change="updateMappingField(index, 'input_source', ($event.target as HTMLSelectElement).value)">
                      <option value="gesture">gesture</option>
                      <option value="voice">voice</option>
                      <option value="musical_audio">musical_audio</option>
                      <option value="keyboard">keyboard</option>
                      <option value="dev">dev</option>
                    </select>
                    <input class="field-input" :value="mapping.raw_input" @input="updateMappingField(index, 'raw_input', ($event.target as HTMLInputElement).value)" />
                    <select class="field-input" :value="mapping.action" @change="updateMappingField(index, 'action', ($event.target as HTMLSelectElement).value)">
                      <option value="move_focus_left">move_focus_left</option>
                      <option value="move_focus_right">move_focus_right</option>
                      <option value="move_focus_up">move_focus_up</option>
                      <option value="move_focus_down">move_focus_down</option>
                      <option value="toggle_shop">toggle_shop</option>
                      <option value="primary_click">primary_click</option>
                      <option value="secondary_select">secondary_select</option>
                      <option value="resize_expand">resize_expand</option>
                      <option value="resize_shrink">resize_shrink</option>
                      <option value="move_selected_widget">move_selected_widget</option>
                      <option value="cancel_selection">cancel_selection</option>
                    </select>
                    <label class="inline-toggle">
                      <input type="checkbox" :checked="mapping.enabled" @change="updateMappingEnabled(index, ($event.target as HTMLInputElement).checked)" />
                      aktiv
                    </label>
                    <button class="ghost-button danger" type="button" @click="removeMapping(index)">Entfernen</button>
                  </div>
                </div>
              </article>
            </section>

            <section v-else-if="activePane === 'runtime'" class="pane-content">
              <article class="surface-card hero-card">
                <div class="section-header wide">
                  <div>
                    <p class="eyebrow">Backend Runtime</p>
                    <h3>{{ runtimeStatus.label }}</h3>
                    <p class="subcopy">{{ runtimeStatus.description }}</p>
                  </div>
                  <div class="toolbar-row compact">
                    <button class="ghost-button" type="button" :disabled="saving" @click="saveMusicalAudioConfig">Runtime-Tuning speichern</button>
                    <button class="primary-button" type="button" :disabled="saving" @click="emit('start-musical-audio', runtimeDeviceIndex)">Runtime starten</button>
                    <button class="ghost-button" type="button" :disabled="saving" @click="emit('stop-musical-audio')">Stop</button>
                  </div>
                </div>

                <div class="stats-grid">
                  <div class="stat-card">
                    <span class="eyebrow">Derived Activation</span>
                    <strong>{{ activeProfile?.modality_settings.musical_audio.enabled ? 'aktiv' : 'deaktiviert' }}</strong>
                    <p>Quelle: aktives Command-Profil</p>
                  </div>
                  <div class="stat-card">
                    <span class="eyebrow">Backend Device</span>
                    <strong>{{ runtimeDeviceLabel }}</strong>
                    <p>Quelle: Command-Profile.device_preferences</p>
                  </div>
                  <div class="stat-card">
                    <span class="eyebrow">Aktives Runtime-Artefakt</span>
                    <strong>{{ activeArtifactLabel }}</strong>
                    <p>Quelle: Command-Profile.modality_settings</p>
                  </div>
                  <div class="stat-card">
                    <span class="eyebrow">Validierter Stream</span>
                    <strong>{{ props.musicalAudioStatus?.validated_sample_rate ?? musicalAudioConfigDraft.sample_rate }} Hz</strong>
                    <p>{{ props.musicalAudioStatus?.validated_device_index ?? runtimeDeviceIndex }} / {{ props.musicalAudioStatus?.provider ?? 'unavailable' }}</p>
                  </div>
                </div>
              </article>

              <article class="surface-card">
                <div class="section-header wide">
                  <div>
                    <p class="eyebrow">Runtime Tuning</p>
                    <strong>Sample-Rate, Windowing und Matching</strong>
                  </div>
                </div>

                <div class="field-grid three-col">
                  <label class="field-label">
                    Sample Rate
                    <input v-model.number="musicalAudioConfigDraft.sample_rate" class="field-input" type="number" min="8000" max="48000" />
                  </label>
                  <label class="field-label">
                    Block Size
                    <input v-model.number="musicalAudioConfigDraft.block_size" class="field-input" type="number" min="256" max="8192" />
                  </label>
                  <label class="field-label">
                    Queue Chunks
                    <input v-model.number="musicalAudioConfigDraft.queue_max_chunks" class="field-input" type="number" min="1" max="256" />
                  </label>
                  <label class="field-label">
                    Silence Threshold
                    <input v-model.number="musicalAudioConfigDraft.silence_threshold" class="field-input" type="number" min="0" max="1" step="0.001" />
                  </label>
                  <label class="field-label">
                    Pitch Confidence
                    <input v-model.number="musicalAudioConfigDraft.pitch_confidence_threshold" class="field-input" type="number" min="0" max="1" step="0.01" />
                  </label>
                  <label class="field-label">
                    Cooldown
                    <input v-model.number="musicalAudioConfigDraft.command_cooldown_seconds" class="field-input" type="number" min="0" max="30" step="0.1" />
                  </label>
                  <label class="field-label">
                    Min Notes
                    <input v-model.number="musicalAudioConfigDraft.min_pattern_notes" class="field-input" type="number" min="1" max="64" />
                  </label>
                  <label class="field-label">
                    Max Window
                    <input v-model.number="musicalAudioConfigDraft.max_pattern_window_seconds" class="field-input" type="number" min="0.2" max="30" step="0.1" />
                  </label>
                </div>
              </article>

              <article class="surface-card">
                <div class="section-header wide">
                  <div>
                    <p class="eyebrow">Runtime Telemetry</p>
                    <strong>Letzte bekannte Backend-Sicht</strong>
                  </div>
                </div>

                <div class="stats-grid">
                  <div class="stat-card"><span class="eyebrow">Status-Code</span><strong>{{ props.musicalAudioStatus?.status_code ?? 'unavailable' }}</strong></div>
                  <div class="stat-card"><span class="eyebrow">Artefakte geladen</span><strong>{{ props.musicalAudioStatus?.artifacts_loaded ?? 0 }}</strong></div>
                  <div class="stat-card"><span class="eyebrow">Letztes Match</span><strong>{{ props.musicalAudioStatus?.last_match ?? 'n/a' }}</strong></div>
                  <div class="stat-card"><span class="eyebrow">Letzte Pitch-Hz</span><strong>{{ props.musicalAudioStatus?.last_pitch_hz ?? 'n/a' }}</strong></div>
                </div>

                <p class="diagnostic-callout" :data-tone="runtimeStatus.tone">
                  <strong>Letzter Fehler:</strong>
                  <span>{{ props.musicalAudioStatus?.last_error ?? 'kein Fehler' }}</span>
                </p>
              </article>
            </section>

            <section v-else class="pane-content">
              <article class="surface-card hero-card">
                <div class="section-header wide">
                  <div>
                    <p class="eyebrow">Browser Training Workspace</p>
                    <h3>{{ artifactDraft?.display_name ?? 'Neues Artefakt' }}</h3>
                    <p class="subcopy">Browser-Aufnahme und Backend-Live-Runtime sind getrennt. Browser nutzt Web Audio und eigene Geraetelogik.</p>
                  </div>
                  <div class="toolbar-row compact">
                    <button class="ghost-button" type="button" @click="createArtifact">Neu</button>
                    <button class="ghost-button" type="button" :disabled="!artifactDraft" @click="saveArtifact">Artefakt speichern</button>
                    <button class="ghost-button" type="button" :disabled="!artifactDraft" @click="activateArtifactDraft">Als Runtime-Artefakt markieren</button>
                    <button class="primary-button" type="button" :disabled="saving" @click="saveCommandProfiles">Profil speichern</button>
                  </div>
                </div>
              </article>

              <div class="workspace-grid">
                <article class="surface-card">
                  <div class="section-header wide">
                    <div>
                      <p class="eyebrow">Artefakt Editor</p>
                      <strong>Template, Metadaten und Kontur</strong>
                    </div>
                    <button class="ghost-button danger" type="button" :disabled="!artifactDraft" @click="deleteArtifact">Loeschen</button>
                  </div>

                  <label class="field-label">
                    Artefakt
                    <select class="field-input" :value="selectedArtifactId ?? ''" @change="selectArtifact(($event.target as HTMLSelectElement).value)">
                      <option v-for="option in artifactOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                  </label>

                  <div v-if="artifactDraft" class="field-grid two-col">
                    <label class="field-label">
                      Anzeigename
                      <input v-model="artifactDraft.display_name" class="field-input" />
                    </label>
                    <label class="field-label">
                      Raw Input
                      <input v-model="artifactDraft.raw_input" class="field-input" />
                    </label>
                    <label class="field-label">
                      Quelle
                      <select v-model="artifactDraft.source_hint" class="field-input">
                        <option value="whistle">whistle</option>
                        <option value="voice">voice</option>
                        <option value="instrument">instrument</option>
                        <option value="unknown">unknown</option>
                      </select>
                    </label>
                    <label class="field-label">
                      Match Threshold
                      <input v-model.number="artifactDraft.match_threshold" class="field-input" type="number" min="0" step="0.1" />
                    </label>
                    <label class="field-label">
                      Min Confidence
                      <input v-model.number="artifactDraft.minimum_confidence" class="field-input" type="number" min="0" max="1" step="0.01" />
                    </label>
                    <label class="field-label">
                      Samples
                      <input v-model.number="artifactDraft.sample_count" class="field-input" type="number" min="0" />
                    </label>
                  </div>

                  <div v-if="artifactDraft" class="notes-section">
                    <div class="section-header wide">
                      <strong>Kontur-Noten</strong>
                      <button class="ghost-button" type="button" @click="addNote">Note hinzufuegen</button>
                    </div>

                    <div v-for="(note, index) in artifactDraft.notes" :key="index" class="note-row">
                      <input class="field-input" type="number" step="0.1" :value="note.relative_pitch_semitones" @input="updateNote(index, { relative_pitch_semitones: Number(($event.target as HTMLInputElement).value) })" />
                      <input class="field-input" type="number" step="0.01" :value="note.relative_time_seconds" @input="updateNote(index, { relative_time_seconds: Number(($event.target as HTMLInputElement).value) })" />
                      <input class="field-input" type="number" step="0.01" :value="note.duration_seconds ?? 0.2" @input="updateNote(index, { duration_seconds: Number(($event.target as HTMLInputElement).value) })" />
                      <input class="field-input" type="number" step="0.01" min="0" max="1" :value="note.confidence ?? 0.9" @input="updateNote(index, { confidence: Number(($event.target as HTMLInputElement).value) })" />
                      <button class="ghost-button danger" type="button" @click="removeNote(index)">Entfernen</button>
                    </div>
                  </div>

                  <div class="template-preview-card">
                    <div class="section-header wide">
                      <div>
                        <p class="eyebrow">Template Preview</p>
                        <strong>{{ artifactDraft?.display_name ?? 'n/a' }}</strong>
                      </div>
                      <span class="status-pill" :data-tone="activeArtifactId === artifactDraft?.artifact_id ? 'ok' : 'muted'">
                        {{ activeArtifactId === artifactDraft?.artifact_id ? 'aktiv im Profil' : 'noch nicht aktiv' }}
                      </span>
                    </div>
                    <svg class="contour-preview large" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">
                      <polyline :points="derivedTemplatePreview" />
                    </svg>
                  </div>
                </article>

                <article class="surface-card">
                  <div class="section-header wide">
                    <div>
                      <p class="eyebrow">Browser Capture</p>
                      <strong>{{ trainingStateLabel }}</strong>
                    </div>
                    <div class="toolbar-row compact">
                      <button
                        class="primary-button"
                        type="button"
                        :disabled="trainingState === 'processing'"
                        @click="trainingState === 'recording' ? stopTrainingRecording() : startTrainingRecording()"
                      >
                        {{ trainingState === 'recording' ? 'Aufnahme stoppen' : 'Take aufnehmen' }}
                      </button>
                      <button class="ghost-button" type="button" :disabled="acceptedTrainingTakes.length === 0" @click="applyAcceptedTrainingTakes">
                        Freigegebene Takes verdichten
                      </button>
                    </div>
                  </div>

                  <div class="stats-grid">
                    <div class="stat-card">
                      <span class="eyebrow">Runtime Device</span>
                      <strong>{{ runtimeDeviceLabel }}</strong>
                      <p>Backend / sounddevice</p>
                    </div>
                    <div class="stat-card">
                      <span class="eyebrow">Browser Device</span>
                      <strong>{{ selectedBrowserDeviceId ? browserAudioDevices.find((device) => device.deviceId === selectedBrowserDeviceId)?.label ?? 'gewahlt' : 'Automatisch' }}</strong>
                      <p>Web Audio / getUserMedia</p>
                    </div>
                    <div class="stat-card">
                      <span class="eyebrow">Aktives Runtime-Artefakt</span>
                      <strong>{{ activeArtifactLabel }}</strong>
                      <p>Wird separat im Profil gespeichert</p>
                    </div>
                    <div class="stat-card">
                      <span class="eyebrow">Training-Ziel</span>
                      <strong>{{ trainingSummary }}</strong>
                      <p>10-20 gute Takes reichen meist aus</p>
                    </div>
                  </div>

                  <label class="field-label">
                    Browser-Aufnahmegeraet
                    <select v-model="selectedBrowserDeviceId" class="field-input">
                      <option :value="null">Automatisch</option>
                      <option v-for="device in browserAudioDevices" :key="device.deviceId" :value="device.deviceId">{{ device.label }}</option>
                    </select>
                  </label>

                  <div class="diagnostic-list">
                    <article
                      v-for="diagnostic in trainingDiagnostics"
                      :key="diagnostic.code"
                      class="diagnostic-card"
                      :data-tone="diagnostic.severity === 'error' ? 'danger' : diagnostic.severity === 'warning' ? 'warning' : 'ok'"
                    >
                      <strong>{{ diagnostic.code }}</strong>
                      <p>{{ diagnostic.message }}</p>
                    </article>
                  </div>

                  <p v-if="trainingMessage" class="diagnostic-callout" :data-tone="trainingPrimaryDiagnostic?.severity === 'error' || trainingState === 'error' ? 'danger' : 'ok'">
                    {{ trainingMessage }}
                  </p>

                  <div class="take-list">
                    <article
                      v-for="take in trainingTakes"
                      :key="take.takeId"
                      class="take-card"
                      :class="[`status-${take.status}`, { active: isTakeActive(take.takeId) }]"
                    >
                      <div class="take-header-row">
                        <div>
                          <strong>{{ take.label }}</strong>
                          <p class="meta-text">{{ take.notes.length }} Noten · {{ take.durationSeconds.toFixed(2) }}s · Peak {{ take.peakLevel.toFixed(2) }}</p>
                        </div>
                        <span class="status-pill" :data-tone="take.status === 'accepted' ? 'ok' : take.status === 'rejected' ? 'danger' : 'muted'">
                          {{ take.status }}
                        </span>
                      </div>
                      <svg class="contour-preview" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">
                        <polyline :points="buildContourPolyline(take.notes)" />
                      </svg>
                      <div class="toolbar-row compact wrap">
                        <button class="ghost-button" type="button" @click="setTakeStatus(take.takeId, 'accepted')">Freigeben</button>
                        <button class="ghost-button" type="button" @click="setTakeStatus(take.takeId, 'rejected')">Verwerfen</button>
                        <button class="ghost-button" type="button" @click="setTakeStatus(take.takeId, 'pending')">Zurueckstellen</button>
                        <button class="ghost-button" type="button" @click="loadTakeIntoArtifact(take.takeId)">Als Entwurf laden</button>
                        <button class="ghost-button danger" type="button" @click="removeTrainingTake(take.takeId)">Entfernen</button>
                      </div>
                    </article>
                  </div>
                </article>
              </div>
            </section>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.command-settings-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1320;
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 16px;
  background:
    radial-gradient(circle at top left, rgba(14, 165, 233, 0.18), transparent 28%),
    radial-gradient(circle at bottom right, rgba(251, 146, 60, 0.16), transparent 26%),
    rgba(9, 14, 22, 0.84);
  backdrop-filter: blur(18px);
}

.command-settings-shell {
  width: min(1600px, 100%);
  height: calc(100vh - 32px);
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 18px;
  padding: 24px;
  border-radius: 28px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.98), rgba(17, 24, 39, 0.96));
  color: #f8fafc;
  box-shadow: 0 30px 80px rgba(2, 6, 23, 0.48);
  overflow: hidden;
}

.shell-header,
.section-header,
.toolbar-row,
.stats-grid,
.field-grid,
.toggle-grid,
.workspace-grid,
.shell-layout,
.mapping-list,
.diagnostic-list,
.take-list,
.notes-section,
.note-row,
.mapping-row,
.pane-content {
  display: grid;
  gap: 16px;
}

.shell-header,
.section-header.wide,
.toolbar-row {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
}

.toolbar-row {
  justify-items: end;
}

.toolbar-row.compact {
  gap: 10px;
}

.toolbar-row.wrap {
  grid-template-columns: repeat(auto-fit, minmax(140px, max-content));
  justify-content: start;
  justify-items: start;
}

.shell-layout {
  grid-template-columns: 280px minmax(0, 1fr);
  min-height: 0;
}

.pane-nav {
  display: grid;
  gap: 10px;
  align-content: start;
}

.pane-nav-button,
.surface-card,
.stat-card,
.take-card,
.template-preview-card,
.diagnostic-card,
.empty-state {
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.74);
}

.pane-nav-button {
  padding: 18px;
  text-align: left;
  color: inherit;
}

.pane-nav-button.active {
  border-color: rgba(56, 189, 248, 0.4);
  background: linear-gradient(180deg, rgba(14, 165, 233, 0.16), rgba(15, 23, 42, 0.82));
}

.pane-body {
  min-height: 0;
  overflow: auto;
  padding-right: 6px;
}

.pane-content {
  align-content: start;
}

.surface-card,
.template-preview-card,
.empty-state,
.diagnostic-card,
.take-card,
.stat-card {
  padding: 20px;
}

.hero-card {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.12), rgba(15, 23, 42, 0.82));
}

.workspace-grid {
  grid-template-columns: 1.05fr 0.95fr;
}

.stats-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.field-grid.two-col {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field-grid.three-col,
.note-row,
.mapping-row {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.note-row {
  grid-template-columns: 1fr 1fr 1fr 1fr auto;
}

.mapping-row {
  grid-template-columns: 0.9fr 1.1fr 1.1fr auto auto;
  align-items: center;
}

.toggle-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.toggle-row,
.field-label,
.inline-toggle {
  display: grid;
  gap: 8px;
}

.toggle-row {
  grid-template-columns: 1fr auto;
  align-items: center;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(30, 41, 59, 0.62);
}

.field-input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  padding: 12px 14px;
  background: rgba(15, 23, 42, 0.82);
  color: inherit;
}

.diagnostic-list,
.mapping-list,
.notes-section,
.take-list {
  margin-top: 8px;
}

.diagnostic-card p,
.subcopy,
.meta-text,
.stat-card p {
  margin: 0;
  color: rgba(226, 232, 240, 0.76);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(30, 41, 59, 0.72);
  font-size: 0.84rem;
}

.status-pill[data-tone='ok'],
.diagnostic-card[data-tone='ok'] {
  border-color: rgba(74, 222, 128, 0.4);
}

.status-pill[data-tone='warning'],
.diagnostic-card[data-tone='warning'] {
  border-color: rgba(251, 191, 36, 0.42);
}

.status-pill[data-tone='danger'],
.diagnostic-card[data-tone='danger'],
.diagnostic-callout[data-tone='danger'] {
  border-color: rgba(248, 113, 113, 0.4);
}

.status-pill[data-tone='muted'] {
  opacity: 0.78;
}

.diagnostic-callout {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.72);
}

.take-card.active,
.template-preview-card {
  border-color: rgba(56, 189, 248, 0.32);
}

.take-card.status-accepted {
  border-color: rgba(74, 222, 128, 0.38);
}

.take-card.status-rejected {
  border-color: rgba(248, 113, 113, 0.32);
  opacity: 0.72;
}

.take-header-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
}

.contour-preview {
  width: 100%;
  height: 72px;
  border-radius: 14px;
  background: rgba(2, 6, 23, 0.38);
}

.contour-preview polyline {
  fill: none;
  stroke: #38bdf8;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.contour-preview.large {
  height: 110px;
}

.primary-button,
.ghost-button,
.pane-nav-button {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(30, 41, 59, 0.72);
  color: inherit;
}

.primary-button {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.82), rgba(3, 105, 161, 0.9));
}

.ghost-button.danger {
  border-color: rgba(248, 113, 113, 0.34);
}

.eyebrow {
  margin: 0 0 6px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-size: 0.72rem;
  color: rgba(148, 163, 184, 0.9);
}

.error-banner,
.empty-state {
  padding: 16px 18px;
}

@media (max-width: 1180px) {
  .shell-layout,
  .workspace-grid,
  .stats-grid,
  .toggle-grid,
  .field-grid.two-col,
  .field-grid.three-col,
  .mapping-row {
    grid-template-columns: 1fr 1fr;
  }

  .shell-header,
  .section-header.wide,
  .toolbar-row,
  .note-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .command-settings-shell {
    height: calc(100vh - 24px);
    padding: 18px;
  }

  .shell-layout,
  .stats-grid,
  .toggle-grid,
  .workspace-grid,
  .field-grid.two-col,
  .field-grid.three-col,
  .mapping-row,
  .note-row {
    grid-template-columns: 1fr;
  }

  .pane-nav {
    grid-auto-flow: column;
    grid-auto-columns: minmax(180px, 1fr);
    overflow: auto;
  }
}

.mapping-row,
.note-row {
  display: grid;
  grid-template-columns: 1fr 1.4fr 1.2fr auto auto;
  gap: 10px;
  align-items: center;
}

.notes-section .note-row {
  grid-template-columns: repeat(4, minmax(0, 1fr)) auto;
}

.field-label {
  display: grid;
  gap: 8px;
  font-size: 0.92rem;
  color: #cbd5e1;
}

.field-label.full-width,
.toggle-row.full-width {
  grid-column: 1 / -1;
}

.field-input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(15, 23, 42, 0.96);
  color: #f8fafc;
}

.toggle-row,
.inline-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ghost-button,
.primary-button {
  border-radius: 999px;
  padding: 10px 14px;
  font-weight: 600;
  cursor: pointer;
}

.ghost-button {
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(30, 41, 59, 0.78);
  color: #e2e8f0;
}

.ghost-button.danger {
  border-color: rgba(248, 113, 113, 0.34);
  color: #fecaca;
}

.primary-button {
  border: 1px solid rgba(56, 189, 248, 0.35);
  background: rgba(3, 105, 161, 0.84);
  color: #e0f2fe;
}

.eyebrow {
  margin: 0 0 6px;
  color: #38bdf8;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.subcopy {
  color: #94a3b8;
}

.error-banner,
.empty-state {
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 16px;
}

.error-banner {
  background: rgba(127, 29, 29, 0.45);
  color: #fecaca;
}

.empty-state {
  background: rgba(30, 41, 59, 0.66);
}

.compact-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.training-banner {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(15, 118, 110, 0.18);
  color: #ccfbf1;
}

.take-header-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: start;
}

.take-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 74px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(51, 65, 85, 0.9);
  color: #cbd5e1;
  text-transform: uppercase;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
}

.take-status.active {
  background: rgba(14, 116, 144, 0.28);
  color: #bae6fd;
}

.contour-preview {
  width: 100%;
  height: 58px;
  margin-top: 12px;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.76));
}

.contour-preview.large {
  height: 88px;
}

.contour-preview polyline {
  fill: none;
  stroke: #38bdf8;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.take-actions {
  margin-top: 12px;
  justify-content: flex-start;
  flex-wrap: wrap;
}

@media (max-width: 980px) {
  .settings-grid,
  .field-grid,
  .device-grid,
  .status-grid,
  .settings-header,
  .section-header,
  .mapping-row,
  .notes-section .note-row {
    grid-template-columns: 1fr;
  }

  .compact-row {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
