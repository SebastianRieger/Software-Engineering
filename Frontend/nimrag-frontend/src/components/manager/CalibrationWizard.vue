<script setup lang="ts">
import { computed } from 'vue'

import type {
  CalibrationDefinitionsResponse,
  CalibrationSessionRecord,
  CalibrationTargetAnalysis,
} from '../../types/calibration'
import type { GestureCameraDevice, GestureStatusResponse } from '../../types/hardware'

const props = defineProps<{
  definitions: CalibrationDefinitionsResponse | null
  session: CalibrationSessionRecord | null
  loading: boolean
  busy: boolean
  error: string | null
  profileName: string
  gestureDevices: GestureCameraDevice[]
  gestureStatus: GestureStatusResponse | null
  previewImage: string | null
  previewState: 'warming_up' | 'live' | 'stale' | 'unavailable' | 'error'
  previewMessage: string | null
  countdownSeconds: number | null
  cameraIndex: number
  selectedTargets: string[]
  targetRepetitions: number
  lastEventMessage: string | null
}>()

const emit = defineEmits<{
  (event: 'update:profileName', value: string): void
  (event: 'update:cameraIndex', value: number): void
  (event: 'update:selectedTargets', value: string[]): void
  (event: 'update:targetRepetitions', value: number): void
  (event: 'start'): void
  (event: 'prepare-take'): void
  (event: 'start-take'): void
  (event: 'stop-take'): void
  (event: 'accept-take'): void
  (event: 'discard-take'): void
  (event: 'complete'): void
  (event: 'apply'): void
  (event: 'rollback'): void
  (event: 'discard'): void
  (event: 'close'): void
}>()

const gestureTargets = computed(() => props.definitions?.targets.filter((target) => target.modality === 'gesture' && target.supported) ?? [])
const activeTake = computed(() => props.session?.active_take ?? null)
const pendingTake = computed(() => props.session?.pending_take ?? null)
const currentTargetId = computed(() => activeTake.value?.target_id ?? pendingTake.value?.target_id ?? props.session?.active_target_id ?? null)
const currentTarget = computed(() => gestureTargets.value.find((target) => target.id === currentTargetId.value) ?? null)
const allTargetsCompleted = computed(() => props.session?.progress.every((entry) => entry.completed) ?? false)
const analysisTargets = computed(() => props.session?.analysis?.targets ?? [])

function toggleTarget(targetId: string): void {
  const nextTargets = new Set(props.selectedTargets)
  if (nextTargets.has(targetId)) {
    nextTargets.delete(targetId)
  } else {
    nextTargets.add(targetId)
  }

  emit(
    'update:selectedTargets',
    gestureTargets.value
      .map((target) => target.id)
      .filter((candidateId) => nextTargets.has(candidateId)),
  )
}

function updateProfileName(event: Event): void {
  emit('update:profileName', (event.target as HTMLInputElement).value)
}

function updateCameraIndex(event: Event): void {
  emit('update:cameraIndex', Number((event.target as HTMLSelectElement).value))
}

function updateTargetRepetitions(event: Event): void {
  emit('update:targetRepetitions', Number((event.target as HTMLInputElement).value))
}

function formatMetricValue(value: number | null): string {
  if (value === null) {
    return 'n/a'
  }
  return value.toFixed(3)
}

function formatTargetTitle(targetId: string): string {
  return gestureTargets.value.find((target) => target.id === targetId)?.display_name ?? targetId
}

function statusLabel(status: CalibrationSessionRecord['status']): string {
  if (status === 'collecting') return 'Guided Collection'
  if (status === 'analysis_ready') return 'Analyse bereit'
  if (status === 'applied') return 'Profil angewendet'
  if (status === 'rolled_back') return 'Rueckgaengig gemacht'
  return 'Verworfen'
}

function previewStateLabel(state: typeof props.previewState): string {
  if (state === 'live') return 'Live'
  if (state === 'stale') return 'Stale'
  if (state === 'unavailable') return 'Unavailable'
  if (state === 'error') return 'Error'
  return 'Warming up'
}

function recommendationKey(analysis: CalibrationTargetAnalysis, parameter: string): string {
  return `${analysis.target_id}-${parameter}`
}

const canManuallyStartTake = computed(() => {
  return activeTake.value?.status === 'prepared' && (props.countdownSeconds ?? activeTake.value.countdown_seconds) <= 0
})
</script>

<template>
  <div class="calibration-backdrop" @click.self="emit('close')">
    <section class="calibration-modal">
      <header class="calibration-header">
        <div>
          <p class="eyebrow">In-App Calibration</p>
          <h2>Guided Source-of-Truth Kalibrierung</h2>
          <p class="subcopy">Prompt, Countdown, Recording, Review. Die Nutzerauswahl ist die Source of Truth, nicht das alte Erkennungslabel.</p>
        </div>
        <button class="ghost-button" type="button" @click="emit('close')">Schliessen</button>
      </header>

      <p v-if="error" class="error-banner">{{ error }}</p>
      <p v-if="lastEventMessage" class="event-banner">{{ lastEventMessage }}</p>

      <div v-if="loading" class="empty-state">
        <strong>Kalibrierungsziele werden geladen.</strong>
      </div>

      <template v-else-if="!session">
        <div class="wizard-grid setup-grid">
          <section class="wizard-card">
            <label class="field-label" for="profile-name">Profilname</label>
            <input id="profile-name" class="field-input" :value="profileName" @input="updateProfileName" />

            <label class="field-label" for="camera-index">Kamera</label>
            <select id="camera-index" class="field-input" :value="cameraIndex" @change="updateCameraIndex">
              <option v-if="gestureDevices.length === 0" :value="cameraIndex">Keine Kamera gefunden</option>
              <option v-for="device in gestureDevices" :key="device.index" :value="device.index">
                {{ device.name }}
              </option>
            </select>

            <label class="field-label" for="target-repetitions">Wiederholungen pro Geste</label>
            <input id="target-repetitions" class="field-input" type="number" min="4" max="20" :value="targetRepetitions" @input="updateTargetRepetitions" />
            <p class="subcopy">Mehrere Gesten pro Sitzung sind erlaubt. Ein neuer Take startet aber nur mit frischer Vorschau.</p>
          </section>

          <section class="wizard-card target-card">
            <p class="field-label">Gesten auswaehlen</p>
            <label v-for="target in gestureTargets" :key="target.id" class="target-option">
              <input type="checkbox" :checked="selectedTargets.includes(target.id)" @change="toggleTarget(target.id)" />
              <span>
                <strong>{{ target.display_name }}</strong>
                <small>{{ target.description }}</small>
              </span>
            </label>
          </section>

          <section class="wizard-card preview-card">
            <div class="preview-card-header">
              <div>
                <p class="field-label">Live-Vorschau</p>
                <strong>{{ gestureStatus?.camera_name ?? 'Kamera wird vorbereitet' }}</strong>
              </div>
              <span class="preview-pill" :class="`preview-pill--${previewState}`">{{ previewStateLabel(previewState) }}</span>
            </div>
            <div class="preview-frame">
              <img v-if="previewImage" :src="previewImage" alt="Kalibrierungs-Vorschau" />
              <div v-else class="preview-empty">Noch kein frischer Kameraframe.</div>
            </div>
            <p class="subcopy">{{ previewMessage ?? 'Pruefe hier, ob die Kamera wirklich ein brauchbares Bild liefert und nicht nur als Linux-Device auftaucht.' }}</p>
          </section>
        </div>

        <footer class="button-row">
          <button class="ghost-button" type="button" @click="emit('close')">Abbrechen</button>
          <button class="primary-button" type="button" :disabled="busy || selectedTargets.length === 0 || previewState !== 'live'" @click="emit('start')">
            {{ busy ? 'Startet...' : 'Kalibrierung starten' }}
          </button>
        </footer>
      </template>

      <template v-else>
        <section class="summary-grid">
          <div>
            <p class="eyebrow">Status</p>
            <strong>{{ statusLabel(session.status) }}</strong>
            <p class="subcopy">Profil {{ session.profile }} · {{ session.target_repetitions }} akzeptierte Takes pro Ziel</p>
          </div>
          <div>
            <p class="eyebrow">Aktueller Prompt</p>
            <strong>{{ currentTarget?.display_name ?? 'Kein aktiver Prompt' }}</strong>
            <p class="subcopy">{{ currentTarget?.description ?? 'Sitzung wartet auf den naechsten Take.' }}</p>
          </div>
          <div>
            <p class="eyebrow">Preview</p>
            <strong>{{ previewStateLabel(previewState) }}</strong>
            <p class="subcopy">{{ previewMessage ?? 'Vorschau ist live.' }}</p>
          </div>
        </section>

        <section class="wizard-grid live-grid">
          <section class="wizard-card take-card">
            <p class="field-label">Take-Steuerung</p>
            <strong class="prompt-title">{{ currentTarget?.display_name ?? 'Noch kein Ziel vorbereitet' }}</strong>
            <p class="subcopy" v-if="activeTake?.status === 'prepared'">Countdown laeuft lokal. Recording startet automatisch bei 0.</p>
            <p class="subcopy" v-else-if="activeTake?.status === 'recording'">Recording ist aktiv. Fuehre die Geste aus und stoppe manuell.</p>
            <p class="subcopy" v-else-if="pendingTake">Review den letzten Take und akzeptiere oder verwerfe ihn.</p>
            <p class="subcopy" v-else>Bereite den naechsten Take vor, sobald die Vorschau live ist.</p>

            <div v-if="activeTake?.status === 'prepared'" class="countdown-box">
              <span class="countdown-label">Countdown</span>
              <strong>{{ countdownSeconds ?? activeTake.countdown_seconds }}</strong>
            </div>

            <div v-if="activeTake?.status === 'recording'" class="recording-indicator">
              <span class="recording-dot"></span>
              Recording aktiv
            </div>

            <div v-if="pendingTake" class="review-box">
              <p class="field-label">Review</p>
              <strong>{{ formatTargetTitle(pendingTake.target_id) }}</strong>
              <small>
                Advisory recognition:
                {{ pendingTake.advisory_recognition?.recognized_target_id ? formatTargetTitle(pendingTake.advisory_recognition.recognized_target_id) : 'keine Erkennung' }}
              </small>
            </div>
          </section>

          <section class="wizard-card preview-card">
            <div class="preview-card-header">
              <div>
                <p class="field-label">Kamerafenster</p>
                <strong>{{ gestureStatus?.camera_name ?? 'Kamera unbekannt' }}</strong>
              </div>
              <span class="preview-pill" :class="`preview-pill--${previewState}`">{{ previewStateLabel(previewState) }}</span>
            </div>
            <div class="preview-frame preview-frame--large">
              <img v-if="previewImage" :src="previewImage" alt="Kalibrierungs-Vorschau" />
              <div v-else class="preview-empty">Noch kein Kamerabild verfuegbar.</div>
            </div>
            <p class="subcopy">{{ previewMessage ?? 'Das Live-Bild ist die direkte Sichtkontrolle fuer Schwarzbild-, Treiber- und Frischeprobleme.' }}</p>
          </section>
        </section>

        <section class="progress-grid">
          <article
            v-for="progress in session.progress"
            :key="progress.target_id"
            class="progress-card"
            :class="{ active: progress.target_id === currentTargetId, completed: progress.completed }"
          >
            <p class="field-label">{{ formatTargetTitle(progress.target_id) }}</p>
            <strong>{{ progress.collected_samples }} / {{ progress.target_repetitions }}</strong>
            <p class="progress-copy">{{ progress.last_feedback ?? 'Wartet auf akzeptierte Takes.' }}</p>
            <small>Rejects: {{ progress.rejected_samples }} · Mittelwert Konfidenz: {{ (progress.quality_metrics.mean_confidence ?? 0).toFixed(2) }}</small>
          </article>
        </section>

        <section v-if="session.status === 'analysis_ready' || session.status === 'applied' || session.status === 'rolled_back'" class="analysis-section">
          <h3>Empfehlungen</h3>
          <p class="subcopy">{{ session.analysis?.summary ?? 'Keine Analyse verfuegbar.' }}</p>
          <article v-for="analysis in analysisTargets" :key="analysis.target_id" class="analysis-card">
            <header>
              <strong>{{ formatTargetTitle(analysis.target_id) }}</strong>
              <small>{{ analysis.sample_count }} Samples</small>
            </header>

            <div class="metric-grid">
              <div v-for="metric in analysis.metrics" :key="metric.name" class="metric-card">
                <p class="field-label">{{ metric.name }}</p>
                <strong>{{ formatMetricValue(metric.mean_value) }}</strong>
                <small>P10 {{ formatMetricValue(metric.p10_value) }} · P90 {{ formatMetricValue(metric.p90_value) }}</small>
              </div>
            </div>

            <div class="recommendation-list">
              <div v-for="recommendation in analysis.recommendations" :key="recommendationKey(analysis, recommendation.parameter)" class="recommendation-card">
                <strong>{{ recommendation.parameter }}</strong>
                <p>{{ recommendation.current_value.toFixed(3) }} → {{ recommendation.recommended_value.toFixed(3) }}</p>
                <small>{{ recommendation.rationale }}</small>
              </div>
            </div>
          </article>
        </section>

        <footer class="button-row button-row--stacked">
          <button v-if="session.status === 'collecting' && !activeTake && !pendingTake" class="primary-button" type="button" :disabled="busy || previewState !== 'live'" @click="emit('prepare-take')">
            {{ busy ? 'Bereitet vor...' : 'Naechsten Take vorbereiten' }}
          </button>
          <button v-if="canManuallyStartTake" class="primary-button" type="button" :disabled="busy || previewState !== 'live'" @click="emit('start-take')">
            {{ busy ? 'Startet...' : 'Recording jetzt starten' }}
          </button>
          <button v-if="activeTake?.status === 'recording'" class="primary-button" type="button" :disabled="busy" @click="emit('stop-take')">
            {{ busy ? 'Stoppt...' : 'Recording stoppen' }}
          </button>
          <button v-if="pendingTake" class="ghost-button" type="button" :disabled="busy" @click="emit('discard-take')">
            Take verwerfen
          </button>
          <button v-if="pendingTake" class="primary-button" type="button" :disabled="busy" @click="emit('accept-take')">
            Take akzeptieren
          </button>
          <button v-if="session.status === 'collecting' || session.status === 'analysis_ready'" class="ghost-button" type="button" :disabled="busy" @click="emit('discard')">
            Sitzung verwerfen
          </button>
          <button v-if="session.status === 'collecting'" class="primary-button" type="button" :disabled="busy || !allTargetsCompleted || !!activeTake || !!pendingTake" @click="emit('complete')">
            {{ busy ? 'Analysiert...' : 'Analyse erzeugen' }}
          </button>
          <button v-if="session.status === 'analysis_ready'" class="ghost-button" type="button" :disabled="busy" @click="emit('apply')">
            {{ busy ? 'Wendet an...' : 'Profil anwenden' }}
          </button>
          <button v-if="session.status === 'applied'" class="ghost-button" type="button" :disabled="busy" @click="emit('rollback')">
            {{ busy ? 'Rollback...' : 'Rueckgaengig machen' }}
          </button>
          <button v-if="session.status === 'rolled_back' || session.status === 'cancelled'" class="ghost-button" type="button" @click="emit('close')">
            Schliessen
          </button>
        </footer>
      </template>
    </section>
  </div>
</template>

<style scoped>
.calibration-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.16), transparent 32%),
    radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.14), transparent 28%),
    rgba(10, 14, 23, 0.78);
  backdrop-filter: blur(16px);
}

.calibration-modal {
  width: min(1120px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  padding: 28px;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: linear-gradient(180deg, rgba(17, 24, 39, 0.98), rgba(10, 14, 23, 0.96));
  color: #f8fafc;
  box-shadow: 0 26px 80px rgba(2, 6, 23, 0.42);
}

.calibration-header,
.wizard-grid,
.button-row,
.progress-grid,
.metric-grid,
.summary-grid {
  display: grid;
  gap: 16px;
}

.calibration-header,
.button-row {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
}

.setup-grid {
  grid-template-columns: 0.8fr 1fr 1fr;
  margin: 24px 0;
}

.live-grid {
  grid-template-columns: 0.85fr 1.15fr;
  margin: 24px 0;
}

.summary-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 24px;
}

.progress-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin: 24px 0;
}

.metric-grid {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  margin-top: 14px;
}

.wizard-card,
.progress-card,
.analysis-card,
.metric-card,
.recommendation-card,
.summary-grid > div {
  padding: 18px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.preview-card,
.take-card,
.target-card {
  display: grid;
  gap: 12px;
}

.preview-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.preview-frame {
  min-height: 210px;
  border-radius: 18px;
  overflow: hidden;
  background: rgba(2, 6, 23, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.preview-frame--large {
  min-height: 320px;
}

.preview-frame img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-empty {
  display: grid;
  place-items: center;
  min-height: inherit;
  color: rgba(226, 232, 240, 0.72);
  text-align: center;
  padding: 20px;
}

.preview-pill {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.preview-pill--live {
  background: rgba(16, 185, 129, 0.16);
  color: #6ee7b7;
}

.preview-pill--warming_up,
.preview-pill--stale {
  background: rgba(251, 191, 36, 0.16);
  color: #fcd34d;
}

.preview-pill--unavailable,
.preview-pill--error {
  background: rgba(248, 113, 113, 0.16);
  color: #fca5a5;
}

.countdown-box,
.review-box,
.recording-indicator {
  padding: 14px;
  border-radius: 16px;
  background: rgba(2, 6, 23, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.countdown-box strong {
  display: block;
  font-size: 40px;
  line-height: 1;
  margin-top: 6px;
}

.recording-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fca5a5;
}

.recording-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: #ef4444;
  box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.16);
}

.prompt-title {
  font-size: 24px;
}

.progress-card.active {
  border-color: rgba(251, 191, 36, 0.78);
  box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.18);
}

.progress-card.completed {
  border-color: rgba(16, 185, 129, 0.7);
}

.analysis-section {
  margin-top: 24px;
}

.analysis-card + .analysis-card {
  margin-top: 16px;
}

.target-option {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(2, 6, 23, 0.42);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.field-label,
.eyebrow,
.countdown-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(226, 232, 240, 0.72);
}

.subcopy,
.progress-copy,
.target-option small,
.recommendation-card small,
.analysis-card small,
.review-box small {
  color: rgba(226, 232, 240, 0.72);
}

.field-input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(2, 6, 23, 0.62);
  color: inherit;
  margin-bottom: 14px;
}

.button-row {
  margin-top: 24px;
}

.button-row--stacked {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.primary-button,
.ghost-button {
  border: none;
  border-radius: 14px;
  padding: 14px 18px;
  font-weight: 700;
  cursor: pointer;
}

.primary-button {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #1f2937;
}

.primary-button:disabled,
.ghost-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ghost-button {
  background: rgba(148, 163, 184, 0.14);
  color: #f8fafc;
}

.error-banner,
.event-banner {
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 16px;
}

.error-banner {
  background: rgba(248, 113, 113, 0.14);
  border: 1px solid rgba(248, 113, 113, 0.28);
}

.event-banner {
  background: rgba(59, 130, 246, 0.16);
  border: 1px solid rgba(96, 165, 250, 0.24);
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 240px;
  text-align: center;
}

@media (max-width: 900px) {
  .setup-grid,
  .live-grid,
  .summary-grid,
  .button-row {
    grid-template-columns: 1fr;
  }

  .calibration-modal {
    padding: 20px;
  }
}
</style>
