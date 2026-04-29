<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

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

type TrainingTakeStatus = 'pending' | 'accepted' | 'rejected'

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

const commandProfilesDraft = ref<CommandProfilesConfig | null>(null)
const musicalAudioConfigDraft = ref<MusicalAudioConfig | null>(null)
const artifactDraft = ref<MusicalAudioTrainingArtifact | null>(null)
const selectedArtifactId = ref<string | null>(null)
const trainingTakes = ref<TrainingTakeRecord[]>([])
const selectedTakeId = ref<string | null>(null)
const trainingState = ref<'idle' | 'recording' | 'processing'>('idle')
const trainingMessage = ref<string | null>(null)
const recordingElapsedSeconds = ref(0)

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

watch(
  () => props.artifacts,
  (value) => {
    if (value.length === 0) {
      const activeProfileId = commandProfilesDraft.value?.active_profile_id ?? 'default'
      artifactDraft.value = buildDefaultArtifact(activeProfileId)
      selectedArtifactId.value = artifactDraft.value.artifact_id
      trainingTakes.value = []
      selectedTakeId.value = null
      trainingMessage.value = null
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
    trainingMessage.value = null
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

const artifactOptions = computed(() => props.artifacts.map((artifact) => ({
  label: artifact.display_name,
  value: artifact.artifact_id,
})))

const selectedTake = computed(() => trainingTakes.value.find((take) => take.takeId === selectedTakeId.value) ?? null)

const acceptedTrainingTakes = computed(() => trainingTakes.value.filter((take) => take.status === 'accepted'))

const activeArtifactId = computed(() => activeProfile.value?.modality_settings.musical_audio.active_training_artifact_id ?? null)

const derivedTemplatePreview = computed(() => buildContourPolyline(artifactDraft.value?.notes ?? []))

const trainingSummary = computed(() => {
  const accepted = acceptedTrainingTakes.value.length
  const total = trainingTakes.value.length
  if (accepted >= 10 && accepted <= 20) {
    return `${accepted}/${total} freigegeben, bereit fuer Few-Shot-Aktivierung`
  }
  return `${accepted}/${total} freigegeben, Zielbereich 10-20 Takes`
})

function updateMappingField(index: number, field: 'input_source' | 'raw_input' | 'action', value: string): void {
  if (!activeProfile.value) {
    return
  }

  const mapping = activeProfile.value.input_action_config.mappings[index]
  if (!mapping) {
    return
  }

  activeProfile.value.input_action_config.mappings[index] = {
    ...mapping,
    [field]: value,
  }
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
  if (!activeProfile.value) {
    return
  }
  activeProfile.value.input_action_config.mappings.splice(index, 1)
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
  artifactDraft.value = artifact ? clone(artifact) : null
  trainingTakes.value = []
  selectedTakeId.value = null
  trainingMessage.value = null
}

function createArtifact(): void {
  const profileId = commandProfilesDraft.value?.active_profile_id ?? 'default'
  const nextArtifact = buildDefaultArtifact(profileId)
  selectedArtifactId.value = nextArtifact.artifact_id
  artifactDraft.value = nextArtifact
  trainingTakes.value = []
  selectedTakeId.value = null
  trainingMessage.value = null
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
  if (!artifactDraft.value || !activeProfile.value || !musicalAudioConfigDraft.value) {
    return
  }

  activeProfile.value.modality_settings.musical_audio = {
    ...activeProfile.value.modality_settings.musical_audio,
    active_training_artifact_id: artifactDraft.value.artifact_id,
  }
  musicalAudioConfigDraft.value.active_artifact_id = artifactDraft.value.artifact_id
  trainingMessage.value = `${artifactDraft.value.display_name} als aktives Template markiert.`
}

function addNote(): void {
  if (!artifactDraft.value) {
    return
  }
  const lastNote = artifactDraft.value.notes[artifactDraft.value.notes.length - 1]
  const nextTime = artifactDraft.value.notes.length === 0
    ? 0
    : ((lastNote?.relative_time_seconds ?? 0) + 0.3)
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
  artifactDraft.value.notes[index] = {
    ...currentNote,
    ...patch,
  }
}

function clearRecordingSession(session: RecordingSession): void {
  window.clearInterval(session.sampleTimerId)
  window.clearTimeout(session.timeoutId)
  session.stream.getTracks().forEach((track) => track.stop())
  void session.audioContext.close().catch(() => undefined)
}

async function startTrainingRecording(): Promise<void> {
  if (trainingState.value === 'recording') {
    return
  }

  if (!artifactDraft.value || !musicalAudioConfigDraft.value) {
    trainingMessage.value = 'Waehle zuerst ein Artefakt aus.'
    return
  }

  if (!navigator.mediaDevices?.getUserMedia || typeof window.AudioContext === 'undefined') {
    trainingMessage.value = 'Browser-Mikrofonzugriff ist in dieser Umgebung nicht verfuegbar.'
    return
  }

  trainingMessage.value = null

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      },
    })
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
  } catch (error) {
    trainingMessage.value = error instanceof Error ? error.message : 'Mikrofonaufnahme konnte nicht gestartet werden.'
    trainingState.value = 'idle'
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
    trainingState.value = 'idle'
    trainingMessage.value = `Zu wenig stabile Noten erkannt (${extractedNotes.length}). Bitte deutlicher pfeifen oder erneut aufnehmen.`
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
  trainingState.value = 'idle'
  trainingMessage.value = `${nextTake.label} analysiert. Kontur pruefen und freigeben oder verwerfen.`
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
  trainingMessage.value = `${take.label} als aktueller Kontur-Entwurf uebernommen.`
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
  trainingMessage.value = `${accepted.length} freigegebene Takes zu einem Template verdichtet.`
}

function isTakeActive(takeId: string): boolean {
  return selectedTakeId.value === takeId
}

onBeforeUnmount(() => {
  if (recordingSession) {
    clearRecordingSession(recordingSession)
    recordingSession = null
  }
})
</script>

<template>
  <div class="command-settings-backdrop" @click.self="emit('close')">
    <section class="command-settings-modal">
      <header class="settings-header">
        <div>
          <p class="eyebrow">Command Config</p>
          <h2>Modale Eingaben und Musical Audio</h2>
          <p class="subcopy">Gemeinsame Profile, Geraete-Praeferenzen, Mappings und musikalische Command-Artefakte.</p>
        </div>
        <button class="ghost-button" type="button" @click="emit('close')">Schliessen</button>
      </header>

      <p v-if="error" class="error-banner">{{ error }}</p>
      <div v-if="loading || !commandProfilesDraft || !musicalAudioConfigDraft" class="empty-state">
        <strong>Command Settings werden geladen.</strong>
      </div>

      <template v-else>
        <section class="settings-grid">
          <article class="settings-card">
            <div class="section-header">
              <div>
                <p class="eyebrow">Aktives Profil</p>
                <strong>{{ activeProfile?.display_name ?? 'n/a' }}</strong>
              </div>
              <button class="primary-button" type="button" :disabled="saving" @click="saveCommandProfiles">
                {{ saving ? 'Speichert...' : 'Profil speichern' }}
              </button>
            </div>

            <div v-if="activeProfile" class="field-grid">
              <label class="field-label">
                Anzeigename
                <input v-model="activeProfile.display_name" class="field-input" />
              </label>
              <label class="field-label full-width">
                Beschreibung
                <input v-model="activeProfile.description" class="field-input" />
              </label>
            </div>

            <div v-if="activeProfile" class="device-grid">
              <label class="toggle-row">
                <span>Gesten aktiviert</span>
                <input type="checkbox" :checked="activeProfile.modality_settings.gesture.enabled" @change="updateModalityEnabled('gesture', ($event.target as HTMLInputElement).checked)" />
              </label>
              <label class="toggle-row">
                <span>Voice aktiviert</span>
                <input type="checkbox" :checked="activeProfile.modality_settings.voice.enabled" @change="updateModalityEnabled('voice', ($event.target as HTMLInputElement).checked)" />
              </label>
              <label class="toggle-row">
                <span>Musical Audio aktiviert</span>
                <input type="checkbox" :checked="activeProfile.modality_settings.musical_audio.enabled" @change="updateModalityEnabled('musical_audio', ($event.target as HTMLInputElement).checked)" />
              </label>

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
                Musical Audio Geraet
                <select class="field-input" :value="activeProfile.device_preferences.musical_audio_device_index ?? ''" @change="handleDevicePreferenceChange('musical_audio_device_index', $event)">
                  <option value="">Automatisch</option>
                  <option v-for="device in musicalAudioDevices" :key="device.index" :value="device.index">{{ device.name }}</option>
                </select>
              </label>
            </div>
          </article>

          <article class="settings-card">
            <div class="section-header compact">
              <div>
                <p class="eyebrow">Gemeinsame Mappings</p>
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

        <section class="settings-grid lower">
          <article class="settings-card">
            <div class="section-header compact">
              <div>
                <p class="eyebrow">Musical Audio Runtime</p>
                <strong>{{ musicalAudioStatus?.running ? 'Laeuft' : 'Gestoppt' }}</strong>
              </div>
              <div class="button-row compact-row">
                <button class="ghost-button" type="button" :disabled="saving" @click="saveMusicalAudioConfig">Runtime speichern</button>
                <button class="ghost-button" type="button" :disabled="saving" @click="emit('start-musical-audio', musicalAudioConfigDraft.device_index)">Start</button>
                <button class="ghost-button" type="button" :disabled="saving" @click="emit('stop-musical-audio')">Stop</button>
              </div>
            </div>

            <div class="field-grid">
              <label class="toggle-row full-width">
                <span>Modul aktiviert</span>
                <input v-model="musicalAudioConfigDraft.enabled" type="checkbox" />
              </label>
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

            <div class="status-grid">
              <div><strong>Artefakte geladen:</strong> {{ musicalAudioStatus?.artifacts_loaded ?? 0 }}</div>
              <div><strong>Letztes Match:</strong> {{ musicalAudioStatus?.last_match ?? 'n/a' }}</div>
              <div><strong>Letzte Pitch-Hz:</strong> {{ musicalAudioStatus?.last_pitch_hz ?? 'n/a' }}</div>
              <div><strong>Letzter Fehler:</strong> {{ musicalAudioStatus?.last_error ?? 'kein Fehler' }}</div>
            </div>
          </article>

          <article class="settings-card">
            <div class="section-header compact">
              <div>
                <p class="eyebrow">Musical Audio Artefakte</p>
                <strong>{{ artifactDraft?.display_name ?? 'Neues Artefakt' }}</strong>
              </div>
              <div class="button-row compact-row">
                <button class="ghost-button" type="button" @click="createArtifact">Neu</button>
                <button class="ghost-button" type="button" :disabled="!artifactDraft" @click="saveArtifact">Artefakt speichern</button>
                <button class="ghost-button danger" type="button" :disabled="!artifactDraft" @click="deleteArtifact">Loeschen</button>
              </div>
            </div>

            <label class="field-label">
              Artefakt
              <select class="field-input" :value="selectedArtifactId ?? ''" @change="selectArtifact(($event.target as HTMLSelectElement).value)">
                <option v-for="option in artifactOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </label>

            <div v-if="artifactDraft" class="field-grid">
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

            <div v-if="artifactDraft" class="training-section">
              <div class="section-header compact">
                <div>
                  <p class="eyebrow">Training Flow</p>
                  <strong>{{ trainingSummary }}</strong>
                  <p class="subcopy">Nimm 10-20 Takes auf, pruefe die Konturen und leite daraus ein aktives Few-Shot-Template ab.</p>
                </div>
                <div class="button-row compact-row">
                  <button
                    class="ghost-button"
                    type="button"
                    :disabled="trainingState === 'processing'"
                    @click="trainingState === 'recording' ? stopTrainingRecording() : startTrainingRecording()"
                  >
                    {{ trainingState === 'recording' ? 'Aufnahme stoppen' : 'Take aufnehmen' }}
                  </button>
                  <button class="ghost-button" type="button" :disabled="acceptedTrainingTakes.length === 0" @click="applyAcceptedTrainingTakes">
                    Freigegebene Takes verdichten
                  </button>
                  <button class="ghost-button" type="button" :disabled="!artifactDraft" @click="activateArtifactDraft">
                    Als aktiv markieren
                  </button>
                </div>
              </div>

              <div class="status-grid training-meta">
                <div><strong>Aktives Artefakt:</strong> {{ activeArtifactId ?? 'keins' }}</div>
                <div><strong>Ausgewaehlter Take:</strong> {{ selectedTake?.label ?? 'keiner' }}</div>
                <div><strong>Recording-Status:</strong> {{ trainingState === 'recording' ? `Laeuft ${recordingElapsedSeconds.toFixed(1)}s` : trainingState === 'processing' ? 'Analyse laeuft' : 'Bereit' }}</div>
                <div><strong>Template-Vorschau:</strong> {{ artifactDraft.notes.length }} Noten</div>
              </div>

              <p v-if="trainingMessage" class="training-banner">{{ trainingMessage }}</p>

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
                    <span class="take-status">{{ take.status }}</span>
                  </div>
                  <svg class="contour-preview" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">
                    <polyline :points="buildContourPolyline(take.notes)" />
                  </svg>
                  <div class="button-row compact-row take-actions">
                    <button class="ghost-button" type="button" @click="setTakeStatus(take.takeId, 'accepted')">Freigeben</button>
                    <button class="ghost-button" type="button" @click="setTakeStatus(take.takeId, 'rejected')">Verwerfen</button>
                    <button class="ghost-button" type="button" @click="setTakeStatus(take.takeId, 'pending')">Zurueckstellen</button>
                    <button class="ghost-button" type="button" @click="loadTakeIntoArtifact(take.takeId)">Als Entwurf laden</button>
                    <button class="ghost-button danger" type="button" @click="removeTrainingTake(take.takeId)">Entfernen</button>
                  </div>
                </article>
              </div>

              <div class="template-preview-card">
                <div class="section-header compact">
                  <div>
                    <p class="eyebrow">Template Preview</p>
                    <strong>{{ artifactDraft.display_name }}</strong>
                  </div>
                  <span class="take-status" :class="{ active: activeArtifactId === artifactDraft.artifact_id }">
                    {{ activeArtifactId === artifactDraft.artifact_id ? 'aktiv' : 'inaktiv' }}
                  </span>
                </div>
                <svg class="contour-preview large" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">
                  <polyline :points="derivedTemplatePreview" />
                </svg>
              </div>
            </div>

            <div v-if="artifactDraft" class="notes-section">
              <div class="section-header compact">
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
          </article>
        </section>
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
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(56, 189, 248, 0.16), transparent 30%),
    radial-gradient(circle at bottom right, rgba(248, 113, 113, 0.14), transparent 24%),
    rgba(10, 14, 23, 0.8);
  backdrop-filter: blur(18px);
}

.command-settings-modal {
  width: min(1200px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  padding: 28px;
  border-radius: 28px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: linear-gradient(180deg, rgba(17, 24, 39, 0.98), rgba(15, 23, 42, 0.96));
  color: #f8fafc;
  box-shadow: 0 30px 80px rgba(2, 6, 23, 0.48);
}

.settings-header,
.section-header,
.button-row,
.settings-grid,
.field-grid,
.device-grid,
.status-grid {
  display: grid;
  gap: 16px;
}

.settings-header,
.section-header {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
}

.settings-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 22px;
}

.settings-grid.lower {
  margin-top: 18px;
}

.field-grid,
.device-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 18px;
}

.status-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 18px;
}

.settings-card,
.note-row,
.take-card,
.template-preview-card {
  padding: 18px;
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.74);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.mapping-list,
.notes-section,
.training-section,
.take-list {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.training-section {
  margin-top: 22px;
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
