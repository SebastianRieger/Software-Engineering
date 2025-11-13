<script setup lang="ts">
const data = { temp: "21°C", city: "Karlsruhe", cond: "Wolkig" };
</script>

<template>
  <div class="w-full h-full card flex flex-col justify-center">
    <h3>Wetter</h3>
    <p>{{ data.city }} · {{ data.cond }} · {{ data.temp }}</p>
  </div>
</template>

<style scoped>
.card { background:#111; color:#eee; padding:16px; }
</style>
