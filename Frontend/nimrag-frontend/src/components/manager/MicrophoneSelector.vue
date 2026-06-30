<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useMicrophoneSelection } from '../../composables/useMicrophoneSelection'

const isOpen = ref(false)
let statusInterval: ReturnType<typeof window.setInterval> | null = null

const {
  devices,
  activeDeviceIndex,
  deviceName,
  isRunning,
  isAvailable,
  isEnabled,
  isLoading,
  error,
  lastBackendError,
  selectDevice,
  init,
  fetchDevices,
  fetchStatus,
} = useMicrophoneSelection()

function startStatusRefresh(): void {
  if (statusInterval !== null) return
  statusInterval = window.setInterval(() => {
    void fetchStatus()
  }, 5000)
}

function stopStatusRefresh(): void {
  if (statusInterval === null) return
  window.clearInterval(statusInterval)
  statusInterval = null
}

onMounted(() => {
  void init()
  startStatusRefresh()
})

onBeforeUnmount(() => {
  stopStatusRefresh()
})

watch(isOpen, (open) => {
  if (!open) return
  void Promise.all([fetchDevices(), fetchStatus()])
})

function toggle(): void {
  isOpen.value = !isOpen.value
}

function close(): void {
  isOpen.value = false
}

async function handleSelect(deviceIndex: number): Promise<void> {
  const result = await selectDevice(deviceIndex)
  if (result.ok) {
    close()
  }
}

const activeName = computed(() => {
  if (activeDeviceIndex.value === null) return null
  return devices.value.find((d) => d.index === activeDeviceIndex.value)?.name ?? null
})

const combinedErrorMessage = computed(() => error.value ?? lastBackendError.value)
const unavailableMessage = computed(() => {
  if (!isEnabled.value) {
    return 'Spracherkennung ist deaktiviert.'
  }
  return lastBackendError.value ?? 'Vosk-Modell fehlt oder VOICE_ENABLED=False'
})
const triggerTitle = computed(() => (
  combinedErrorMessage.value
  ?? deviceName.value
  ?? activeName.value
  ?? 'Mikrofon auswählen'
))
</script>

<template>
  <div class="mic-selector">
    <!-- Floating trigger button -->
    <button
      class="mic-trigger"
      :class="{
        'mic-trigger--active': isRunning,
        'mic-trigger--open': isOpen,
      }"
      @click="toggle"
      :aria-label="isOpen ? 'Mikrofon-Auswahl schließen' : 'Mikrofon auswählen'"
      :title="triggerTitle"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="2" width="6" height="11" rx="3"/>
        <path d="M5 10a7 7 0 0 0 14 0"/>
        <line x1="12" y1="19" x2="12" y2="22"/>
        <line x1="8" y1="22" x2="16" y2="22"/>
      </svg>
      <span v-if="isRunning" class="mic-active-dot" />
    </button>

    <!-- Picker panel -->
    <Transition name="mic-panel">
      <div v-if="isOpen" class="mic-panel" role="dialog" aria-label="Mikrofon auswählen">
        <div class="mic-panel-header">
          <svg class="mic-panel-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="2" width="6" height="11" rx="3"/>
            <path d="M5 10a7 7 0 0 0 14 0"/>
            <line x1="12" y1="19" x2="12" y2="22"/>
            <line x1="8" y1="22" x2="16" y2="22"/>
          </svg>
          <span class="mic-panel-title">Mikrofon</span>
          <button class="mic-panel-close" @click="close" aria-label="Schließen">×</button>
        </div>

        <div v-if="combinedErrorMessage" class="mic-error">{{ combinedErrorMessage }}</div>

        <div v-if="!isEnabled || !isAvailable" class="mic-unavailable">
          Spracherkennung nicht verfügbar.<br>
          <small>{{ unavailableMessage }}</small>
        </div>
        <div v-else-if="devices.length === 0" class="mic-empty">
          Keine Mikrofone gefunden
        </div>

        <ul v-else class="mic-list" role="listbox">
          <li
            v-for="device in devices"
            :key="device.index"
            class="mic-item"
            :class="{
              'mic-item--active': device.index === activeDeviceIndex,
              'mic-item--loading': isLoading,
            }"
            role="option"
            :aria-selected="device.index === activeDeviceIndex"
            @click="!isLoading && handleSelect(device.index)"
          >
            <span class="mic-item-check" v-if="device.index === activeDeviceIndex">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="2,8 6,12 14,4"/>
              </svg>
            </span>
            <span v-else class="mic-item-check mic-item-check--empty" />
            <span class="mic-item-name">{{ device.name }}</span>
            <span v-if="device.is_default" class="mic-item-badge">Standard</span>
          </li>
        </ul>

        <div v-if="isLoading" class="mic-loading">Wechsle Mikrofon…</div>
      </div>
    </Transition>

    <!-- Click-outside backdrop -->
    <div v-if="isOpen" class="mic-backdrop" @click="close" />
  </div>
</template>

<style scoped>
.mic-selector {
  position: relative;
  z-index: 60;
}

/* ── Trigger button ── */
.mic-trigger {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.45);
  transition: background 0.18s, border-color 0.18s, color 0.18s, transform 0.12s;
}

.mic-trigger svg {
  width: 18px;
  height: 18px;
}

.mic-trigger:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.22);
  color: rgba(255, 255, 255, 0.80);
}

.mic-trigger:active {
  transform: scale(0.92);
}

.mic-trigger--open {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.28);
  color: #fff;
}

.mic-trigger--active {
  color: #86efac;
  border-color: rgba(134, 239, 172, 0.30);
}

.mic-trigger--active.mic-trigger--open {
  color: #86efac;
}

/* Running indicator dot */
.mic-active-dot {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 0 1.5px rgba(0, 0, 0, 0.6);
  animation: dot-pulse 2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

/* ── Panel ── */
.mic-panel {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  width: 280px;
  background: rgba(15, 15, 20, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.mic-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.mic-panel-icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: rgba(255, 255, 255, 0.40);
}

.mic-panel-title {
  flex: 1;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.50);
}

.mic-panel-close {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: none;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 255, 255, 0.45);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.mic-panel-close:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

/* ── Device list ── */
.mic-list {
  list-style: none;
  margin: 0;
  padding: 6px 0;
  max-height: 260px;
  overflow-y: auto;
}

.mic-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  cursor: pointer;
  transition: background 0.12s;
  min-height: 40px;
}

.mic-item:hover:not(.mic-item--loading) {
  background: rgba(255, 255, 255, 0.06);
}

.mic-item--active {
  background: rgba(74, 222, 128, 0.08);
}

.mic-item--active:hover {
  background: rgba(74, 222, 128, 0.12) !important;
}

.mic-item--loading {
  cursor: default;
  opacity: 0.6;
}

.mic-item-check {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: #4ade80;
}

.mic-item-check svg {
  width: 100%;
  height: 100%;
}

.mic-item-check--empty {
  width: 16px;
  height: 16px;
}

.mic-item-name {
  flex: 1;
  font-size: 0.80rem;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.3;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.mic-item--active .mic-item-name {
  color: #fff;
  font-weight: 600;
}

.mic-item-badge {
  font-size: 0.60rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.30);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 4px;
  padding: 1px 5px;
  white-space: nowrap;
}

/* ── States ── */
.mic-error {
  padding: 8px 14px;
  font-size: 0.78rem;
  color: #fca5a5;
  background: rgba(239, 68, 68, 0.08);
  border-top: 1px solid rgba(239, 68, 68, 0.12);
}

.mic-unavailable {
  padding: 14px 14px;
  font-size: 0.80rem;
  color: rgba(255, 255, 255, 0.40);
  text-align: center;
  line-height: 1.5;
}

.mic-unavailable small {
  font-size: 0.70rem;
  color: rgba(255, 255, 255, 0.25);
}

.mic-empty {
  padding: 16px 14px;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
}

.mic-loading {
  padding: 8px 14px 10px;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.40);
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* ── Backdrop ── */
.mic-backdrop {
  position: fixed;
  inset: 0;
  z-index: 59; /* below mic-selector (60) but above all other content */
}

/* ── Panel transition ── */
.mic-panel-enter-active,
.mic-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

.mic-panel-enter-from,
.mic-panel-leave-to {
  opacity: 0;
  transform: translateY(6px) scale(0.97);
}
</style>
