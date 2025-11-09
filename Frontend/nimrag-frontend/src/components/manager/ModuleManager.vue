<script setup lang="ts">
import { defineAsyncComponent } from 'vue';

const props = defineProps<{ module: string }>();

// Dynamically import the component based on the module prop
const moduleComponent = defineAsyncComponent(() => import(`@/components/widgets/${props.module}.vue`));
</script>

<template>
  <div class="card w-full h-full">
    <component :is="moduleComponent" />
    <!-- Module management UI goes here -->
  </div>
</template>


<style scoped>
.card {
  background: #111;
  color: #eee;
  border-radius: 16px;
  padding: 16px;
  width: 100%;
  height: 100%;
}
</style>