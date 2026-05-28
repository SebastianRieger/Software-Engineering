<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const CAMERA_STORAGE_KEY = 'nimrag-camera-device-id'

const videoRef = ref<HTMLVideoElement | null>(null)
const cameras = ref<MediaDeviceInfo[]>([])
const selectedDeviceId = ref(localStorage.getItem(CAMERA_STORAGE_KEY) ?? '')
const error = ref<string | null>(null)
const loading = ref(true)

let currentStream: MediaStream | null = null

function stopStream(): void {
  currentStream?.getTracks().forEach((track) => track.stop())
  currentStream = null
}

async function refreshCameraList(): Promise<void> {
  if (!navigator.mediaDevices?.enumerateDevices) {
    cameras.value = []
    return
  }

  const devices = await navigator.mediaDevices.enumerateDevices()
  cameras.value = devices.filter((device) => device.kind === 'videoinput')
}

async function startPreview(): Promise<void> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Kamera wird von diesem Browser nicht unterstuetzt.')
  }

  stopStream()
  const videoConstraint = selectedDeviceId.value
    ? { deviceId: { exact: selectedDeviceId.value } }
    : true

  currentStream = await navigator.mediaDevices.getUserMedia({
    video: videoConstraint,
    audio: false,
  })

  if (videoRef.value) {
    videoRef.value.srcObject = currentStream
    await videoRef.value.play().catch(() => undefined)
  }
}

async function initializeCamera(): Promise<void> {
  loading.value = true
  error.value = null

  try {
    await startPreview()
    await refreshCameraList()
  } catch (cameraError) {
    error.value = cameraError instanceof Error
      ? cameraError.message
      : 'Kamera nicht verfuegbar.'
  } finally {
    loading.value = false
  }
}

async function handleDeviceChange(): Promise<void> {
  if (selectedDeviceId.value) {
    localStorage.setItem(CAMERA_STORAGE_KEY, selectedDeviceId.value)
  } else {
    localStorage.removeItem(CAMERA_STORAGE_KEY)
  }
  await initializeCamera()
}

onMounted(() => {
  void initializeCamera()
})

onBeforeUnmount(() => {
  stopStream()
})
</script>

<template>
  <div class="camera-widget">
    <header class="camera-header">
      <span>Kamera</span>
      <select
        v-if="cameras.length > 1"
        v-model="selectedDeviceId"
        class="camera-select"
        aria-label="Kamera auswaehlen"
        @change="handleDeviceChange"
      >
        <option value="">Standardkamera</option>
        <option
          v-for="(camera, index) in cameras"
          :key="camera.deviceId || index"
          :value="camera.deviceId"
        >
          {{ camera.label || `Kamera ${index + 1}` }}
        </option>
      </select>
    </header>

    <div class="camera-preview">
      <video
        ref="videoRef"
        class="camera-video"
        autoplay
        muted
        playsinline
      />
      <div v-if="loading" class="camera-state">Lädt...</div>
      <div v-else-if="error" class="camera-state camera-state--error">Kamera nicht verfuegbar</div>
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

.camera-select {
  min-width: 0;
  max-width: 65%;
  height: 28px;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 6px;
  background: #111827;
  color: #f8fafc;
  font-size: 0.78rem;
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
</style>