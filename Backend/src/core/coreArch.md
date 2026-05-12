# Core Module Architecture Analysis

## Scope

- Snapshot basis: 4 files and 215 lines in `Backend/src/core`
- Files: `config.py`, `database.py`, `logging.py`, `realtime.py`

## Structure And Logic

`core/` remains the infrastructure spine of the backend. The new calibration flow increased the importance of two existing primitives without introducing a new infrastructure package:

- `database.py` still bootstraps and serves SQLite connections, now also for calibration sessions, profiles and rollback snapshots.
- `realtime.py` now carries raw modality-specific input events, modality-generic `RawInputDetected`, semantic UI-action events and calibration lifecycle events such as session start, target arm, sample accepted, analysis ready and profile applied.

The backend startup path in `main.py` now initializes the calibration service in the same lifecycle phase that already bound the realtime loop and bootstrapped persistence.

## Critical Assessment

- The module stays small and high leverage.
- Calibration reused existing infrastructure instead of adding a parallel event or persistence mechanism. That is the right tradeoff for the current project size.
- `realtime.py` is now more central because it bridges user-facing interaction, multimodal raw-input diagnostics and operator-facing calibration feedback.
- The operational gaps remain the same: no backpressure strategy for slow websocket consumers, no structured health surface and no real migration layer.

## Intended But Missing Elements

- migration support beyond startup-time schema creation
- health and metrics around websocket throughput and database access
- stronger operational logging and correlation ids
- clearer grouping of configuration defaults as more domains arrive

## Navigation

- Parent: `../backendArch.md`