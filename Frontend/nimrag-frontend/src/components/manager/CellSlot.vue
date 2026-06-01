<script setup lang="ts">
import { computed, provide } from 'vue'
import type { Component } from 'vue'
import { useWidgetResize } from '../../composables/useWidgetResize'

const props = defineProps<{ cellId: number; component: Component; isEditMode?: boolean }>()
const { cellSizes } = useWidgetResize()

provide('cellId', props.cellId)
provide('cellSizes', cellSizes)
provide('isEditMode', computed(() => props.isEditMode ?? false))
</script>

<template>
  <component :is="component" class="w-full h-full" />
</template>
