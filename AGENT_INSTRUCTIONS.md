# Agent Instructions for Hassio Timelapse Project

## Project Overview

This is a Home Assistant custom component (`hassio_camlapse`) that acts as a timelapse generator for cameras.

- **Domain**: `hassio_camlapse`
- **Output**: Generates hourly and daily timelapse videos from camera snapshots.

## Architecture

The project follows a service-oriented architecture layout within the component:

### Core Files

- `timelapse.py`: **Coordinator**. Manages simple state and orchestrates calls to services. Does NOT contain business logic.
- `config_flow.py`: Handles HA configuration flow.
- `const.py`: Constants and default configuration values.
- `translations/`: Internationalization and configuration labels.

### Services (`custom_components/hassio_camlapse/services/`)

- `snapshot.py`: `SnapshotService`. Handles image capture and file storage.
- `video.py`: `VideoService`. Handles FFmpeg operations, video generation, and merging.
- `cleanup.py`: `CleanupService`. Handles file retention and deletion.

## Development Environment

- **Python**: 3.13 (Managed via `mise`)
- **Dependency Management**: `requirements.txt` / `pyproject.toml`
- **Task Runner**: `mise`

## Coding Standards

1. **Type Hinting**: All code must be strictly typed.
2. **Async/Await**: Home Assistant is async-first.
   - Use `async def` for all component methods.
   - Blocking I/O (file ops) **MUST** be run in the executor: `await hass.async_add_executor_job(func, *args)`.
   - Subprocesses (ffmpeg) **MUST** use `asyncio.create_subprocess_exec`.
3. **Linting**:
   - Run `mise run lint` to check code style.
   - Tools: `ruff` (formatting/linting), `mypy` (static types).

## Configuration Rules

- **No Base Path**: Do not use a generic `base_path`. Explicitly use `snapshot_path` and `video_path`.
- **Defaults**: defined in `const.py`.

## Verification & Testing

**CRITICAL**: This project has a standalone verification script that mocks Home Assistant.

- **Script**: `tests/verify.py`
- **Usage**: `python3 tests/verify.py`
- **Behavior**:
  - Uses real Home Assistant classes; mocks camera input and FFmpeg subprocesses.
  - Verifies folder structure creation.
  - Verifies FFmpeg command generation (does not actual run ffmpeg, mocks subprocess).
  - Verifies logic (gap filling, merging, codec selection).
- **Config tests**: `python -m pytest tests/test_config_flow.py` covers numeric validation, UI schema serialization, legacy entries and camera changes.
- **Rule**: ALWAYS run `tests/verify.py` after modifying logic strings or service interactions.

## Key Files

- `custom_components/hassio_camlapse/timelapse.py`
- `custom_components/hassio_camlapse/services/video.py`
- `tests/verify.py`
