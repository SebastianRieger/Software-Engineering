<template>
  <div class="layout-grid">
    <slot />
  </div>
</template>

<script setup lang="ts">
// Minimal layout wrapper; complex drag/resize can be added later
</script>

<style scoped>
.layout-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}
</style>
