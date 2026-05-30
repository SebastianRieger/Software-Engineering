<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { buildApiUrl } from '../../services/apiConfig'

const POLL_MS = 250

const frameUrl = ref<string | null>(null)
const cameraName = ref<string | null>(null)
const frameAgeMs = ref<number | null>(null)
const error = ref<string | null>(null)
const loading = ref(true)

let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchStatus(): Promise<void> {
  const response = await fetch(buildApiUrl('gestures/status'))
  if (!response.ok) return
  const status = (await response.json()) as {
    running: boolean
    camera_name: string | null
  }
  cameraName.value = status.camera_name
  if (!status.running) {
    error.value = 'Backend-Kamera ist nicht aktiv.'
  }
}

async function fetchFrame(): Promise<void> {
  const response = await fetch(buildApiUrl('gestures/frame'))
  if (!response.ok) {
    error.value = 'Kein Backend-Kamerabild verfuegbar.'
    return
  }
  const data = (await response.json()) as {
    image: string
    frame_age_ms: number | null
  }
  frameUrl.value = data.image
  frameAgeMs.value = data.frame_age_ms
  error.value = null
  loading.value = false
}

async function initializeCamera(): Promise<void> {
  loading.value = true
  error.value = null

  try {
    await fetchStatus()
    await fetchFrame()
  } catch (cameraError) {
    error.value = cameraError instanceof Error
      ? cameraError.message
      : 'Backend-Kamera nicht verfuegbar.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void initializeCamera()
  pollTimer = setInterval(() => {
    void fetchFrame()
  }, POLL_MS)
})

onBeforeUnmount(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="camera-widget">
    <header class="camera-header">
      <span>Kamera</span>
      <span class="camera-source">{{ cameraName ?? 'Backend' }}</span>
    </header>

    <div class="camera-preview">
      <img
        v-if="frameUrl"
        class="camera-video"
        :src="frameUrl"
        alt="Backend camera preview"
      />
      <div v-if="loading" class="camera-state">Laedt...</div>
      <div v-else-if="error" class="camera-state camera-state--error">{{ error }}</div>
      <div v-else-if="frameAgeMs !== null" class="camera-age">{{ frameAgeMs }} ms</div>
    </div>
  </div>
</template>

<style scoped>
.camera-widget {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0f172a;
  color: #f8fafc;
  overflow: hidden;
}

.camera-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  font-size: 0.9rem;
  font-weight: 700;
  background: rgba(15, 23, 42, 0.92);
  min-height: 42px;
}

.camera-source {
  min-width: 0;
  max-width: 65%;
  color: #cbd5e1;
  font-size: 0.76rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.camera-preview {
  position: relative;
  flex: 1;
  min-height: 0;
  background: #020617;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.camera-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 12px;
  text-align: center;
  background: rgba(2, 6, 23, 0.78);
  font-size: 0.9rem;
}

.camera-state--error {
  color: #fca5a5;
}

.camera-age {
  position: absolute;
  right: 8px;
  bottom: 8px;
  padding: 3px 7px;
  border-radius: 6px;
  background: rgba(2, 6, 23, 0.72);
  color: #cbd5e1;
  font-size: 0.72rem;
  font-weight: 700;
}
</style>