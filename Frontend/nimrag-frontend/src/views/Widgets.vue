<template>
  <div class="widgets-view">
    <h2>Widgets</h2>

    <LayoutGrid>
      <WidgetContainer>
        <!-- Example: mount our WeatherWidget -->
        <WeatherWidget widgetId="weather-1" title="Local Weather" />
      </WidgetContainer>
    </LayoutGrid>
  </div>
</template>

<script setup lang="ts">
import LayoutGrid from '../components/layout/LayoutGrid.vue'
import WidgetContainer from '../components/layout/WidgetContainer.vue'
import WeatherWidget from '../components/widgets/WeatherWidget.vue'
</script>

<style scoped>
.widgets-view {
  text-align: left;
}
</style>
