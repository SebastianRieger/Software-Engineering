import { computed, type ComputedRef, type Ref } from 'vue'

export type InteractionState =
  | 'home'
  | 'grid-idle'
  | 'edit-empty'
  | 'edit-widget'
  | 'dragging'
  | 'shop'
  | 'delete-confirm'

export interface InteractionStateSnapshot {
  currentView: 'home' | 'grid'
  isEditMode: boolean
  isShopOpen: boolean
  isDragging: boolean
  deleteConfirmPending: boolean
  focusedCellIsEmpty: boolean
}

export function resolveInteractionState(snapshot: InteractionStateSnapshot): InteractionState {
  if (snapshot.isShopOpen) return 'shop'
  if (snapshot.isDragging) return 'dragging'
  if (snapshot.deleteConfirmPending) return 'delete-confirm'
  if (snapshot.currentView === 'home' && !snapshot.isEditMode) return 'home'
  if (!snapshot.isEditMode) return 'grid-idle'
  if (snapshot.focusedCellIsEmpty) return 'edit-empty'
  return 'edit-widget'
}

export function useInteractionState(options: {
  currentView: Ref<'home' | 'grid'>
  isEditMode: Ref<boolean>
  isShopOpen: Ref<boolean>
  isDragging: Ref<boolean>
  deleteConfirmPending: Ref<boolean>
  focusedCellIsEmpty: ComputedRef<boolean> | Ref<boolean>
}): ComputedRef<InteractionState> {
  return computed(() => resolveInteractionState({
    currentView: options.currentView.value,
    isEditMode: options.isEditMode.value,
    isShopOpen: options.isShopOpen.value,
    isDragging: options.isDragging.value,
    deleteConfirmPending: options.deleteConfirmPending.value,
    focusedCellIsEmpty: options.focusedCellIsEmpty.value,
  }))
}
