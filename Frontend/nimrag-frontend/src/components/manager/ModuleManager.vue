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
const activeWidgets: { [key: number]: any } = {}

const isShopOpen = ref(false);
const isEditMode = ref(false);
const moduleShopRef = ref<ComponentPublicInstance<{}, ModuleShopExposed> | null>(null);

// Function to insert a Vue component into a cell
const insertVueWidgetIntoCell = (cellId: number, widgetComponent: any) => {
  const mount = document.getElementById(`cell-content-${cellId}`)
  if (!mount) {
    console.error(`Mount for cell ${cellId} not found`)
    return
  }

  // Clean up old component if exists
  if (activeWidgets[cellId]) {
    activeWidgets[cellId].unmount()
  }

  // Clear mount content
  mount.innerHTML = ''

  // Create container for Vue component
  const widgetContainer = document.createElement('div')
  widgetContainer.className = 'w-full h-full'
  mount.appendChild(widgetContainer)

  // Create and mount Vue app for this component
  const app = createApp(widgetComponent)
  app.mount(widgetContainer)

  // Store app for later cleanup
  activeWidgets[cellId] = app
}

// Handle adding widget from shop
const handleAddWidget = ({ cellId, component }: { cellId: number; component: any }) => {
  insertVueWidgetIntoCell(cellId, component);
  console.log('Widget added to cell:', cellId);
  console.log('Active widgets:', Object.keys(activeWidgets[cellId]));
};

// Clear a cell
const clearCell = (cellId: number) => {
  const mount = document.getElementById(`cell-content-${cellId}`)
  if (!mount) return

  // Clean up Vue app if exists
  if (activeWidgets[cellId]) {
    activeWidgets[cellId].unmount()
    delete activeWidgets[cellId]
  }

  // Platzhalter wiederherstellen
  mount.innerHTML = `
    <div class="w-full h-full grid place-items-center text-2xl font-semibold opacity-70">
      ${String(cellId).padStart(2, '0')}
    </div>
  `
}

// Toggle edit mode
const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value;
}

// Handle widgets moved event from GridBoard
const handleWidgetsMoved = ({ sourceCellId, targetCellId }: { sourceCellId: number; targetCellId: number }) => {
  const sourceApp = activeWidgets[sourceCellId]
  const targetApp = activeWidgets[targetCellId]

  if (sourceApp && targetApp) {
    activeWidgets[targetCellId] = sourceApp
    activeWidgets[sourceCellId] = targetApp
  } else if (sourceApp && !targetApp) {
    activeWidgets[targetCellId] = sourceApp
    delete activeWidgets[sourceCellId]
  } else if (!sourceApp && targetApp) {
    activeWidgets[sourceCellId] = targetApp
    delete activeWidgets[targetCellId]
  }
}

// Handle keydown events
const handleKeydown = (event: KeyboardEvent) => {
  console.log('Key pressed:', event.key); // Debug log
  if (event.key === 'e') {
    isShopOpen.value = !isShopOpen.value;
  } else if (event.key === 'f' || event.key === 'F') {
    toggleEditMode();
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
    <!-- Edit Mode Banner -->
    <Transition name="slide-down">
      <div v-if="isEditMode" class="edit-mode-banner">
        <span class="edit-mode-text">Editor Modus</span>
        <span class="edit-mode-hint">Drücke F zum Beenden</span>
      </div>
    </Transition>

    <!-- Module Shop Popup -->
    <div v-if="isShopOpen" class="shop-overlay" @click.self="isShopOpen = false">
      <div class="shop-modal">
        <button class="close-btn" @click="isShopOpen = false">×</button>
        <ModuleShop ref="moduleShopRef" @addWidget="handleAddWidget" />
      </div>
    </div>

    <!-- GridBoard mit Event-Listener für widgetsMoved -->
    <GridBoard
        :is-edit-mode="isEditMode"
        @widgets-moved="handleWidgetsMoved"
        @delete-widget="clearCell"
    />
  </div>
</template>

<style scoped>
.edit-mode-banner {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  padding: 12px 24px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
  z-index: 999;
  display: flex;
  align-items: center;
  gap: 16px;
  font-weight: 600;
}

.edit-mode-text {
  font-size: 16px;
}

.edit-mode-hint {
  font-size: 12px;
  opacity: 0.9;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 6px;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from {
  transform: translateX(-50%) translateY(-100%);
  opacity: 0;
}

.slide-down-leave-to {
  transform: translateX(-50%) translateY(-100%);
  opacity: 0;
}

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