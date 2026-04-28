# Repository Module Architecture Analysis

## Scope

- Snapshot basis: 3 files and 782 lines in `Backend/src/repositories`
- Real repository modules: `config.py` and `weather.py`

## Structure And Logic

The repository layer is broader than before because `ConfigRepository` now persists not only layout, system, gesture, voice and input-action config, but also calibration sessions, saved profiles and deterministic apply or rollback snapshots. The important architectural decision is unchanged: a single SQLite-backed `app_config` keyspace stores structured JSON payloads behind stable domain keys.

This keeps the calibration feature aligned with existing persistence instead of introducing a second storage concept. The tradeoff is that `config.py` has become a genuine multi-domain repository and is no longer just a small config helper.

## Critical Assessment

- Reusing `app_config` for calibration was a good fit for the current stage.
- `ConfigRepository` now clearly owns profile and session persistence concerns for input behavior.
- The repository layer remains valuable, but `config.py` is now large enough that key naming and schema evolution need more discipline.
- `WeatherRepository` is still independent and unchanged in architectural role.

## Intended But Missing Elements

- repository-level listing and retention policies for older calibration sessions if history becomes a user-facing feature
- clearer migration rules for long-lived stored calibration payloads
- broader repository coverage for calendar, smart-home or hardware state domains

## Navigation

- Parent: `../backendArch.md`