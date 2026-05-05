import { ApiError } from '../services/api'
import type { LayoutConfig, SystemConfig, WidgetConfig, WidgetSettings } from '../types/config'
import type { FocusState } from '../types/interactions'
import type { ActiveWidgetMap, RenderedWidget, RenderedWidgetList } from '../types/widgets'
import { getWidgetDefaultSettings, getWidgetDefinition } from '../widgets/registry'

export const GRID_ROWS = 4
export const GRID_COLUMNS = 4
const RESIZE_STEPS = [1, 2, 3] as const

export function formatApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return fallback
}

export function positionToCellId(row: number, col: number): number {
  return ((row - 1) * GRID_COLUMNS) + col
}

export function cellIdToPosition(cellId: number): { row: number; col: number } {
  const zeroBasedCell = cellId - 1
  return {
    row: Math.floor(zeroBasedCell / GRID_COLUMNS) + 1,
    col: (zeroBasedCell % GRID_COLUMNS) + 1,
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function clampWidget(widget: WidgetConfig): WidgetConfig {
  const row = clamp(widget.row, 1, GRID_ROWS)
  const col = clamp(widget.col, 1, GRID_COLUMNS)
  const rowSpan = clamp(widget.row_span, 1, GRID_ROWS - row + 1)
  const colSpan = clamp(widget.col_span, 1, GRID_COLUMNS - col + 1)

  return {
    ...widget,
    row,
    col,
    row_span: rowSpan,
    col_span: colSpan,
    cell_id: positionToCellId(row, col),
  }
}

export function normalizeWidget(widget: WidgetConfig): WidgetConfig | null {
  const fallbackPosition = widget.cell_id != null ? cellIdToPosition(widget.cell_id) : { row: 1, col: 1 }
  const widgetDefinition = getWidgetDefinition(widget.widget_type)
  if (!widgetDefinition) {
    return null
  }

  return clampWidget({
    ...widget,
    row: Number.isFinite(widget.row) ? widget.row : fallbackPosition.row,
    col: Number.isFinite(widget.col) ? widget.col : fallbackPosition.col,
    row_span: widget.row_span ?? 1,
    col_span: widget.col_span ?? 1,
    title: widget.title ?? widgetDefinition.defaultTitle,
    settings: widget.settings ?? {},
  })
}

export function widgetOccupiesCell(widget: Pick<WidgetConfig, 'row' | 'col' | 'row_span' | 'col_span'>, row: number, col: number): boolean {
  return row >= widget.row
    && row < widget.row + widget.row_span
    && col >= widget.col
    && col < widget.col + widget.col_span
}

function widgetsOverlap(
  left: Pick<WidgetConfig, 'row' | 'col' | 'row_span' | 'col_span'>,
  right: Pick<WidgetConfig, 'row' | 'col' | 'row_span' | 'col_span'>,
): boolean {
  return left.row < right.row + right.row_span
    && left.row + left.row_span > right.row
    && left.col < right.col + right.col_span
    && left.col + left.col_span > right.col
}

export function findWidgetAtCell(activeWidgets: ActiveWidgetMap, row: number, col: number): WidgetConfig | null {
  return Object.values(activeWidgets).find((widget) => widgetOccupiesCell(widget, row, col)) ?? null
}

export function isCellEmpty(activeWidgets: ActiveWidgetMap, row: number, col: number): boolean {
  return findWidgetAtCell(activeWidgets, row, col) == null
}

export function canPlaceWidget(activeWidgets: ActiveWidgetMap, candidate: WidgetConfig, ignoreWidgetId?: string): boolean {
  const clampedCandidate = clampWidget(candidate)
  if (clampedCandidate.row !== candidate.row || clampedCandidate.col !== candidate.col) {
    return false
  }
  if (clampedCandidate.row_span !== candidate.row_span || clampedCandidate.col_span !== candidate.col_span) {
    return false
  }

  return Object.values(activeWidgets).every((widget) => {
    if (widget.widget_id === ignoreWidgetId) {
      return true
    }
    return !widgetsOverlap(widget, candidate)
  })
}

function findFirstAvailablePlacement(activeWidgets: ActiveWidgetMap, rowSpan: number, colSpan: number): { row: number; col: number } | null {
  for (let row = 1; row <= GRID_ROWS - rowSpan + 1; row += 1) {
    for (let col = 1; col <= GRID_COLUMNS - colSpan + 1; col += 1) {
      const probe: WidgetConfig = {
        widget_id: '__probe__',
        widget_type: '__probe__',
        row,
        col,
        row_span: rowSpan,
        col_span: colSpan,
        cell_id: positionToCellId(row, col),
        title: null,
        settings: {},
      }
      if (canPlaceWidget(activeWidgets, probe)) {
        return { row, col }
      }
    }
  }
  return null
}

export function applyLoadedLayout(layout: LayoutConfig): ActiveWidgetMap {
  const nextWidgets: ActiveWidgetMap = {}

  layout.widgets.forEach((widget) => {
    const normalizedWidget = normalizeWidget(widget)
    if (!normalizedWidget) {
      return
    }

    if (canPlaceWidget(nextWidgets, normalizedWidget)) {
      nextWidgets[normalizedWidget.widget_id] = normalizedWidget
      return
    }

    const fallbackPlacement = findFirstAvailablePlacement(nextWidgets, normalizedWidget.row_span, normalizedWidget.col_span)
    if (!fallbackPlacement) {
      return
    }

    nextWidgets[normalizedWidget.widget_id] = {
      ...normalizedWidget,
      row: fallbackPlacement.row,
      col: fallbackPlacement.col,
      cell_id: positionToCellId(fallbackPlacement.row, fallbackPlacement.col),
    }
  })

  return nextWidgets
}

export function buildLayoutPayload(activeWidgets: ActiveWidgetMap): LayoutConfig {
  const widgets = Object.values(activeWidgets)
    .map((widget) => clampWidget(widget))
    .sort((left, right) => positionToCellId(left.row, left.col) - positionToCellId(right.row, right.col))

  return {
    version: 2,
    widgets,
    updated_at: null,
  }
}

function buildWidgetProps(
  widget: WidgetConfig,
  systemConfig: SystemConfig | null,
  updateWidgetSettings: (widgetId: string, nextSettingsPatch: WidgetSettings) => void,
): Record<string, unknown> | undefined {
  if (widget.widget_type === 'weather') {
    return { initialSystemConfig: systemConfig }
  }

  if (widget.widget_type === 'clock' || widget.widget_type === 'template') {
    return {
      widgetId: widget.widget_id,
      settings: widget.settings,
      updateSettings: (nextSettingsPatch: WidgetSettings) => updateWidgetSettings(widget.widget_id, nextSettingsPatch),
    }
  }

  return undefined
}

export function buildRenderedWidgets(
  activeWidgets: ActiveWidgetMap,
  systemConfig: SystemConfig | null,
  updateWidgetSettings: (widgetId: string, nextSettingsPatch: WidgetSettings) => void,
): RenderedWidgetList {
  return Object.values(activeWidgets)
    .map((widget) => {
      const widgetDefinition = getWidgetDefinition(widget.widget_type)
      const renderedWidget: RenderedWidget = {
        ...widget,
        component: widgetDefinition?.component ?? null,
        widgetProps: buildWidgetProps(widget, systemConfig, updateWidgetSettings),
      }

      return renderedWidget
    })
    .sort((left, right) => positionToCellId(left.row, left.col) - positionToCellId(right.row, right.col))
}

export function patchWidgetSettings(activeWidgets: ActiveWidgetMap, widgetId: string, nextSettingsPatch: WidgetSettings): ActiveWidgetMap {
  const widget = activeWidgets[widgetId]
  if (!widget) {
    return activeWidgets
  }

  return {
    ...activeWidgets,
    [widgetId]: {
      ...widget,
      settings: {
        ...widget.settings,
        ...nextSettingsPatch,
      },
    },
  }
}

export function removeWidget(activeWidgets: ActiveWidgetMap, widgetId: string): ActiveWidgetMap {
  if (!activeWidgets[widgetId]) {
    return activeWidgets
  }

  const nextWidgets = { ...activeWidgets }
  delete nextWidgets[widgetId]
  return nextWidgets
}

export function createFocusState(row: number, col: number, activeWidgets: ActiveWidgetMap): FocusState {
  const nextRow = clamp(row, 1, GRID_ROWS)
  const nextCol = clamp(col, 1, GRID_COLUMNS)
  const widget = findWidgetAtCell(activeWidgets, nextRow, nextCol)

  return {
    row: nextRow,
    col: nextCol,
    widgetId: widget?.widget_id ?? null,
  }
}

export function getDefaultFocus(activeWidgets: ActiveWidgetMap): FocusState {
  const firstWidget = Object.values(activeWidgets)
    .sort((left, right) => positionToCellId(left.row, left.col) - positionToCellId(right.row, right.col))[0]
  if (!firstWidget) {
    return createFocusState(1, 1, activeWidgets)
  }

  return createFocusState(firstWidget.row, firstWidget.col, activeWidgets)
}

export function getFocusStateForWidget(activeWidgets: ActiveWidgetMap, widgetId: string): FocusState {
  const widget = activeWidgets[widgetId]
  if (!widget) {
    return createFocusState(1, 1, activeWidgets)
  }

  return createFocusState(widget.row, widget.col, activeWidgets)
}

export function moveFocus(activeWidgets: ActiveWidgetMap, focus: FocusState, rowOffset: number, colOffset: number): FocusState {
  return createFocusState(focus.row + rowOffset, focus.col + colOffset, activeWidgets)
}

export function upsertWidget(activeWidgets: ActiveWidgetMap, focus: FocusState, widgetType: string): ActiveWidgetMap {
  const widgetDefinition = getWidgetDefinition(widgetType)
  if (!widgetDefinition) {
    throw new Error(`Unbekannter Widget-Typ: ${widgetType}`)
  }

  if (!isCellEmpty(activeWidgets, focus.row, focus.col)) {
    throw new Error('Die Fokuszelle ist bereits belegt.')
  }

  const widget = clampWidget({
    widget_id: `${widgetType}-${focus.row}-${focus.col}-${Date.now()}`,
    widget_type: widgetType,
    row: focus.row,
    col: focus.col,
    row_span: 1,
    col_span: 1,
    cell_id: positionToCellId(focus.row, focus.col),
    title: widgetDefinition.defaultTitle,
    settings: getWidgetDefaultSettings(widgetType),
  })

  if (!canPlaceWidget(activeWidgets, widget)) {
    throw new Error('Widget konnte an dieser Position nicht platziert werden.')
  }

  return {
    ...activeWidgets,
    [widget.widget_id]: widget,
  }
}

export function moveWidgetByOffset(activeWidgets: ActiveWidgetMap, widgetId: string, rowOffset: number, colOffset: number): ActiveWidgetMap {
  const widget = activeWidgets[widgetId]
  if (!widget) {
    return activeWidgets
  }

  const nextWidget = {
    ...widget,
    row: widget.row + rowOffset,
    col: widget.col + colOffset,
    cell_id: positionToCellId(widget.row + rowOffset, widget.col + colOffset),
  }

  if (!canPlaceWidget(activeWidgets, nextWidget, widgetId)) {
    return activeWidgets
  }

  return {
    ...activeWidgets,
    [widgetId]: nextWidget,
  }
}

export function resizeWidget(activeWidgets: ActiveWidgetMap, widgetId: string, mode: 'expand' | 'shrink'): ActiveWidgetMap {
  const widget = activeWidgets[widgetId]
  if (!widget) {
    return activeWidgets
  }

  const currentIndex = RESIZE_STEPS.indexOf(widget.row_span as (typeof RESIZE_STEPS)[number])
  const safeIndex = currentIndex === -1 ? 0 : currentIndex
  const nextIndex = mode === 'expand'
    ? Math.min(safeIndex + 1, RESIZE_STEPS.length - 1)
    : Math.max(safeIndex - 1, 0)
  const nextSize = RESIZE_STEPS[nextIndex] ?? widget.row_span

  if (nextSize === widget.row_span && nextSize === widget.col_span) {
    return activeWidgets
  }

  const nextWidget = {
    ...widget,
    row_span: nextSize,
    col_span: nextSize,
  }

  if (!canPlaceWidget(activeWidgets, nextWidget, widgetId)) {
    return activeWidgets
  }

  return {
    ...activeWidgets,
    [widgetId]: nextWidget,
  }
}

export function getWidgetDisplayTitle(widget: WidgetConfig | null | undefined): string {
  if (!widget) {
    return 'Leer'
  }

  return widget.title ?? getWidgetDefinition(widget.widget_type)?.defaultTitle ?? widget.widget_type
}
