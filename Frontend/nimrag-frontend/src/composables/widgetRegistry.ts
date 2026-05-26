import { markRaw } from 'vue'
import type { Component } from 'vue'

/**
 * Eagerly loads all widget components from the widgets directory.
 * This runs once at build/module-load time and provides a bidirectional
 * name ↔ component mapping used for localStorage serialization.
 *
 * name  = filename without .vue extension (e.g. "ClockWidget")
 */
const modules = import.meta.glob('../components/widgets/*.vue', { eager: true })

const nameToComponent = new Map<string, Component>()
const componentToName = new Map<Component, string>()

for (const path in modules) {
  const name = path.split('/').pop()?.replace('.vue', '') ?? ''
  const component = markRaw((modules[path] as { default: Component }).default)
  nameToComponent.set(name, component)
  componentToName.set(component, name)
}

/**
 * Returns the Component for a given widget name, or undefined if unknown.
 */
export function getWidgetComponent(name: string): Component | undefined {
  return nameToComponent.get(name)
}

/**
 * Returns the widget name (filename stem) for a given component reference.
 * Returns undefined for components not in the widgets directory (e.g. test mocks).
 */
export function getWidgetName(component: Component): string | undefined {
  return componentToName.get(component)
}
