<script setup lang="ts">
const data = { temp: "21°C", city: "Karlsruhe", cond: "Wolkig" };
</script>

<template>
  <div class="card">
    <h3>Wetter</h3>
    <p>{{ data.city }} · {{ data.cond }} · {{ data.temp }}</p>
  </div>
</template>

<style scoped>
.card { background:#111; color:#eee; border-radius:16px; padding:16px; }
</style>
