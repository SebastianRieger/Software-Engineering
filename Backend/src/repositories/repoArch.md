# Repository Module Architecture Analysis

## Scope

- Snapshot basis: 3 files and 782 lines in `Backend/src/repositories`
- Real repository modules: `config.py` and `weather.py`

## Structure And Logic

The repository layer is broader than before because `ConfigRepository` now persists not only layout, system, gesture, voice and input-action config, but also calibration sessions, saved profiles, deterministic apply or rollback snapshots and the currently active gesture sequence profile set. The important architectural decision is unchanged: a single SQLite-backed `app_config` keyspace stores structured JSON payloads behind stable domain keys.

This keeps the calibration feature aligned with existing persistence instead of introducing a second storage concept. The tradeoff is that `config.py` has become a genuine multi-domain repository and is no longer just a small config helper. The active gesture sequence profile set is stored separately from named calibration profiles so runtime shadow matching can load the currently applied references without guessing a profile name.

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