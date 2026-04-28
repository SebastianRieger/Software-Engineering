import { ApiError } from '../services/api'
import type { LayoutConfig, SystemConfig, WidgetConfig, WidgetSettings } from '../types/config'
import type { ActiveWidgetMap, RenderedWidget, RenderedWidgetMap } from '../types/widgets'
import { getWidgetDefaultSettings, getWidgetDefinition } from '../widgets/registry'

export function formatApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return fallback
}

export function normalizeWidget(widget: WidgetConfig): WidgetConfig | null {
  if (widget.cell_id < 1 || widget.cell_id > 16) {
    return null
  }

  return {
    ...widget,
    title: widget.title ?? getWidgetDefinition(widget.widget_type)?.defaultTitle ?? null,
    settings: widget.settings ?? {},
  }
}

export function applyLoadedLayout(layout: LayoutConfig): ActiveWidgetMap {
  const nextWidgets: ActiveWidgetMap = {}
  layout.widgets.forEach((widget) => {
    const normalizedWidget = normalizeWidget(widget)
    if (!normalizedWidget) {
      return
    }

    nextWidgets[normalizedWidget.cell_id] = normalizedWidget
  })
  return nextWidgets
}

export function buildLayoutPayload(activeWidgets: ActiveWidgetMap): LayoutConfig {
  const widgets = Object.values(activeWidgets).sort((left, right) => left.cell_id - right.cell_id)
  return {
    version: 1,
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
): RenderedWidgetMap {
  return Object.fromEntries(
    Object.values(activeWidgets).map((widget) => {
      const widgetDefinition = getWidgetDefinition(widget.widget_type)
      const renderedWidget: RenderedWidget = {
        ...widget,
        component: widgetDefinition?.component ?? null,
        widgetProps: buildWidgetProps(widget, systemConfig, updateWidgetSettings),
      }

      return [widget.cell_id, renderedWidget]
    }),
  ) as RenderedWidgetMap
}

export function upsertWidget(activeWidgets: ActiveWidgetMap, cellId: number, widgetType: string): ActiveWidgetMap {
  const widgetDefinition = getWidgetDefinition(widgetType)
  if (!widgetDefinition) {
    throw new Error(`Unbekannter Widget-Typ: ${widgetType}`)
  }

  const existingWidget = activeWidgets[cellId]
  return {
    ...activeWidgets,
    [cellId]: {
      widget_id: existingWidget?.widget_id ?? `${widgetType}-${cellId}-${Date.now()}`,
      widget_type: widgetType,
      cell_id: cellId,
      title: widgetDefinition.defaultTitle,
      settings: existingWidget?.widget_type === widgetType
        ? existingWidget.settings
        : getWidgetDefaultSettings(widgetType),
    },
  }
}

export function moveWidget(activeWidgets: ActiveWidgetMap, sourceCellId: number, targetCellId: number): ActiveWidgetMap {
  const sourceWidget = activeWidgets[sourceCellId]
  if (!sourceWidget) {
    return activeWidgets
  }

  const targetWidget = activeWidgets[targetCellId]
  const nextWidgets: ActiveWidgetMap = { ...activeWidgets }

  if (targetWidget) {
    nextWidgets[sourceCellId] = { ...targetWidget, cell_id: sourceCellId }
  } else {
    delete nextWidgets[sourceCellId]
  }

  nextWidgets[targetCellId] = { ...sourceWidget, cell_id: targetCellId }
  return nextWidgets
}