# Changelog

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
