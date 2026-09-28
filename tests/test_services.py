"""Service regression tests with real temporary files and mocked camera/FFmpeg."""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hassio_camlapse.services import SnapshotService, VideoService


@pytest.fixture
def services(hass, tmp_path):
    snapshots = SnapshotService(hass, "camera.garden", str(tmp_path), "camera_garden")
    videos = VideoService(hass, str(tmp_path), "camera_garden", 10, "libx264", 24, snapshots)
    return snapshots, videos


async def test_snapshot_creates_expected_layout(services):
    snapshots, _ = services
    now = datetime(2026, 9, 28, 10, 30, tzinfo=timezone.utc)
    with (
        patch(
            "custom_components.hassio_camlapse.services.snapshot.async_get_image",
            new=AsyncMock(return_value=SimpleNamespace(content=b"jpeg")),
        ),
        patch("custom_components.hassio_camlapse.services.snapshot.dt_util.now", return_value=now),
    ):
        await snapshots.async_take_snapshot()
    path = Path(snapshots.get_snapshot_path("2026-09-28", "10")) / "2026-09-28_10-30-00.jpg"
    assert path.read_bytes() == b"jpeg"


@pytest.mark.parametrize("codec", ["libx264", "libx265"])
async def test_generation_orders_frames_and_passes_codec(services, codec):
    snapshots, videos = services
    videos.output_codec = codec
    folder = Path(snapshots.get_snapshot_path("2026-09-28", "09"))
    folder.mkdir(parents=True)
    for name in ["02.jpg", "01.jpg"]:
        (folder / name).write_bytes(b"jpeg")

    async def ffmpeg(*args, **kwargs):
        assert args[args.index("-c:v") + 1] == codec
        assert args[args.index("-r") + 1] == "10"
        assert (folder / "file_list.txt").read_text() == (
            "file '01.jpg'\nduration 0.1\nfile '02.jpg'\nduration 0.1\nfile '02.jpg'\n"
        )
        Path(args[-1]).write_bytes(b"video")
        return SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b"", b"")))

    with patch("asyncio.create_subprocess_exec", side_effect=ffmpeg) as process:
        await videos.async_generate_timelapse("2026-09-28", "09")
    process.assert_called_once()
    assert (Path(videos.get_video_path()) / "timelapse_2026-09-28_09.mp4").read_bytes() == b"video"
    assert not (folder / "file_list.txt").exists()


async def test_first_daily_merge_moves_video_and_marks_snapshots(services):
    snapshots, videos = services
    videos.videos_per_day = 1
    folder = Path(snapshots.get_snapshot_path("2026-09-28", "09"))
    folder.mkdir(parents=True)
    video_folder = Path(videos.get_video_path())
    video_folder.mkdir(parents=True)
    source = video_folder / "timelapse_2026-09-28_09.mp4"
    source.write_bytes(b"video")
    await videos.merge_timelapses("2026-09-28", "09")
    assert not source.exists()
    assert (video_folder / "timelapse_2026-09-28.mp4").read_bytes() == b"video"
    assert (folder / ".merged").exists()


async def test_backlog_skips_current_hour_and_merged_hours(services):
    snapshots, videos = services
    now = datetime(2026, 9, 28, 10, 30, tzinfo=timezone.utc)
    for hour in ["07", "08", "09", "10"]:
        folder = Path(snapshots.get_snapshot_path("2026-09-28", hour))
        folder.mkdir(parents=True)
        (folder / "frame.jpg").write_bytes(b"jpeg")
    (Path(snapshots.get_snapshot_path("2026-09-28", "08")) / ".merged").touch()
    video_folder = Path(videos.get_video_path())
    video_folder.mkdir(parents=True)
    (video_folder / "timelapse_2026-09-28_07.mp4").write_bytes(b"existing")
    with (
        patch("custom_components.hassio_camlapse.services.video.dt_util.now", return_value=now),
        patch.object(videos, "async_generate_timelapse", new_callable=AsyncMock) as generate,
    ):
        await videos.check_and_generate_backlog(1)
    generate.assert_awaited_once_with("2026-09-28", "09")
