# Utils Module Architecture Analysis

## Scope

- Snapshot basis: 3 code files and 414 code lines in `src/utils`
- Files: `layout.ts`, `hardwareWidget.ts`, `moduleShop.ts`

## Metric View

| File | Lines | Responsibility |
| --- | ---: | --- |
| `hardwareWidget.ts` | 234 | Hardware-widget integration logic, realtime handling and control helpers |
| `layout.ts` | 127 | Layout normalization, payload building and rendered-widget assembly |
| `moduleShop.ts` | 53 | Module list, selection and carousel helper logic |

## Reading The Module

`utils/` is now the first real frontend helper layer instead of a reserved folder. The extracted files are all tied to one concrete goal: reduce the amount of orchestration logic living inline in `ModuleManager.vue`, `TemplateWidget.vue` and `ModuleShop.vue`.

This is a pragmatic intermediate step. It does not replace a future shared state or composable layer, but it gives repeated logic a stable home and makes the component layer easier to read.

## Critical Assessment

- The new helper layer is small but immediately valuable.
- `layout.ts` and `moduleShop.ts` are pure enough to be good future test targets.
- `hardwareWidget.ts` is a useful extraction, but it already behaves like a composable-style integration layer and may want a more explicit frontend-state home later.
- The module now reduces architecture debt instead of merely signaling it.

## Intended But Missing Elements

- formatting helpers for display values and timestamps once UI richness grows
- test coverage for the extracted pure helpers
- possible evolution from helper modules to shared composables or domain state modules

## Diagram

```mermaid
flowchart LR
    Utils[utils]
    Layout[layout.ts]
    Hardware[hardwareWidget.ts]
    Shop[moduleShop.ts]
    Components[components]
    Services[services]
    PlannedState[Planned shared state or composables]

    Utils --> Layout
    Utils --> Hardware
    Utils --> Shop
    Components --> Utils
    Layout --> Services
    Hardware --> Services
    Shop --> Components
    Hardware -. possible evolution .-> PlannedState
```

## Navigation

- Parent: `../frontendArch.md`
