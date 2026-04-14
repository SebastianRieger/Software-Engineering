import type { Component, ComponentPublicInstance } from 'vue'

import type { WidgetConfig } from './config'

export interface ModuleShopExposed {
  nextModule: () => void
  prevModule: () => void
}

export type ModuleShopRef = ComponentPublicInstance<{}, ModuleShopExposed> | null

export type ActiveWidgetMap = Record<number, WidgetConfig>

export interface RenderedWidget extends WidgetConfig {
  component: Component | null
  widgetProps?: Record<string, unknown>
}

export type RenderedWidgetMap = Record<number, RenderedWidget>