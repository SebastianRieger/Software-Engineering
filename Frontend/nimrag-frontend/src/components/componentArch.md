# Components Module Architecture Analysis

## Scope

- Snapshot basis: 8 Vue files and 2182 lines in `src/components`
- Subtrees: `manager/` and `widgets/`

## Metric View

| Component | Lines | Why it matters |
| --- | ---: | --- |
| `ModuleManager.vue` | 718 | Central interaction controller for layout, shop, ArrangeMode, realtime and calibration state |
| `CalibrationWizard.vue` | 431 | Dedicated in-app calibration flow with review, apply and rollback actions |
| `ModuleShop.vue` | 279 | Widget insertion flow |
| `TemplateWidget.vue` | 252 | Hardware and system UI surface with camera and microphone selection |
| `GridBoard.vue` | 195 | Placement-based board rendering |
| `InteractionOverlay.vue` | 101 | Live feedback for normal interaction mode |

## Structure And Logic

The biggest frontend change is that calibration is not a side panel or separate page. It is integrated into the existing manager flow as a mutually exclusive mode. `ModuleManager.vue` now owns two explicit interaction states:

- normal control mode with focus, shop and ArrangeMode
- calibration mode with its own lifecycle, websocket feedback and review actions

`CalibrationWizard.vue` provides the calibration-specific UI, while `InteractionOverlay.vue` remains dedicated to the normal interaction flow. This separation keeps calibration visuals explicit and prevents the existing overlay from turning into a mixed state machine.

`TemplateWidget.vue` also crossed from passive status display into an actual hardware control surface. It now consumes discovered camera and microphone lists, lets the user bind a specific device per widget instance and triggers the matching runtime start or stop actions through the shared hardware composable.

## Critical Assessment

- The component structure is stronger because calibration got its own dedicated surface.
- `ModuleManager.vue` is still the main orchestration hotspot and now even more clearly the application controller of the frontend.
- The next architectural pressure point is no longer raw rendering complexity but shared state extraction out of `ModuleManager.vue`.
- There are still no automated component tests.

## Intended But Missing Elements

- composables or stores to move calibration and layout orchestration above `ModuleManager.vue`
- automated component or state-machine tests
- a richer settings area with session history and profile management beyond the modal wizard

## Navigation

- Parent: `../frontendArch.md`