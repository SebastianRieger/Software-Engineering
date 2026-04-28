# Types Module Architecture Analysis

## Scope

- Snapshot basis: 5 files and 182 lines in `src/types`
- Files: `config.ts`, `hardware.ts`, `interactions.ts`, `weather.ts`, `widgets.ts`

## Metric View

| File | Lines | Responsibility |
| --- | ---: | --- |
| `config.ts` | 57 | Placement-based layout and system configuration contracts |
| `hardware.ts` | 56 | Realtime and hardware-oriented event or status types |
| `interactions.ts` | 35 | Semantic UI-action and raw gesture event types |
| `widgets.ts` | 20 | Frontend widget-rendering and shop-exposure types |
| `weather.ts` | 14 | Weather response types |

## Structure And Logic

The types module is still the frontend contract mirror of the backend, but it now also stabilizes frontend-specific widget wiring and interaction semantics. `api.ts`, `realtime.ts`, the widget components and the extracted helper layer all depend on these local TypeScript models.

The most important new file is `interactions.ts`. It mirrors the new backend distinction between raw gesture recognition and modality-neutral UI actions. Together with the expanded placement fields in `config.ts`, this gives the frontend a typed base for focus navigation, shop toggling and ArrangeMode behavior. This keeps the frontend typed without a generated shared schema package. It also creates an explicit maintenance obligation: backend contract changes still need to be mirrored manually here.

## Critical Assessment

- Type coverage is strong relative to the size of the frontend.
- Adding `widgets.ts` and `interactions.ts` was a useful separation because widget-rendering and interaction types no longer have to hide inside components.
- Manual synchronization with backend Pydantic schemas remains the main architectural risk.
- As more domains arrive, the lack of generated or shared contracts will become more expensive.

## Intended But Missing Elements

- generated or shared contracts across backend and frontend
- additional domain types once calendar and smart-home flows become real in the UI
- stronger separation between transport types and richer frontend view models if UI logic grows further

## Diagram

```mermaid
flowchart LR
    BackendSchemas[Backend schemas]
    Types[frontend types]
    ApiClient[api.ts]
    Realtime[realtime.ts]
    Components[components]
    Utils[utils]
    UIActions[interaction semantics]
    PlannedContracts[Planned shared or generated contracts]

    BackendSchemas -. mirrored manually .-> Types
    Types --> ApiClient
    Types --> Realtime
    Types --> Components
    Types --> Utils
    Types --> UIActions
    Types -. intended evolution .-> PlannedContracts
```

## Navigation

- Parent: `../frontendArch.md`
