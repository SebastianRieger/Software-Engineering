import { describe, expect, it } from 'vitest'

import { resolveInteractionState } from '../../composables/useInteractionState'

const base = {
  currentView: 'grid' as const,
  isEditMode: false,
  isShopOpen: false,
  isDragging: false,
  deleteConfirmPending: false,
  focusedCellIsEmpty: true,
}

describe('resolveInteractionState', () => {
  it('distinguishes home, grid idle, and edit cell states', () => {
    expect(resolveInteractionState({ ...base, currentView: 'home' })).toBe('home')
    expect(resolveInteractionState(base)).toBe('grid-idle')
    expect(resolveInteractionState({ ...base, isEditMode: true })).toBe('edit-empty')
    expect(resolveInteractionState({ ...base, isEditMode: true, focusedCellIsEmpty: false })).toBe('edit-widget')
  })

  it('prioritizes modal and transient states over base view state', () => {
    expect(resolveInteractionState({ ...base, currentView: 'home', isShopOpen: true })).toBe('shop')
    expect(resolveInteractionState({ ...base, isDragging: true })).toBe('dragging')
    expect(resolveInteractionState({ ...base, deleteConfirmPending: true })).toBe('delete-confirm')
  })
})