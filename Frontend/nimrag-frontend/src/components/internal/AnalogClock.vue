<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import type { CellSize } from '../../composables/useWidgetResize'

const props = defineProps<{
  time: Date
  size: CellSize
}>()

const canvasRef = ref<HTMLCanvasElement>()

const getClockRadius = () => {
  switch (props.size) {
    case 4:  return 130
    case 2:  return 110
    default: return 95
  }
}

const drawClock = () => {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const radius = getClockRadius()
  const centerX = canvas.width / 2
  const centerY = canvas.height / 2

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Schwarzer Hintergrund
  ctx.fillStyle = '#000000'
  ctx.beginPath()
  ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI)
  ctx.fill()

  // Alle 12 Ziffern am äußeren Rand - vertikal angeordnet (wie Apple Watch)
  for (let i = 1; i <= 12; i++) {
    const angle = ((i - 3) * 30) * Math.PI / 180
    const x = centerX + (radius - 12) * Math.cos(angle)
    const y = centerY + (radius - 12) * Math.sin(angle)

    ctx.save()
    ctx.translate(x, y)
    // Rotiere den Text so dass er vertikal lesbar ist
    ctx.rotate(angle + Math.PI / 2)

    ctx.fillStyle = '#ffffff'
    ctx.font = `bold ${radius * 0.22}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(i.toString(), 0, 0)

    ctx.restore()
  }

  const hours = props.time.getHours() % 12
  const minutes = props.time.getMinutes()
  const seconds = props.time.getSeconds()
  const milliseconds = props.time.getMilliseconds()
  const totalSeconds = seconds + milliseconds / 1000

  // Stundenzeiger - weiß, kurz und dick
  drawHand(
    ctx,
    centerX,
    centerY,
    (hours * 30 + minutes * 0.5) * Math.PI / 180,
    radius * 0.35,
    8,
    '#ffffff'
  )

  // Minutenzeiger - weiß, lang und mittel
  drawHand(
    ctx,
    centerX,
    centerY,
    (minutes * 6 + totalSeconds * 0.1) * Math.PI / 180,
    radius * 0.62,
    6,
    '#ffffff'
  )

  // Sekundenzeiger - rot
  drawHand(
    ctx,
    centerX,
    centerY,
    (totalSeconds * 6) * Math.PI / 180,
    radius * 0.65,
    3,
    '#ff0000'
  )

  // Mittelpunkt - rote Kugel
  ctx.fillStyle = '#ff0000'
  ctx.beginPath()
  ctx.arc(centerX, centerY, 7, 0, 2 * Math.PI)
  ctx.fill()

  // Innerer weißer Punkt
  ctx.fillStyle = '#ffffff'
  ctx.beginPath()
  ctx.arc(centerX, centerY, 3, 0, 2 * Math.PI)
  ctx.fill()
}

const drawHand = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  angle: number,
  length: number,
  width: number,
  color: string
) => {
  const endX = x + length * Math.cos(angle - Math.PI / 2)
  const endY = y + length * Math.sin(angle - Math.PI / 2)

  ctx.strokeStyle = color
  ctx.lineWidth = width
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  ctx.moveTo(x, y)
  ctx.lineTo(endX, endY)
  ctx.stroke()
}

watch(() => props.time, drawClock, { deep: true })

onMounted(() => {
  if (canvasRef.value) {
    const radius = getClockRadius()
    canvasRef.value.width = radius * 2.8
    canvasRef.value.height = radius * 2.8
    drawClock()
  }
})
</script>

<template>
  <canvas ref="canvasRef" class="analog-canvas" />
</template>

<style scoped>
.analog-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
</style>
