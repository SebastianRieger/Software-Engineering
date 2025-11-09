<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
const now = ref(new Date())
let timer: number
onMounted(() => { timer = window.setInterval(() => now.value = new Date(), 1000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div class="w-full h-full card flex flex-col justify-center">
    <h3>Uhr</h3>
    <p style="font-size:2rem; margin:0;">{{ now.toLocaleTimeString() }}</p>
  </div>
</template>

<style scoped>
.card { background:#111; color:#eee; padding:16px; }

</style>