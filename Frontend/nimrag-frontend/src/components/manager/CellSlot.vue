<script setup lang="ts">
import { provide } from 'vue'
import type { Component } from 'vue'
import { useWidgetResize } from '../../composables/useWidgetResize'

const props = defineProps<{ cellId: number; component: Component }>()
const { cellSizes } = useWidgetResize()

provide('cellId', props.cellId)
provide('cellSizes', cellSizes)
</script>

<template>
  <component :is="component" class="w-full h-full" />
</template>
