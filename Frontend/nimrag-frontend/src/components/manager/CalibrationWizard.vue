<script setup lang="ts">
import { computed } from 'vue'

import type {
  CalibrationDefinitionsResponse,
  CalibrationSessionRecord,
  CalibrationTargetAnalysis,
} from '../../types/calibration'

const props = defineProps<{
  definitions: CalibrationDefinitionsResponse | null
  session: CalibrationSessionRecord | null
  loading: boolean
  busy: boolean
  error: string | null
  profileName: string
  selectedTargets: string[]
  targetRepetitions: number
  lastEventMessage: string | null
}>()

const emit = defineEmits<{
  (event: 'update:profileName', value: string): void
  (event: 'update:selectedTargets', value: string[]): void
  (event: 'update:targetRepetitions', value: number): void
  (event: 'start'): void
  (event: 'complete'): void
  (event: 'apply'): void
  (event: 'rollback'): void
  (event: 'discard'): void
  (event: 'close'): void
}>()

const gestureTargets = computed(() => props.definitions?.targets.filter((target) => target.modality === 'gesture' && target.supported) ?? [])

const currentTargetId = computed(() => props.session?.active_target_id ?? null)

const currentTarget = computed(() => gestureTargets.value.find((target) => target.id === currentTargetId.value) ?? null)

const allTargetsCompleted = computed(() => props.session?.progress.every((entry) => entry.completed) ?? false)

const analysisTargets = computed(() => props.session?.analysis?.targets ?? [])

function toggleTarget(targetId: string): void {
  const nextTargets = props.selectedTargets.includes(targetId)
    ? props.selectedTargets.filter((entry) => entry !== targetId)
    : [...props.selectedTargets, targetId]
  emit('update:selectedTargets', nextTargets)
}

function selectAllTargets(): void {
  emit('update:selectedTargets', gestureTargets.value.map((target) => target.id))
}

function clearTargets(): void {
  emit('update:selectedTargets', [])
}

function updateProfileName(event: Event): void {
  emit('update:profileName', (event.target as HTMLInputElement).value)
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
  if (status === 'collecting') {
    return 'Sammelt Samples'
  }
  if (status === 'analysis_ready') {
    return 'Analyse bereit'
  }
  if (status === 'applied') {
    return 'Profil angewendet'
  }
  if (status === 'rolled_back') {
    return 'Rueckgaengig gemacht'
  }
  return 'Verworfen'
}

function recommendationKey(analysis: CalibrationTargetAnalysis, parameter: string): string {
  return `${analysis.target_id}-${parameter}`
}
</script>

<template>
  <div class="calibration-backdrop" @click.self="emit('close')">
    <section class="calibration-modal">
      <header class="calibration-header">
        <div>
          <p class="eyebrow">In-App Calibration</p>
          <h2>Gestenprofil kalibrieren</h2>
          <p class="subcopy">Die Kalibrierung sammelt nur korrekte Live-Wiederholungen und erzeugt daraus ein anwendbares Schwellenprofil.</p>
        </div>
        <button class="ghost-button" type="button" @click="emit('close')">Schliessen</button>
      </header>

      <p v-if="error" class="error-banner">{{ error }}</p>
      <p v-if="lastEventMessage" class="event-banner">{{ lastEventMessage }}</p>

      <div v-if="loading" class="empty-state">
        <strong>Kalibrierungsziele werden geladen.</strong>
      </div>

      <template v-else-if="!session">
        <div class="wizard-grid">
          <section class="wizard-card">
            <label class="field-label" for="profile-name">Profilname</label>
            <input id="profile-name" class="field-input" :value="profileName" @input="updateProfileName" />

            <label class="field-label" for="target-repetitions">Wiederholungen pro Geste</label>
            <input id="target-repetitions" class="field-input" type="number" min="10" max="20" :value="targetRepetitions" @input="updateTargetRepetitions" />

            <div class="button-row compact">
              <button class="ghost-button" type="button" @click="selectAllTargets">Alle</button>
              <button class="ghost-button" type="button" @click="clearTargets">Keine</button>
            </div>
          </section>

          <section class="wizard-card target-card">
            <p class="field-label">Gesten-Auswahl</p>
            <label v-for="target in gestureTargets" :key="target.id" class="target-option">
              <input type="checkbox" :checked="selectedTargets.includes(target.id)" @change="toggleTarget(target.id)" />
              <span>
                <strong>{{ target.display_name }}</strong>
                <small>{{ target.description }}</small>
              </span>
            </label>
          </section>
        </div>

        <footer class="button-row">
          <button class="ghost-button" type="button" @click="emit('close')">Abbrechen</button>
          <button class="primary-button" type="button" :disabled="busy || selectedTargets.length === 0" @click="emit('start')">
            {{ busy ? 'Startet...' : 'Kalibrierung starten' }}
          </button>
        </footer>
      </template>

      <template v-else>
        <section class="session-summary">
          <div>
            <p class="eyebrow">Status</p>
            <strong>{{ statusLabel(session.status) }}</strong>
            <p class="subcopy">Profil {{ session.profile }} · {{ session.target_repetitions }} Wiederholungen pro Ziel</p>
          </div>
          <div>
            <p class="eyebrow">Aktuelles Ziel</p>
            <strong>{{ currentTarget?.display_name ?? 'Keines' }}</strong>
            <p class="subcopy">{{ currentTarget?.description ?? 'Sitzung wartet auf eine Folgeaktion.' }}</p>
          </div>
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
            <p class="progress-copy">{{ progress.last_feedback ?? 'Wartet auf Samples.' }}</p>
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

        <footer class="button-row">
          <button v-if="session.status === 'collecting' || session.status === 'analysis_ready'" class="ghost-button" type="button" :disabled="busy" @click="emit('discard')">
            Verwerfen
          </button>
          <button v-if="session.status === 'collecting'" class="primary-button" type="button" :disabled="busy || !allTargetsCompleted" @click="emit('complete')">
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
  width: min(1040px, 100%);
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
.session-summary,
.button-row,
.wizard-grid,
.progress-grid,
.metric-grid {
  display: grid;
  gap: 16px;
}

.calibration-header,
.session-summary,
.button-row {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
}

.wizard-grid {
  grid-template-columns: 0.9fr 1.1fr;
  margin: 24px 0;
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
.session-summary > div {
  padding: 18px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.18);
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

.target-card {
  display: grid;
  gap: 12px;
}

.target-option {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;
}

.target-option small,
.progress-copy,
.subcopy,
.event-banner,
.error-banner,
.recommendation-card small,
.metric-card small {
  color: rgba(226, 232, 240, 0.78);
}

.field-label,
.eyebrow {
  margin: 0 0 6px;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.9);
}

.field-input {
  width: 100%;
  margin-bottom: 14px;
  padding: 11px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: rgba(15, 23, 42, 0.92);
  color: #f8fafc;
}

.button-row {
  margin-top: 24px;
}

.button-row.compact {
  display: flex;
  gap: 10px;
}

.primary-button,
.ghost-button {
  border-radius: 999px;
  padding: 11px 18px;
  border: 1px solid transparent;
  font-weight: 600;
  cursor: pointer;
}

.primary-button {
  justify-self: end;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #111827;
}

.ghost-button {
  justify-self: start;
  background: rgba(51, 65, 85, 0.55);
  border-color: rgba(148, 163, 184, 0.18);
  color: #f8fafc;
}

.primary-button:disabled,
.ghost-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.empty-state,
.event-banner,
.error-banner {
  padding: 14px 16px;
  border-radius: 16px;
  margin-top: 18px;
}

.event-banner {
  background: rgba(15, 118, 110, 0.24);
}

.error-banner {
  background: rgba(153, 27, 27, 0.34);
}

.recommendation-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

@media (max-width: 900px) {
  .calibration-header,
  .session-summary,
  .wizard-grid,
  .button-row {
    grid-template-columns: 1fr;
  }

  .primary-button,
  .ghost-button {
    justify-self: stretch;
  }
}
</style>