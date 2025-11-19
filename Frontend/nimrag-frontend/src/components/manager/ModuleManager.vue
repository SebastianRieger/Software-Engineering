<script setup lang="ts">
import { createApp, ref, onMounted, onBeforeUnmount} from 'vue';
import type { ComponentPublicInstance } from 'vue';
import GridBoard from './GridBoard.vue';
import ModuleShop from './ModuleShop.vue';

// Define an interface for the exposed methods
interface ModuleShopExposed {
  nextModule: () => void;
  prevModule: () => void;
}

// Store for active widgets
const activeWidgets = ref<{[key: string]: any}>({});
const isShopOpen = ref(false);
const moduleShopRef = ref<ComponentPublicInstance<{}, ModuleShopExposed> | null>(null);

// Function to insert a Vue component into a cell
const insertVueWidgetIntoCell = (cellId: number, widgetComponent: any) => {
  const cell = document.getElementById(cellId.toString());
  if (!cell) {
    console.error(`Cell with ID ${cellId} not found`);
    return;
  }

  // Clean up old component if exists
  if (activeWidgets.value[cellId]) {
    activeWidgets.value[cellId].unmount();
  }

  // Clear cell content
  cell.innerHTML = '';

  // Create container for Vue component
  const widgetContainer = document.createElement('div');
  widgetContainer.className = 'w-full h-full';
  cell.appendChild(widgetContainer);

  // Create and mount Vue app for this component
  const app = createApp(widgetComponent);
  app.mount(widgetContainer);

  // Store app for later cleanup
  activeWidgets.value[cellId] = app;

  // Update cell styling
  cell.className = 'rounded-xl bg-neutral-800 shadow-inner overflow-hidden';
};

// Handle adding widget from shop
const handleAddWidget = ({ cellId, component }: { cellId: number; component: any }) => {
  insertVueWidgetIntoCell(cellId, component);
};

// // Clear a cell
// const clearCell = (cellId: number) => {
//   const cell = document.getElementById(cellId.toString());
//   if (!cell) return;
//
//   // Clean up Vue app if exists
//   if (activeWidgets.value[cellId]) {
//     activeWidgets.value[cellId].unmount();
//     delete activeWidgets.value[cellId];
//   }
//
//   cell.innerHTML = `
//     <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
//       ${String(cellId).padStart(2, '0')}
//     </div>
//   `;
//   cell.className = 'rounded-xl bg-neutral-800 shadow-inner overflow-hidden';
// };

// Handle keydown events
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'e') {
    isShopOpen.value = !isShopOpen.value;
  } else if (event.key === 'Escape') {
    isShopOpen.value = false;
  } else if (isShopOpen.value && moduleShopRef.value) {
    // Only when shop is open and ref is available
    if (event.key === 'ArrowRight') {
      moduleShopRef.value.nextModule();
    } else if (event.key === 'ArrowLeft') {
      moduleShopRef.value.prevModule();
    }
  }
};

onMounted(() => {
  // Add keyboard event listener
  window.addEventListener('keydown', handleKeydown);
});

onBeforeUnmount(() => {
  // Remove keyboard event listener
  window.removeEventListener('keydown', handleKeydown);
});
</script>

<template>
  <div>
    <!-- Module Shop Popup -->
    <div v-if="isShopOpen" class="shop-overlay" @click.self="isShopOpen = false">
      <div class="shop-modal">
        <button class="close-btn" @click="isShopOpen = false">×</button>
        <ModuleShop ref="moduleShopRef" @addWidget="handleAddWidget" />
      </div>
    </div>

    <GridBoard />
  </div>
</template>

<style scoped>
.shop-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.shop-modal {
  position: relative;
  background: #222;
  border-radius: 8px;
  padding: 20px;
  max-width: 80%;
  max-height: 80%;
  overflow: auto;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
}
</style>