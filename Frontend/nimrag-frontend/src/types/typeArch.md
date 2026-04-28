# Types Module Architecture Analysis

## Scope

- Snapshot basis: 6 files and 324 lines in `src/types`
- Files: `config.ts`, `hardware.ts`, `interactions.ts`, `calibration.ts`, `weather.ts`, `widgets.ts`

## Structure And Logic

The types layer is still the handwritten contract mirror of the backend, but it now also mirrors a full calibration lifecycle. `calibration.ts` adds typed definitions, session progress, analysis summaries, recommendation contracts and realtime calibration events. This gives the frontend a typed base for the new wizard without introducing a generated shared-schema package.

Together with `interactions.ts`, the layer now covers both normal input behavior and calibration behavior. That is useful, but it also increases the maintenance burden of manual synchronization with the backend Pydantic models.

## Critical Assessment

- Type coverage is strong relative to the frontend size.
- Adding `calibration.ts` was the right separation because the new contracts are broader than a small extension to `interactions.ts`.
- The biggest architectural risk remains contract drift between Python schemas and TypeScript mirrors.
- The layer still mixes transport types and light UI-facing state types, which is acceptable now but may want clearer separation later.

## Intended But Missing Elements

- generated or shared contracts across backend and frontend
- future voice-calibration type support on top of the same lifecycle model
- clearer separation between raw transport contracts and richer frontend view models if the wizard grows further

## Navigation

- Parent: `../frontendArch.md`