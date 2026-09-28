"""Core logic for Hassio Timelapse."""

import datetime
import logging
from typing import Any, Mapping, Optional

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.helpers.event import async_track_time_interval

from .services import SnapshotService, VideoService, CleanupService
from .const import (
    DEFAULT_SNAPSHOT_PATH,
    DEFAULT_VIDEO_PATH,
    DEFAULT_OUTPUT_FPS,
    DEFAULT_IMAGE_RETENTION_DAYS,
    DEFAULT_VIDEO_RETENTION_DAYS,
    DEFAULT_VIDEOS_PER_DAY,
    DEFAULT_OUTPUT_CODEC,
)

_LOGGER = logging.getLogger(__name__)


class TimelapseManager:
    """Manages snapshots and timelapse generation."""

    def __init__(self, hass: HomeAssistant, config: Mapping[str, Any]):
        self.hass = hass
        self.camera_entity_id = config["camera_entity_id"]
        # Use a safe ID for folders
        self.camera_id = self.camera_entity_id.replace(".", "_")
        self.interval = config["interval_seconds"]

        # Paths and config with defaults
        self.snapshot_path = config.get("snapshot_path", DEFAULT_SNAPSHOT_PATH)
        self.video_path = config.get("video_path", DEFAULT_VIDEO_PATH)
        self.output_fps = config.get("output_fps", DEFAULT_OUTPUT_FPS)
        self.image_retention_days = config.get("image_retention_days", DEFAULT_IMAGE_RETENTION_DAYS)
        self.video_retention_days = config.get("video_retention_days", DEFAULT_VIDEO_RETENTION_DAYS)
        self.videos_per_day = config.get("videos_per_day", DEFAULT_VIDEOS_PER_DAY)
        self.output_codec = config.get("output_codec", DEFAULT_OUTPUT_CODEC)

        self._remove_timer: Optional[CALLBACK_TYPE] = None
        self._timer_generation = 0

        # Initialize Services
        self.snapshot_service = SnapshotService(hass, self.camera_entity_id, self.snapshot_path, self.camera_id)

        self.video_service = VideoService(
            hass,
            self.video_path,
            self.camera_id,
            self.output_fps,
            self.output_codec,
            self.videos_per_day,
            self.snapshot_service,
        )

        self.cleanup_service = CleanupService(
            hass, self.snapshot_service, self.video_service, self.image_retention_days, self.video_retention_days
        )

    @property
    def is_recording(self) -> bool:
        """Return whether a snapshot timer is active."""
        return self._remove_timer is not None

    async def start(self) -> None:
        """Start the periodic snapshot task once, even after repeated service calls."""
        if self.is_recording:
            return
        self._timer_generation += 1
        generation = self._timer_generation

        async def snapshot_tick(now: datetime.datetime) -> None:
            await self._async_take_snapshot_wrapper(now, generation)

        self._remove_timer = async_track_time_interval(
            self.hass,
            snapshot_tick,
            datetime.timedelta(seconds=self.interval),
        )
        _LOGGER.info(f"Started timelapse snapshots for {self.camera_entity_id} every {self.interval}s")

    async def stop(self) -> None:
        """Stop the periodic snapshot task."""
        if self._remove_timer:
            self._remove_timer()
            self._remove_timer = None
            _LOGGER.info("Stopped timelapse snapshots")

    async def _async_take_snapshot_wrapper(self, now: datetime.datetime, generation: int) -> None:
        """Ignore callbacks from a stopped or replaced snapshot timer."""
        if self.is_recording and generation == self._timer_generation:
            await self.async_take_snapshot()

    async def async_take_snapshot(self):
        """Take a snapshot and save it."""
        await self.snapshot_service.async_take_snapshot()

    async def check_and_generate_backlog(self):
        """Check for missing hourly timelapses and generate them."""
        await self.video_service.check_and_generate_backlog(self.video_retention_days)

    async def cleanup_old_files(self):
        """Delete old images and videos."""
        await self.cleanup_service.cleanup_old_files()

    async def async_generate_timelapse(self, date_str: str, hour_str: str):
        """Generate timelapse for a specific date and hour."""
        await self.video_service.async_generate_timelapse(date_str, hour_str)

    async def merge_timelapses(self, date_str: str, hour_str: str):
        """Merge hourly timelapse into daily video if configured."""
        await self.video_service.merge_timelapses(date_str, hour_str)
