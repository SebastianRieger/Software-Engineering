<script setup lang="ts">
//startet beim laden der seite -> imports und so hier rein
</script>

<script lang="ts">
//startet nicht beim init der seite -> eigene Funktionen und so hier rein


</script>

<template>
<div class="grid h-screen w-screen grid-cols-4 grid-rows-4 gap-1 bg-neutral-900 text-white p-4">
    <!--
    <div class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden p-3">
      <ModuleManager module="ClockWidget" class="w-full h-full" />
    </div>


    <div class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden p-3">
      <ModuleManager module="WeatherWidget" class="w-full h-full" />
    </div>
  -->
    <!-- generiert leere Zellen mit Platzhaltern -->
    <div
        v-for="i in 16"
        :key="i"
        :id=i.toString()
        class="rounded-xl bg-neutral-800 shadow-inner overflow-hidden"
    >
      <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
        {{ String(i).padStart(2, '0') }}
      </div>
    </div>
</div>
</template>

<style scoped>

</style>

