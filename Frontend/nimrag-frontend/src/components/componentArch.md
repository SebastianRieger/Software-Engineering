# Components Module Architecture Analysis

## Scope

- Snapshot basis: 6 files and 1249 lines in `src/components`
- Subtrees: `manager/` and `widgets/`

## Metric View

| Slice | Files | Lines | Reading |
| --- | ---: | ---: | --- |
| `manager/` | 3 | 789 | Layout orchestration, board rendering and widget selection |
| `widgets/` | 3 | 460 | Domain-facing widget UI |

### Largest Component Hotspots

| Component | Lines | Why it matters |
| --- | ---: | --- |
| `ModuleShop.vue` | 485 | Largest remaining interaction-heavy component |
| `TemplateWidget.vue` | 212 | Hardware and system UI surface, now backed by extracted helper logic |
| `ModuleManager.vue` | 203 | Frontend state and persistence orchestrator |

## Structure And Logic

The components layer still contains the main application flow, but not as monolithically as before. `ModuleManager.vue` owns layout state, loading and persistence. `GridBoard.vue` renders the 4x4 board. `ModuleShop.vue` handles widget selection. The widget components render the concrete weather, clock and hardware experiences.

The key change is that helper-heavy logic is no longer forced to live inline. Layout transformation and rendered-widget assembly were moved into `utils/layout.ts`, module-shop mechanics into `utils/moduleShop.ts`, and hardware-widget integration logic into `utils/hardwareWidget.ts`.

## Critical Assessment

- The state-driven rendering model remains the right structural base.
- `manager/` still does more than presentation. It mixes application state, persistence choreography and UI control flow.
- `widgets/` provides good feature isolation, but the hardware widget still consumes service behavior directly through its helper layer instead of a shared state layer.
- The biggest remaining pressure point is `ModuleShop.vue`, followed by broader frontend state ownership rather than raw component size alone.

## Intended But Missing Elements

- composables or stores to move layout and widget state above `ModuleManager.vue`
- clearer split between presentation components and feature orchestration
- automated component tests

## Diagram

```mermaid
flowchart LR
    ModuleManager[ModuleManager.vue]
    GridBoard[GridBoard.vue]
    ModuleShop[ModuleShop.vue]
    WeatherWidget[WeatherWidget.vue]
    ClockWidget[ClockWidget.vue]
    TemplateWidget[TemplateWidget.vue]
    Registry[widgets/registry.ts]
    Utils[utils layer]
    Services[services]
    PlannedState[Planned stores or composables]

    ModuleManager --> GridBoard
    ModuleManager --> ModuleShop
    ModuleManager --> Registry
    ModuleManager --> Utils
    GridBoard --> WeatherWidget
    GridBoard --> ClockWidget
    GridBoard --> TemplateWidget
    TemplateWidget --> Utils
    WeatherWidget --> Services
    Utils --> Services
    ModuleManager -. intended extraction .-> PlannedState
```

## Navigation

- Parent: `../frontendArch.md`
