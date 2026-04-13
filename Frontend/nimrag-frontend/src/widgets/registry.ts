import type { Component } from 'vue'

import ClockWidget from '../components/widgets/ClockWidget.vue'
import TemplateWidget from '../components/widgets/TemplateWidget.vue'
import WeatherWidget from '../components/widgets/WeatherWidget.vue'

export type WidgetType = 'clock' | 'template' | 'weather'

export interface WidgetDefinition {
  type: WidgetType
  name: string
  defaultTitle: string
  component: Component
}

const widgetDefinitions: WidgetDefinition[] = [
  {
    type: 'clock',
    name: 'Clock',
    defaultTitle: 'Uhr',
    component: ClockWidget,
  },
  {
    type: 'weather',
    name: 'Weather',
    defaultTitle: 'Wetter',
    component: WeatherWidget,
  },
  {
    type: 'template',
    name: 'Template',
    defaultTitle: 'Template',
    component: TemplateWidget,
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