<script setup lang="ts">
defineProps<{
  lastRawInput: string | null
  lastCommandMatch: string | null
  lastUIAction: string | null
  focusedLabel: string
  isArrangeMode: boolean
  selectedWidgetTitle: string | null
  shopVisible: boolean
  cooldownActive: boolean
  nextHint: string
}>()
</script>

<template>
  <aside class="overlay-panel">
    <div class="overlay-chip-group">
      <span class="overlay-chip">Raw: {{ lastRawInput ?? 'keine' }}</span>
      <span class="overlay-chip">Match: {{ lastCommandMatch ?? 'keine' }}</span>
      <span class="overlay-chip">Action: {{ lastUIAction ?? 'keine' }}</span>
      <span class="overlay-chip">Fokus: {{ focusedLabel }}</span>
    </div>

    <div class="overlay-grid">
      <div>
        <p class="overlay-label">ArrangeMode</p>
        <strong>{{ isArrangeMode ? 'aktiv' : 'inaktiv' }}</strong>
        <p class="overlay-copy">{{ selectedWidgetTitle ?? 'kein Widget selektiert' }}</p>
      </div>

      <div>
        <p class="overlay-label">Shop</p>
        <strong>{{ shopVisible ? 'offen' : 'geschlossen' }}</strong>
        <p class="overlay-copy">{{ cooldownActive ? 'Cooldown aktiv' : 'bereit fuer naechste Aktion' }}</p>
      </div>
    </div>

    <p class="overlay-hint">{{ nextHint }}</p>
  </aside>
</template>

<style scoped>
.overlay-panel {
  position: fixed;
  left: 24px;
  bottom: 24px;
  z-index: 1200;
  width: min(420px, calc(100vw - 32px));
  padding: 16px 18px;
  border-radius: 22px;
  background: rgba(15, 23, 42, 0.84);
  border: 1px solid rgba(248, 250, 252, 0.12);
  backdrop-filter: blur(18px);
  color: #e2e8f0;
  box-shadow: 0 18px 40px rgba(2, 6, 23, 0.4);
}

.overlay-chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.overlay-chip {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(148, 163, 184, 0.14);
  font-size: 0.8rem;
}

.overlay-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.overlay-label,
.overlay-copy,
.overlay-hint {
  margin: 0;
  font-size: 0.8rem;
  opacity: 0.76;
}

.overlay-hint {
  margin-top: 14px;
  line-height: 1.4;
}

@media (max-width: 700px) {
  .overlay-panel {
    left: 12px;
    right: 12px;
    bottom: 12px;
    width: auto;
  }

  .overlay-grid {
    grid-template-columns: 1fr;
  }
}
</style>
