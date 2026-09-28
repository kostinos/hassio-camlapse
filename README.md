# Hassio CamLapse — maintained fork

Maintained by [kostinos](https://github.com/kostinos), based on
[tolwi/hassio-camlapse](https://github.com/tolwi/hassio-camlapse).
Please report bugs in [this repository](https://github.com/kostinos/hassio-camlapse/issues).

[![CI](https://github.com/kostinos/hassio-camlapse/actions/workflows/lint.yaml/badge.svg)](https://github.com/kostinos/hassio-camlapse/actions/workflows/lint.yaml)

A Home Assistant integration that takes camera snapshots at regular intervals and
turns them into hourly or daily timelapse videos.

## Features

- **Start / Stop**: Each camera has a recording switch for manual control and automations; its state survives restarts.
- **Automated Snapshots**: Captures images from any `camera` entity at a configurable interval (default: 60s).
- **Hourly Timelapses**: Automatically compiles snapshots into an MP4 video at the end of every hour.
- **Daily Merging**: Optionally merges hourly videos into a single daily timelapse file to reduce clutter.
- **Gap Filling**: Checks for and generates missing hourly videos from looking back at existing snapshots (e.g., after a restart).
- **Retention Management**: Configurable retention periods for raw snapshots and video files.
- **High Efficiency**: Supports **H.264 (AVC)** and **H.265 (HEVC)** codecs for optimized file sizes.
- **Customizable**: Adjustable frame rates (FPS) and output paths.

## Supported version and maintenance

Tested with **Home Assistant 2025.12.5 / Python 3.13**. CI runs lint, type checks
and regression tests. Tests use mocked camera input and FFmpeg; newer HA versions
and recording on a real camera have not been checked yet.

Version **0.2.0** adds a recording switch for each camera. Numeric validation and
duplicate-camera protection from 0.1.1 remain included. See [CHANGELOG.md](CHANGELOG.md).

## Installation

### Option 1: HACS (Recommended)

1.  Open HACS in Home Assistant.
2.  Go to **Integrations** > **Triple dots** (top right) > **Custom repositories**.
3.  Paste the repository URL: `https://github.com/kostinos/hassio-camlapse` into the **Repository** field.
4.  Select **Integration** as the **Category**.
5.  Click **Add**.
6.  Close the custom repositories dialog.
7.  Search for **Hassio CamLapse (kostinos fork)** and click **Download**.
8.  Restart Home Assistant.

### Option 2: Manual Installation

1.  Download the `custom_components/hassio_camlapse` folder from this repository.
2.  Copy the folder into your Home Assistant's `config/custom_components/` directory.
3.  Restart Home Assistant.

## Switching from the original integration

This fork uses the same domain, `hassio_camlapse`, configuration keys and storage layout.
It replaces the original integration; **do not install both side by side**.

1. Back up Home Assistant configuration and your snapshots/videos.
2. Note the configured camera and storage paths. **Keep the entries under Settings > Devices & Services**;
   deleting those entries is not part of the migration.
3. In HACS, remove the original repository/download, then add
   `https://github.com/kostinos/hassio-camlapse` as a custom **Integration** repository and download this fork.
   Complete the replacement before restarting Home Assistant. For manual installations,
   replace only `config/custom_components/hassio_camlapse` with the folder from this fork.
4. Restart Home Assistant and check the existing CamLapse entries and logs.
5. If an old entry has invalid numeric settings (such as FPS = 0), use **Reconfigure**
   to correct them. Invalid values are reported rather than silently changed.

Existing duplicate entries are not deleted automatically. Keep one entry per camera;
reconfigure or remove extra entries deliberately. Changing the camera does not move or
rename previously recorded files. Old entries without a `unique_id` are included in
duplicate checks; reconfiguring them also saves the camera identity.

## Configuration

**Hassio CamLapse** is configured entirely via the Home Assistant UI.

1.  Go to **Settings** > **Devices & Services**.
2.  Click **Add Integration**.
3.  Search for **Hassio CamLapse**.
4.  Follow the setup wizard.

### Configuration Options

| Option                 | Description                                               | Default            |
| :--------------------- | :-------------------------------------------------------- | :----------------- |
| **Camera Entity**      | The camera entity id to capture snapshots from.           | Required           |
| **Interval**           | Time in seconds between snapshots (1–3600).                        | `60`               |
| **Snapshot Path**      | Base path. Files saved in `<path>/<camera_id>/snapshots`. | `/media/timelapse` |
| **Video Path**         | Base path. Files saved in `<path>/<camera_id>/videos`.    | `/media/timelapse` |
| **Output FPS**         | Frames per second for the output video (1–60).                   | `10`               |
| **Codec**              | Video codec to use (`libx264` or `libx265`).              | `H.264 (AVC)`      |
| **Snapshot Retention** | Number of days to keep raw images (1–3650).                        | `7`                |
| **Video Retention**    | Number of days to keep video files (1–3650).                       | `30`               |
| **Videos Per Day**     | `1` merges daily; `2`–`24` keep hourly videos (not an exact count).      | `1`                |

## Start and stop recording

Each configured camera exposes a **CamLapse recording** switch in Home Assistant.
Find it under **Settings > Devices & Services > Hassio CamLapse > Entities** and
add it to a dashboard, or target it from an automation with `switch.turn_on` /
`switch.turn_off`. Each switch controls only its own camera; it does not turn off
the camera itself.

- **On**: take snapshots at the configured interval. The first snapshot is taken
  after one interval, not immediately.
- **Off**: stop scheduling new snapshots. An already-running snapshot may finish.
- The last on/off state is restored after a restart or reconfiguration. New entries
  and entries upgraded from 0.1.x start **on**, preserving the previous behavior.
  Turn the switch off once if you want recording only on request.
- Previously captured images are still processed by hourly maintenance, and normal
  retention cleanup continues while recording is off. Stopping does not immediately
  finalize a video, delete recordings, or create a separate clip for each session.

Example actions (replace the example entity ID with the switch's actual entity ID):

```yaml
# Start recording from an automation or Developer Tools > Actions.
action: switch.turn_on
target:
  entity_id: switch.camera_garden_camlapse_recording
```

```yaml
# Stop recording.
action: switch.turn_off
target:
  entity_id: switch.camera_garden_camlapse_recording
```

No removal or reinstallation of the integration is needed to pause recording.

## How It Works

1.  **Snapshotting**: The integration triggers `camera.snapshot` for your selected entity at the defined interval. Files are saved in `Snapshot Path/{camera_name}/snapshots/YYYY-MM-DD/HH/`.
2.  **Hourly Generation**: At the start of a new hour, it checks the previous hour's folder. If snapshots exist, it uses `ffmpeg` to compile them into `timelapse_YYYY-MM-DD_HH.mp4`.
3.  **Backlog Check**: Periodically checks for past hours that have snapshots but missing videos and generates them.
4.  **Merging**: If "Videos Per Day" is set to 1, hourly videos are appended to a daily `timelapse_YYYY-MM-DD.mp4` file and the hourly file is deleted.
5.  **Cleanup**: Old snapshots and videos exceeding the retention period are automatically deleted.

## Troubleshooting

- **Videos not generating**: Ensure `ffmpeg` is installed and accessible in your Home Assistant environment (standard in HAOS/Supervised).
- **Permissions**: Ensure the `Snapshot Path` and `Video Path` are writable by Home Assistant.
- **Logs**: Check **Settings** > **System** > **Logs** for entries involved with `hassio_camlapse` for error details.

## Development

```sh
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
ruff check custom_components tests
mypy custom_components
python -m pytest
python tests/verify.py
```

With mise, use `mise run lint` and `mise run test`. Tests mock camera input and
FFmpeg execution; they do not require a physical camera or modify a Home Assistant installation.

## Credits and license

Original integration by [tolwi](https://github.com/tolwi). Fork maintained by
[kostinos](https://github.com/kostinos). Licensed under [Apache License 2.0](LICENSE);
the original license and attribution are retained.
