# Changelog

## 0.2.0 — 2026-09-28

- Add a per-camera recording switch for manual control and Home Assistant automations.
- Restore on/off state across restarts and reconfiguration; retain the previous
  always-on default for newly created or upgraded entries.
- Make start/stop idempotent and skip queued snapshot callbacks after stopping.
- Stop timers when the control entity is removed and preserve managers on failed unloads.
- Continue backlog processing and retention cleanup while snapshots are paused.
- Add recording lifecycle tests and automation examples.

Implements the request described in [upstream issue #3](https://github.com/tolwi/hassio-camlapse/issues/3).

## 0.1.1 — 2026-09-28

First independently maintained release from kostinos, based on tolwi's v0.1.0.

- Validate whole-number numeric settings in the UI and on entry setup; reject zero,
  negative, fractional, non-finite and out-of-range values.
- Prevent duplicate cameras on creation and reconfiguration, including legacy entries
  without a unique ID. Update the camera identity and title when reconfiguring.
- Keep configuration keys, integration domain and recording directories compatible.
- Add automated regression tests and CI checks for the fork.
- Document installation, migration, supported baseline and the new support location.

Existing invalid configurations need reconfiguration. Existing duplicates are not
removed automatically. Recording with a real camera/FFmpeg is not part of automated tests.

## 0.1.0 — 2025-12-29

Original release by tolwi.
