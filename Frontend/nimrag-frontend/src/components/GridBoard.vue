<script setup lang="ts">
import ClockWidget from './widgets/ClockWidget.vue'
import WeatherWidget from './widgets/WeatherWidget.vue'
</script>

<template>
  <div class="grid h-screen w-screen grid-cols-4 grid-rows-4 gap-4 bg-neutral-900 text-white p-4">
    <!-- Zelle 1: Uhr -->
    <div class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden p-3">
      <ClockWidget class="w-full h-full" />
    </div>

    <!-- Zelle 2: Wetter -->
    <div class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden p-3">
      <WeatherWidget class="w-full h-full" />
    </div>

    <!-- restliche Zellen als Platzhalter -->
    <div
        v-for="i in 10"
        :key="i"
        class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden"
    >
      <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
        {{ String(i + 2).padStart(2, '0') }}
      </div>
    </div>
  </div>
</template>

<style scoped>

</style>

