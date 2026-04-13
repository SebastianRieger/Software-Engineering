import type { Component } from 'vue'

import type { WidgetSettings } from '../types/config'
import ClockWidget from '../components/widgets/ClockWidget.vue'
import TemplateWidget from '../components/widgets/TemplateWidget.vue'
import WeatherWidget from '../components/widgets/WeatherWidget.vue'

export type WidgetType = 'clock' | 'template' | 'weather'

export interface WidgetDefinition {
  type: WidgetType
  name: string
  defaultTitle: string
  component: Component
  defaultSettings: WidgetSettings
}

const widgetDefinitions: WidgetDefinition[] = [
  {
    type: 'clock',
    name: 'Clock',
    defaultTitle: 'Uhr',
    component: ClockWidget,
    defaultSettings: {
      format: '24h',
      showSeconds: true,
      timezoneMode: 'browser',
    },
  },
  {
    type: 'weather',
    name: 'Weather',
    defaultTitle: 'Wetter',
    component: WeatherWidget,
    defaultSettings: {},
  },
  {
    type: 'template',
    name: 'Hardware',
    defaultTitle: 'Hardware',
    component: TemplateWidget,
    defaultSettings: {
      showPreview: false,
      autoRefresh: true,
    },
  },
]

const widgetDefinitionMap = new Map(
  widgetDefinitions.map((widgetDefinition) => [widgetDefinition.type, widgetDefinition]),
)

export function listWidgetDefinitions(): WidgetDefinition[] {
  return widgetDefinitions
}

export function getWidgetDefinition(widgetType: string): WidgetDefinition | undefined {
  return widgetDefinitionMap.get(widgetType as WidgetType)
}

export function getWidgetDefaultSettings(widgetType: string): WidgetSettings {
  return { ...(getWidgetDefinition(widgetType)?.defaultSettings ?? {}) }
}