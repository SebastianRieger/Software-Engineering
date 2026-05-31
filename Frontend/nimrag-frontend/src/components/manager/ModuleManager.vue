<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import type { ComponentPublicInstance } from 'vue';
import type { UIActionRequestedPayload } from '../../types/interactions';
import GridBoard from './GridBoard.vue';
import ModuleShop from './ModuleShop.vue';
import GestureCursor from './GestureCursor.vue';
import GestureContextHUD from './GestureContextHUD.vue';
import GestureDebugPanel from './GestureDebugPanel.vue';
import HomeScreen from '../HomeScreen.vue';
import { useWidgetManager } from '../../composables/useWidgetManager';
import { useWidgetResize } from '../../composables/useWidgetResize';
import { useEditMode } from '../../composables/useEditMode';
import { useModuleShop } from '../../composables/useModuleShop';
import { useClockWidgetMode } from '../../composables/useClockWidgetMode';
import { useActionDispatcher } from '../../composables/useActionDispatcher';
import { useGestureDebug } from '../../composables/useGestureDebug';
import { useHomeScreen } from '../../composables/useHomeScreen';
import { useHandTracking } from '../../composables/useHandTracking';
import { useInteractionState } from '../../composables/useInteractionState';
import { backendReachability } from '../../services/backendReachability';
import { realtimeClient } from '../../services/realtime';
import { checkExternalApiHealth } from '../../services/systemHealth';

interface ModuleShopExposed {
  addCurrentWidgetToCell: (cellId: number) => void;
  nextModule: () => void;
  prevModule: () => void;
}

// View-State
const currentView = ref<'home' | 'grid'>('home');
function goToGrid(): void { currentView.value = 'grid'; }

// HomeScreen
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

// Widget management
const { insertWidgetIntoCell, clearCell, moveWidgets, occupiedCells, widgetMap } = useWidgetManager();
const { getVisibleCells, resizeCell } = useWidgetResize();

const availableCells = computed(() => {
  const occupied = new Set(occupiedCells.value)
  return getVisibleCells().filter(id => !occupied.has(id))
});

const { isEditMode, setEditMode, setupKeyboardListener } = useEditMode();
const { isShopOpen, toggleShop, openShop, closeShop } = useModuleShop();
const { toggleClockMode } = useClockWidgetMode();
const { indexFingerCursor } = useHandTracking();
const {
  entries: gestureDebugEntries,
  trackingStatus: gestureDebugTrackingStatus,
  lastGesture: gestureDebugLastGesture,
  lastGestureDetail: gestureDebugLastGestureDetail,
  lastCommand: gestureDebugLastCommand,
  lastCommandDetail: gestureDebugLastCommandDetail,
  lastAction: gestureDebugLastAction,
  lastActionDetail: gestureDebugLastActionDetail,
  lastDispatch: gestureDebugLastDispatch,
  lastDispatchDetail: gestureDebugLastDispatchDetail,
  recordRealtimeEvent,
  recordDispatchResult,
} = useGestureDebug();

const moduleShopRef = ref<ComponentPublicInstance<{}, ModuleShopExposed> | null>(null);
let unsubscribeRealtime: (() => void) | null = null;
const debugPanelVisible = ref(true);

const {
  focusedCellId,
  isDragging,
  dragSourceCell,
  deleteConfirmCell,
  handleRealtimeEvent,
  syncFocusedCell,
} = useActionDispatcher({
  isShopOpen,
  openShop,
  closeShop,
  toggleShop,
  isEditMode,
  setEditMode,
  visibleCellIds: getVisibleCells,
  isCellAvailable: (cellId: number) => availableCells.value.includes(cellId),
  isCellOccupied: (cellId: number) => {
    const occupied = new Set(occupiedCells.value)
    return getVisibleCells().includes(cellId) && occupied.has(cellId)
  },
  resizeCell,
  moduleShopRef,
  currentView,
  navigateCamera,
  goToGrid,
  onWidgetMoved: (sourceCellId: number, targetCellId: number) => {
    moveWidgets({ sourceCellId, targetCellId });
    syncFocusedCell();
  },
  onWidgetDeleted: (cellId: number) => {
    clearCell(cellId);
    syncFocusedCell();
  },
});

// Cursor → focusedCellId: always tracks the cell under the index finger in edit mode.
// This makes pinch gestures always act on whatever the cursor is pointing at.
watch(indexFingerCursor, (pos) => {
  if (!pos || !isEditMode.value) return;
  const x = (pos.x / 100) * window.innerWidth;
  const y = (pos.y / 100) * window.innerHeight;
  const el = document.elementFromPoint(x, y);
  const cellEl = el?.closest('[data-cell-id]') as HTMLElement | null;
  if (!cellEl) return;
  const cellId = Number(cellEl.dataset['cellId']);
  if (!isNaN(cellId) && cellId !== focusedCellId.value) {
    focusedCellId.value = cellId;
  }
});

// Drag widget name for cursor label (reads __name from the Vue SFC component)
const dragWidgetName = computed<string | null>(() => {
  if (!isDragging.value || dragSourceCell.value === null) return null;
  const component = widgetMap.value[dragSourceCell.value] as any;
  return component?.__name ?? 'Widget';
});

// HUD: is the focused cell empty?
const focusedCellIsEmpty = computed(() =>
  availableCells.value.includes(focusedCellId.value)
);

const interactionState = useInteractionState({
  currentView,
  isEditMode,
  isShopOpen,
  isDragging,
  deleteConfirmPending: computed(() => deleteConfirmCell.value !== null),
  focusedCellIsEmpty,
});

const activeCameraName = computed(() => {
  const camera = cameras.value[currentIndex.value];
  return camera?.name ?? 'Backend camera';
});

const cameraDebugStatus = computed(() => {
  if (cameraError.value) return cameraError.value;
  if (cameraLoading.value) return 'loading';
  return frameUrl.value ? 'frame active' : 'waiting for frame';
});

const handleAddWidget = ({ cellId, component }: { cellId: number; component: any }) => {
  insertWidgetIntoCell(cellId, component);
  syncFocusedCell();
};

const handleWidgetsMoved = ({ sourceCellId, targetCellId }: { sourceCellId: number; targetCellId: number }) => {
  moveWidgets({ sourceCellId, targetCellId });
  syncFocusedCell();
};

const handleDeleteWidget = (cellId: number) => {
  clearCell(cellId);
  syncFocusedCell();
};

const handleConfirmDelete = (cellId: number) => {
  deleteConfirmCell.value = null;
  clearCell(cellId);
  syncFocusedCell();
};

const handleCancelDelete = () => {
  deleteConfirmCell.value = null;
};

// Keyboard shop navigation (mouse/keyboard fallback)
const handleShopNavigation = (key: string) => {
  if (isShopOpen.value && moduleShopRef.value) {
    if (key === 'ArrowRight') moduleShopRef.value.nextModule();
    else if (key === 'ArrowLeft') moduleShopRef.value.prevModule();
  }
};

setupKeyboardListener({
  onShopToggle: toggleShop,
  onShopNavigate: handleShopNavigation,
  onClockToggle: toggleClockMode,
});

watch(availableCells, () => { syncFocusedCell(); });

onMounted(() => {
  void initializeCamera();
  void (async () => {
    const reachable = await backendReachability.requestAvailabilityCheck();
    if (!reachable) return;

    void checkExternalApiHealth().catch((error) => {
      console.warn('External API health check failed', error);
    });
  })();
  syncFocusedCell();
  unsubscribeRealtime = realtimeClient.subscribe((event) => {
    recordRealtimeEvent(event);
    const handled = handleRealtimeEvent(event);
    if (event.eventType === 'UIActionRequested') {
      recordDispatchResult(event.payload as UIActionRequestedPayload, handled);
    }
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

    <!-- Finger cursor overlay (edit mode only) -->
    <GestureCursor
      v-if="isEditMode || isShopOpen"
      :cursor="indexFingerCursor"
      :is-dragging="isDragging"
      :drag-widget-name="dragWidgetName"
    />

    <!-- Gesture context HUD -->
    <GestureContextHUD
      :interaction-state="interactionState"
    />

    <GestureDebugPanel
      v-if="debugPanelVisible"
      :tracking-status="gestureDebugTrackingStatus"
      :last-gesture="gestureDebugLastGesture"
      :last-gesture-detail="gestureDebugLastGestureDetail"
      :last-command="gestureDebugLastCommand"
      :last-command-detail="gestureDebugLastCommandDetail"
      :last-action="gestureDebugLastAction"
      :last-action-detail="gestureDebugLastActionDetail"
      :last-dispatch="gestureDebugLastDispatch"
      :last-dispatch-detail="gestureDebugLastDispatchDetail"
      :interaction-state="interactionState"
      :camera-name="activeCameraName"
      :camera-status="cameraDebugStatus"
      :entries="gestureDebugEntries"
    />

    <button
      class="debug-toggle"
      type="button"
      :aria-pressed="debugPanelVisible"
      @click="debugPanelVisible = !debugPanelVisible"
    >
      Debug
    </button>

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
      />
    </Transition>

    <!-- Grid-Ansicht -->
    <Transition name="view-from-right">
      <div v-if="currentView === 'grid'" class="grid-view">

        <!-- Module Shop Popup -->
        <Transition name="shop-rise">
          <div v-if="isShopOpen" class="shop-overlay" @click.self="closeShop">
            <div class="shop-modal">
              <button class="close-btn" @click="closeShop" aria-label="Shop schließen">×</button>
              <ModuleShop ref="moduleShopRef" @addWidget="handleAddWidget" />
            </div>
          </div>
        </Transition>

        <GridBoard
          :is-edit-mode="isEditMode"
          :focused-cell-id="focusedCellId"
          :is-dragging="isDragging"
          :drag-source-cell="dragSourceCell"
          :delete-confirm-cell="deleteConfirmCell"
          @widgets-moved="handleWidgetsMoved"
          @delete-widget="handleDeleteWidget"
          @confirm-delete="handleConfirmDelete"
          @cancel-delete="handleCancelDelete"
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

.debug-toggle {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 1500;
  min-width: 72px;
  height: 34px;
  border: 1px solid rgba(148, 163, 184, 0.36);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.82);
  color: #e5e7eb;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  backdrop-filter: blur(10px);
}

.debug-toggle:hover {
  background: rgba(30, 41, 59, 0.92);
}

/* View-Transition: HomeScreen → Grid */
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

/* Shop modal */
.shop-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.72);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.shop-modal {
  position: relative;
  background: #111111;
  border-radius: 16px;
  padding: 20px;
  width: 92vw;
  max-width: 680px;
  height: 72vh;
  max-height: 560px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.75);
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 50%;
  color: rgba(255, 255, 255, 0.55);
  font-size: 22px;
  width: 32px;
  height: 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 180ms ease, color 180ms ease;
  z-index: 10;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff;
}

/* Shop entrance animation */
.shop-rise-enter-active,
.shop-rise-leave-active {
  transition: opacity 220ms ease;
}

.shop-rise-enter-active .shop-modal,
.shop-rise-leave-active .shop-modal {
  transition: transform 220ms cubic-bezier(0.4, 0, 0.2, 1), opacity 220ms ease;
}

.shop-rise-enter-from {
  opacity: 0;
}

.shop-rise-enter-from .shop-modal {
  transform: translateY(24px);
  opacity: 0;
}

.shop-rise-leave-to {
  opacity: 0;
}

.shop-rise-leave-to .shop-modal {
  transform: translateY(16px);
  opacity: 0;
}
</style>
