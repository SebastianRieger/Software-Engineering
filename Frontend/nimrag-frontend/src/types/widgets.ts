import type { Component, ComponentPublicInstance } from 'vue'

import type { WidgetConfig } from './config'

export interface ModuleShopExposed {
  nextModule: () => void
  prevModule: () => void
  setCurrentModule: (index: number) => void
  getCurrentModuleType: () => string | null
}

export type ModuleShopRef = ComponentPublicInstance<object, ModuleShopExposed> | null

export type ActiveWidgetMap = Record<string, WidgetConfig>

export interface RenderedWidget extends WidgetConfig {
  component: Component | null
  widgetProps?: Record<string, unknown>
}

export type RenderedWidgetList = RenderedWidget[]