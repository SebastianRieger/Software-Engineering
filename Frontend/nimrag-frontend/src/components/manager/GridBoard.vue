<script setup lang="ts">
import { computed } from 'vue'

import type { FocusState } from '../../types/interactions'
import type { RenderedWidgetList } from '../../types/widgets'
import { GRID_COLUMNS, GRID_ROWS, widgetOccupiesCell } from '../../utils/layout'

const props = defineProps<{
  widgets: RenderedWidgetList
  focusedCell: FocusState
  selectedWidgetId: string | null
  isArrangeMode: boolean
}>()

const emit = defineEmits<{
  focusCell: [payload: { row: number; col: number }]
  focusWidget: [payload: { widgetId: string; row: number; col: number }]
  resizeWidget: [payload: { widgetId: string; mode: 'expand' | 'shrink' }]
  deleteWidget: [payload: { widgetId: string }]
}>()

const cells = computed(() => {
  return Array.from({ length: GRID_ROWS * GRID_COLUMNS }, (_, index) => {
    const row = Math.floor(index / GRID_COLUMNS) + 1
    const col = (index % GRID_COLUMNS) + 1
    const widget = props.widgets.find((entry) => widgetOccupiesCell(entry, row, col)) ?? null
    return {
      row,
      col,
      label: String(((row - 1) * GRID_COLUMNS) + col).padStart(2, '0'),
      widget,
    }
  })
})

function widgetStyle(row: number, col: number, rowSpan: number, colSpan: number): Record<string, string> {
  return {
    gridColumn: `${col} / span ${colSpan}`,
    gridRow: `${row} / span ${rowSpan}`,
  }
}

function showWidgetActions(widgetId: string): boolean {
  return props.selectedWidgetId === widgetId || props.focusedCell.widgetId === widgetId
}
</script>

<template>
  <section class="board-shell">
    <div class="grid-surface">
      <button
        v-for="cell in cells"
        :key="`${cell.row}-${cell.col}`"
        class="grid-cell"
        :class="{
          'is-focused': focusedCell.row === cell.row && focusedCell.col === cell.col,
          'is-occupied': Boolean(cell.widget),
          'is-arrange-target': isArrangeMode && selectedWidgetId === cell.widget?.widget_id,
        }"
        @click="emit('focusCell', { row: cell.row, col: cell.col })"
      >
        <span class="cell-label">{{ cell.label }}</span>
      </button>

      <article
        v-for="widget in widgets"
        :key="widget.widget_id"
        class="widget-card"
        :class="{
          'is-focused': focusedCell.widgetId === widget.widget_id,
          'is-selected': selectedWidgetId === widget.widget_id,
          'is-arranging': isArrangeMode && selectedWidgetId === widget.widget_id,
        }"
        :style="widgetStyle(widget.row, widget.col, widget.row_span, widget.col_span)"
        @click.stop="emit('focusWidget', { widgetId: widget.widget_id, row: widget.row, col: widget.col })"
      >
        <header class="widget-meta">
          <div class="widget-heading">
            <span class="widget-title">{{ widget.title ?? widget.widget_type }}</span>
            <span class="widget-size">{{ widget.row_span }}x{{ widget.col_span }}</span>
          </div>

          <div v-if="showWidgetActions(widget.widget_id)" class="widget-actions">
            <button
              type="button"
              class="widget-action"
              data-action="resize-shrink"
              title="Widget verkleinern"
              @click.stop="emit('resizeWidget', { widgetId: widget.widget_id, mode: 'shrink' })"
            >
              -
            </button>

            <button
              type="button"
              class="widget-action"
              data-action="resize-expand"
              title="Widget vergroessern"
              @click.stop="emit('resizeWidget', { widgetId: widget.widget_id, mode: 'expand' })"
            >
              +
            </button>

            <button
              type="button"
              class="widget-action is-danger"
              data-action="delete-widget"
              title="Widget entfernen"
              @click.stop="emit('deleteWidget', { widgetId: widget.widget_id })"
            >
              x
            </button>
          </div>
        </header>

        <component
          :is="widget.component"
          v-bind="widget.widgetProps ?? {}"
          class="widget-body"
        />
      </article>
    </div>
  </section>
</template>

<style scoped>
.board-shell {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(239, 68, 68, 0.16), transparent 32%),
    radial-gradient(circle at bottom right, rgba(56, 189, 248, 0.18), transparent 30%),
    linear-gradient(160deg, #080a12 0%, #111827 45%, #030712 100%);
}

.grid-surface {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-rows: repeat(4, minmax(140px, 1fr));
  gap: 14px;
  min-height: calc(100vh - 48px);
}

.grid-cell {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 24px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.92), rgba(2, 6, 23, 0.84));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 10px 12px;
  color: rgba(226, 232, 240, 0.6);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.grid-cell.is-focused {
  border-color: rgba(251, 191, 36, 0.9);
  box-shadow: 0 0 0 1px rgba(251, 191, 36, 0.9), 0 0 0 10px rgba(251, 191, 36, 0.08);
}

.grid-cell.is-occupied {
  border-style: dashed;
}

.grid-cell.is-arrange-target {
  border-color: rgba(74, 222, 128, 0.7);
}

.cell-label {
  font-size: 0.8rem;
  letter-spacing: 0.12em;
}

.widget-card {
  border-radius: 28px;
  overflow: hidden;
  background: linear-gradient(160deg, rgba(15, 23, 42, 0.98), rgba(15, 118, 110, 0.18));
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 28px 48px rgba(2, 6, 23, 0.4);
  display: flex;
  flex-direction: column;
  min-height: 0;
  z-index: 2;
  transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.widget-card.is-focused {
  transform: translateY(-2px);
  border-color: rgba(248, 250, 252, 0.45);
}

.widget-card.is-selected,
.widget-card.is-arranging {
  border-color: rgba(74, 222, 128, 0.9);
  box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.7), 0 24px 48px rgba(21, 128, 61, 0.18);
}

.widget-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px 8px;
  color: rgba(226, 232, 240, 0.9);
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.widget-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.widget-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.widget-size {
  opacity: 0.7;
}

.widget-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.widget-action {
  width: 28px;
  height: 28px;
  border: 1px solid rgba(226, 232, 240, 0.16);
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: rgba(248, 250, 252, 0.92);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.9rem;
  line-height: 1;
  transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
}

.widget-action:hover {
  transform: translateY(-1px);
  border-color: rgba(248, 250, 252, 0.4);
  background: rgba(30, 41, 59, 0.92);
}

.widget-action.is-danger:hover {
  border-color: rgba(248, 113, 113, 0.58);
  background: rgba(127, 29, 29, 0.9);
}

.widget-body {
  flex: 1;
  min-height: 0;
}

@media (max-width: 900px) {
  .board-shell {
    padding: 14px;
  }

  .grid-surface {
    gap: 10px;
    grid-template-rows: repeat(4, minmax(110px, 1fr));
  }
}
</style>
