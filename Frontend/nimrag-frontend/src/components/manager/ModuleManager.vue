<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import type { ComponentPublicInstance } from 'vue';
import GridBoard from './GridBoard.vue';
import ModuleShop from './ModuleShop.vue';
import HomeScreen from '../HomeScreen.vue';
import { useWidgetManager } from '../../composables/useWidgetManager';
import { useWidgetResize } from '../../composables/useWidgetResize';
import { useEditMode } from '../../composables/useEditMode';
import { useModuleShop } from '../../composables/useModuleShop';
import { useClockWidgetMode } from '../../composables/useClockWidgetMode';
import { useActionDispatcher } from '../../composables/useActionDispatcher';
import { useHomeScreen } from '../../composables/useHomeScreen';
import { realtimeClient } from '../../services/realtime';
import { checkExternalApiHealth } from '../../services/systemHealth';

// Interface für die Methoden des ModuleShop
interface ModuleShopExposed {
  addCurrentWidgetToCell: (cellId: number) => void;
  nextModule: () => void;
  prevModule: () => void;
}

// View-State: home = Kamera-Homescreen, grid = GridBoard
const currentView = ref<'home' | 'grid'>('home');
function goToGrid(): void { currentView.value = 'grid'; }

// HomeScreen Composable
const {
  cameras,
  currentIndex,
  frameUrl,
  error: cameraError,
  loading: cameraLoading,
  slideDirection,
  initializeCamera,
  navigateCamera,
  stopStream,
} = useHomeScreen();

// Composables initialisieren
const { insertWidgetIntoCell, clearCell, moveWidgets, occupiedCells } = useWidgetManager();
const { getVisibleCells, resizeCell } = useWidgetResize();

const availableCells = computed(() => {
  const occupied = new Set(occupiedCells.value)
  return getVisibleCells().filter(id => !occupied.has(id))
});
const { isEditMode, setEditMode, setupKeyboardListener } = useEditMode();
const { isShopOpen, toggleShop, openShop, closeShop } = useModuleShop();
const { clockAnalogMode, toggleClockMode } = useClockWidgetMode();

const moduleShopRef = ref<ComponentPublicInstance<{}, ModuleShopExposed> | null>(null);
let unsubscribeRealtime: (() => void) | null = null;

const { focusedCellId, handleRealtimeEvent, syncFocusedCell } = useActionDispatcher({
  isShopOpen,
  openShop,
  closeShop,
  toggleShop,
  isEditMode,
  setEditMode,
  visibleCellIds: getVisibleCells,
  isCellAvailable: (cellId: number) => availableCells.value.includes(cellId),
  resizeCell,
  moduleShopRef,
  currentView,
  navigateCamera,
  goToGrid,
});

/**
 * Verarbeitet das Hinzufügen eines Widgets aus dem Shop
 */
const handleAddWidget = ({ cellId, component }: { cellId: number; component: any }) => {
  insertWidgetIntoCell(cellId, component);
  syncFocusedCell();
  console.log('Widget zu Zelle hinzugefügt:', cellId);
};

/**
 * Verarbeitet das Verschieben von Widgets
 */
const handleWidgetsMoved = ({ sourceCellId, targetCellId }: { sourceCellId: number; targetCellId: number }) => {
  moveWidgets({ sourceCellId, targetCellId });
  syncFocusedCell();
};

/**
 * Verarbeitet das Löschen eines Widgets
 */
const handleDeleteWidget = (cellId: number) => {
  clearCell(cellId);
  syncFocusedCell();
};

/**
 * Keyboard-Event Handler mit Shop-Navigation
 */
const handleShopNavigation = (key: string) => {
  if (isShopOpen.value && moduleShopRef.value) {
    if (key === 'ArrowRight') {
      moduleShopRef.value.nextModule();
    } else if (key === 'ArrowLeft') {
      moduleShopRef.value.prevModule();
    }
  }
};

// Keyboard-Listener Setup
setupKeyboardListener({
  onShopToggle: toggleShop,
  onShopNavigate: handleShopNavigation,
  onClockToggle: toggleClockMode,
});

watch(availableCells, () => {
  syncFocusedCell();
});

onMounted(() => {
  void checkExternalApiHealth().catch((error) => {
    console.warn('External API health check failed', error);
  });
  void initializeCamera();
  syncFocusedCell();
  unsubscribeRealtime = realtimeClient.subscribe((event) => {
    handleRealtimeEvent(event);
  });
});

onBeforeUnmount(() => {
  unsubscribeRealtime?.();
  unsubscribeRealtime = null;
  stopStream();
});

</script>

<template>
  <div class="app-root">

    <!-- HomeScreen (Kamera-Startseite) -->
    <Transition name="view-to-grid">
      <HomeScreen
        v-if="currentView === 'home'"
        :cameras="cameras"
        :current-index="currentIndex"
        :frame-url="frameUrl"
        :error="cameraError"
        :loading="cameraLoading"
        :slide-direction="slideDirection"
        @go-to-grid="goToGrid"
      />
    </Transition>

    <!-- Grid-Ansicht -->
    <Transition name="view-from-right">
      <div v-if="currentView === 'grid'" class="grid-view">

        <!-- Edit Mode Banner -->
        <Transition name="slide-down">
          <div v-if="isEditMode" class="edit-mode-banner">
            <div class="edit-mode-content">
              <span class="edit-mode-text">Editor Modus aktiv</span>
              <div class="edit-mode-shortcuts">
                <span class="shortcut">E – Shop</span>
                <span class="shortcut">F – Beenden</span>
                <span class="shortcut">Klick ⤡ – Größe ändern</span>
                <button
                  class="shortcut shortcut-btn"
                  @click="toggleClockMode"
                  :title="clockAnalogMode ? 'Digitale Uhr' : 'Analoge Uhr'"
                >
                  {{ clockAnalogMode ? '🔢 Digital' : '🕐 Analog' }} – A
                </button>
              </div>
            </div>
          </div>
        </Transition>

        <!-- Module Shop Popup -->
        <div v-if="isShopOpen" class="shop-overlay" @click.self="closeShop">
          <div class="shop-modal">
            <button class="close-btn" @click="closeShop">×</button>
            <ModuleShop ref="moduleShopRef" :available-cells="availableCells" @addWidget="handleAddWidget" />
          </div>
        </div>

        <GridBoard
          :is-edit-mode="isEditMode"
          :focused-cell-id="focusedCellId"
          @widgets-moved="handleWidgetsMoved"
          @delete-widget="handleDeleteWidget"
        />
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.app-root {
  position: fixed;
  inset: 0;
  overflow: hidden;
}

.grid-view {
  position: absolute;
  inset: 0;
}

/* View-Transition: HomeScreen → Grid (slide nach links) */
.view-to-grid-leave-active,
.view-from-right-enter-active {
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.view-to-grid-leave-to {
  transform: translateX(-100%);
}

.view-from-right-enter-from {
  transform: translateX(100%);
}

.edit-mode-banner {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
  z-index: 999;
  display: flex;
  align-items: center;
  gap: 16px;
  font-weight: 600;
}

.edit-mode-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shortcut {
  opacity: 0.9;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 10px;
  border-radius: 6px;
  white-space: nowrap;
}

.shortcut-btn {
  border: none;
  color: white;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s ease;
  display: inline-block;
}

.shortcut-btn:hover {
  background: rgba(255, 255, 255, 0.3) !important;
  transform: scale(1.05);
}

.shortcut-btn:active {
  transform: scale(0.95);
}

.edit-mode-text {
  font-size: 16px;
  font-weight: 700;
}

.edit-mode-shortcuts {
  display: flex;
  gap: 12px;
  font-size: 12px;
  flex-wrap: wrap;
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
  width: 95vw;
  height: 95vh;
  max-width: 1200px;
  max-height: 800px;
  overflow: auto;
  display: flex;
  flex-direction: column;
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
  transition: all 0.2s;
}

.close-btn:hover {
  transform: scale(1.2);
  color: #ef4444;
}
</style>