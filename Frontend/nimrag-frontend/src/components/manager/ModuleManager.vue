<script setup lang="ts">
import { createApp, ref, onMounted } from 'vue';
import GridBoard from '../GridBoard.vue';
import WeatherWidget from '../widgets/WeatherWidget.vue';
import ClockWidget from '../widgets/ClockWidget.vue';

// Store für aktive Widgets
const activeWidgets = ref<{[key: string]: any}>({});

// Funktion zum Einfügen einer echten Vue-Komponente in eine Zelle
const insertVueWidgetIntoCell = (cellId: number, widgetComponent: any) => {
  const cell = document.getElementById(cellId.toString());
  if (!cell) {
    console.error(`Cell with ID ${cellId} not found`);
    return;
  }

  // Alte Komponente aufräumen falls vorhanden
  if (activeWidgets.value[cellId]) {
    activeWidgets.value[cellId].unmount();
  }

  // Zellen-Inhalt leeren
  cell.innerHTML = '';
  
  // Container für die Vue-Komponente erstellen
  const widgetContainer = document.createElement('div');
  widgetContainer.className = 'w-full h-full';
  cell.appendChild(widgetContainer);
  
  // Vue-App für diese Komponente erstellen und mounten
  const app = createApp(widgetComponent);
  app.mount(widgetContainer);
  
  // App für späteres Cleanup speichern
  activeWidgets.value[cellId] = app;
  
  // Styling anpassen für Widget-Container
  cell.className = 'rounded-xl bg-neutral-800 shadow-inner overflow-hidden';
};

// Vereinfachte Funktionen mit echten Vue-Komponenten
const addWeatherToCell = (cellId: number) => {
  insertVueWidgetIntoCell(cellId, WeatherWidget);
};

const addClockToCell = (cellId: number) => {
  insertVueWidgetIntoCell(cellId, ClockWidget);
};

// Beispiel-Funktionen
const addWeatherToCell1 = () => addWeatherToCell(1);
const addClockToCell2 = () => addClockToCell(2);
const addWeatherToCell5 = () => addWeatherToCell(5);

// Zelle wieder leer machen
const clearCell = (cellId: number) => {
  const cell = document.getElementById(cellId.toString());
  if (!cell) return;
  
  // Vue-App aufräumen falls vorhanden
  if (activeWidgets.value[cellId]) {
    activeWidgets.value[cellId].unmount();
    delete activeWidgets.value[cellId];
  }
  
  cell.innerHTML = `
    <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
      ${String(cellId).padStart(2, '0')}
    </div>
  `;
  cell.className = 'rounded-xl bg-neutral-800 shadow-inner overflow-hidden';
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'e') {
    document.querySelector('.control-panel')?.classList.toggle('hidden');
  }
};

onMounted(() => {
  // Beispiel: Automatisch Widgets beim Laden hinzufügen
  // setTimeout(() => {
  //   addWeatherToCell(1);
  //   addClockToCell(2);
  // }, 1000);
  
  // Keyboard event listener hinzufügen
  window.addEventListener('keydown', handleKeydown);
});
</script>

<template>
  <div>
    <div class="control-panel fixed top-4 left-4 z-10 bg-neutral-700 p-4 rounded-lg space-y-2 hidden">
      <h4 class="text-white font-semibold">Widget Manager</h4>
      <div class="space-y-1">
        <button @click="addWeatherToCell1" class="block w-full bg-blue-600 text-white px-3 py-1 rounded text-sm">
          Weather → Cell 1
        </button>
        <button @click="addClockToCell2" class="block w-full bg-green-600 text-white px-3 py-1 rounded text-sm">
          Clock → Cell 2
        </button>
        <button @click="addWeatherToCell5" class="block w-full bg-blue-600 text-white px-3 py-1 rounded text-sm">
          Weather → Cell 5
        </button>
        <button @click="clearCell(1)" class="block w-full bg-red-600 text-white px-3 py-1 rounded text-sm">
          Clear Cell 1
        </button>
      </div>
    </div>
    <GridBoard />
  </div>
</template>

<style scoped>

</style>