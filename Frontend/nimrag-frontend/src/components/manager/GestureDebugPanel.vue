<script setup lang="ts">
import type { PropType } from 'vue'
import type { GestureDebugEntry } from '../../composables/useGestureDebug'
import type { InteractionState } from '../../composables/useInteractionState'

defineProps({
  trackingStatus: { type: String, required: true },
  lastGesture: { type: String, required: true },
  lastGestureDetail: { type: String, required: true },
  lastCommand: { type: String, required: true },
  lastCommandDetail: { type: String, required: true },
  lastAction: { type: String, required: true },
  lastActionDetail: { type: String, required: true },
  lastDispatch: { type: String, required: true },
  lastDispatchDetail: { type: String, required: true },
  interactionState: { type: String as PropType<InteractionState>, required: true },
  cameraName: { type: String, required: true },
  cameraStatus: { type: String, required: true },
  entries: { type: Array as PropType<GestureDebugEntry[]>, required: true },
})
</script>

<template>
  <aside class="gesture-debug" aria-label="Gesture debug panel">
    <header class="gesture-debug__header">
      <span class="gesture-debug__title">Gesture Debug</span>
      <span class="gesture-debug__pill">live</span>
    </header>

    <dl class="gesture-debug__summary">
      <div>
        <dt>State</dt>
        <dd>{{ interactionState }}</dd>
      </div>
      <div>
        <dt>Camera</dt>
        <dd>{{ cameraName }} <span>{{ cameraStatus }}</span></dd>
      </div>
      <div>
        <dt>Tracking</dt>
        <dd>{{ trackingStatus }}</dd>
      </div>
      <div>
        <dt>Gesture</dt>
        <dd>{{ lastGesture }} <span>{{ lastGestureDetail }}</span></dd>
      </div>
      <div>
        <dt>Command</dt>
        <dd>{{ lastCommand }} <span>{{ lastCommandDetail }}</span></dd>
      </div>
      <div>
        <dt>Action</dt>
        <dd>{{ lastAction }} <span>{{ lastActionDetail }}</span></dd>
      </div>
      <div>
        <dt>Frontend</dt>
        <dd>{{ lastDispatch }} <span>{{ lastDispatchDetail }}</span></dd>
      </div>
    </dl>

    <ol class="gesture-debug__events">
      <li
        v-for="entry in entries"
        :key="entry.id"
        class="gesture-debug__event"
        :class="`gesture-debug__event--${entry.tone}`"
      >
        <span class="gesture-debug__time">{{ entry.at }}</span>
        <strong>{{ entry.type }}</strong>
        <span>{{ entry.summary }}</span>
        <small>{{ entry.detail }}</small>
      </li>
    </ol>
  </aside>
</template>

<style scoped>
.gesture-debug {
  position: fixed;
  top: 16px;
  left: 16px;
  z-index: 1400;
  width: min(420px, calc(100vw - 32px));
  max-height: calc(100vh - 32px);
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 8px;
  background: rgba(9, 12, 18, 0.86);
  color: #e5e7eb;
  box-shadow: 0 18px 52px rgba(0, 0, 0, 0.38);
  backdrop-filter: blur(12px);
  font-size: 12px;
  pointer-events: none;
}

.gesture-debug__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.gesture-debug__title {
  font-size: 13px;
  font-weight: 700;
}

.gesture-debug__pill {
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.16);
  color: #86efac;
  text-transform: uppercase;
  font-size: 10px;
  font-weight: 700;
}

.gesture-debug__summary {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 10px 12px;
}

.gesture-debug__summary div {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
}

.gesture-debug__summary dt {
  color: #94a3b8;
  font-weight: 700;
}

.gesture-debug__summary dd {
  min-width: 0;
  margin: 0;
  color: #f8fafc;
  overflow-wrap: anywhere;
}

.gesture-debug__summary dd span {
  color: #cbd5e1;
}

.gesture-debug__events {
  display: grid;
  gap: 4px;
  max-height: 280px;
  margin: 0;
  padding: 0 12px 12px;
  overflow: hidden;
  list-style: none;
}

.gesture-debug__event {
  display: grid;
  grid-template-columns: 70px 68px minmax(0, 1fr);
  gap: 6px;
  align-items: baseline;
  padding: 6px 8px;
  border-left: 3px solid rgba(148, 163, 184, 0.55);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.68);
}

.gesture-debug__event--ok {
  border-left-color: #22c55e;
}

.gesture-debug__event--warn {
  border-left-color: #f59e0b;
}

.gesture-debug__event--error {
  border-left-color: #ef4444;
}

.gesture-debug__time {
  color: #94a3b8;
}

.gesture-debug__event strong {
  color: #e2e8f0;
}

.gesture-debug__event span,
.gesture-debug__event small {
  min-width: 0;
  overflow-wrap: anywhere;
}

.gesture-debug__event small {
  grid-column: 3;
  color: #cbd5e1;
}

@media (max-width: 700px) {
  .gesture-debug {
    top: 8px;
    left: 8px;
    width: calc(100vw - 16px);
    font-size: 11px;
  }

  .gesture-debug__events {
    max-height: 180px;
  }
}
</style>
