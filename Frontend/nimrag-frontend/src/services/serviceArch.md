# Services Module Architecture Analysis

## Scope

- Snapshot basis: 3 files and 261 lines in `src/services`
- Files: `api.ts`, `apiConfig.ts`, `realtime.ts`

## Structure And Logic

The frontend services layer remains intentionally thin, but it now backs a richer interaction model. `api.ts` has grown from a small config and hardware client into the single typed transport surface for layout, system, hardware and calibration. `realtime.ts` still exposes one shared websocket client, but the event stream now carries both normal interaction events and calibration lifecycle feedback.

This keeps transport concerns centralized and prevents calibration from introducing ad hoc fetch or websocket code inside the manager components.

## Critical Assessment

- The module remains clean and reusable despite the wider API surface.
- The calibration addition validated the decision to keep one shared REST client and one shared websocket client.
- There is still no auth handling, caching layer or domain-level state abstraction above these low-level clients.
- Realtime is now used by both normal interaction flow and calibration flow, which increases the value of a future shared store or composable layer.

## Intended But Missing Elements

- shared state consumers above `api.ts` and `realtime.ts`
- auth-aware request handling if backend auth becomes real
- caching or request deduplication for repeated config and calibration refresh reads
- richer domain wrappers once the frontend grows beyond a single manager flow

## Navigation

- Parent: `../frontendArch.md`