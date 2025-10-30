<template>
  <BaseWidget :type="'weather'" :title="title" :isLoading="isLoading" @refresh="fetchData">
    <template #default>
      <div class="weather-widget">
        <div class="weather-header">
          <strong>{{ location }}</strong>
          <span class="temperature">{{ temperature }}</span>
        </div>
        <div class="weather-forecast">
          <ul>
            <li v-for="(f, idx) in forecast" :key="idx">{{ f.summary }} - {{ f.temp }}°</li>
          </ul>
        </div>
      </div>
    </template>
  </BaseWidget>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import BaseWidget from '../base/BaseWidget.vue'
import { useWidget } from '../../composables/useWidget'

const props = withDefaults(defineProps<{ widgetId: string; title?: string; location?: string }>(), {
  title: 'Weather',
  location: 'Unknown'
})

const { widget, isLoading, fetchWidgetData } = useWidget(props.widgetId)

const location = ref(props.location)
const temperature = computed(() => widget.value?.data?.temperature ?? '--')
const forecast = computed(() => widget.value?.data?.forecast ?? [])

const fetchData = async () => {
  await fetchWidgetData()
}
</script>

<style scoped>
.weather-widget {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.weather-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.temperature {
  font-size: 1.5rem;
}
</style>
