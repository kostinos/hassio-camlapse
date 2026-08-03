"""Config flow for Hassio Timelapse integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_CAMERA_ENTITY_ID,
    CONF_INTERVAL_SECONDS,
    CONF_SNAPSHOT_PATH,
    CONF_VIDEO_PATH,
    CONF_OUTPUT_FPS,
    CONF_IMAGE_RETENTION_DAYS,
    CONF_VIDEO_RETENTION_DAYS,
    CONF_VIDEOS_PER_DAY,
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_SNAPSHOT_PATH,
    DEFAULT_VIDEO_PATH,
    DEFAULT_OUTPUT_FPS,
    DEFAULT_IMAGE_RETENTION_DAYS,
    DEFAULT_VIDEO_RETENTION_DAYS,
    DEFAULT_VIDEOS_PER_DAY,
    DEFAULT_OUTPUT_CODEC,
    CONF_OUTPUT_CODEC,
)

_LOGGER = logging.getLogger(__name__)


def _positive_int(*, min_value: int, max_value: int, unit: str | None = None):
    """A bounded integer field rendered as a number box in the UI."""
    return vol.All(
        selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=min_value,
                max=max_value,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement=unit,
            )
        ),
        vol.Coerce(int),
    )


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the shared config/reconfigure schema, prefilled with defaults."""
    return vol.Schema(
        {
            vol.Required(
                CONF_CAMERA_ENTITY_ID,
                default=defaults.get(CONF_CAMERA_ENTITY_ID, vol.UNDEFINED),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="camera")),
            vol.Required(
                CONF_INTERVAL_SECONDS,
                default=defaults.get(CONF_INTERVAL_SECONDS, DEFAULT_INTERVAL_SECONDS),
            ): _positive_int(min_value=1, max_value=3600, unit="s"),
            vol.Required(
                CONF_SNAPSHOT_PATH,
                default=defaults.get(CONF_SNAPSHOT_PATH, DEFAULT_SNAPSHOT_PATH),
            ): cv.string,
            vol.Required(
                CONF_VIDEO_PATH,
                default=defaults.get(CONF_VIDEO_PATH, DEFAULT_VIDEO_PATH),
            ): cv.string,
            vol.Required(
                CONF_OUTPUT_FPS,
                default=defaults.get(CONF_OUTPUT_FPS, DEFAULT_OUTPUT_FPS),
            ): _positive_int(min_value=1, max_value=60, unit="fps"),
            vol.Required(
                CONF_IMAGE_RETENTION_DAYS,
                default=defaults.get(CONF_IMAGE_RETENTION_DAYS, DEFAULT_IMAGE_RETENTION_DAYS),
            ): _positive_int(min_value=1, max_value=3650, unit="d"),
            vol.Required(
                CONF_VIDEO_RETENTION_DAYS,
                default=defaults.get(CONF_VIDEO_RETENTION_DAYS, DEFAULT_VIDEO_RETENTION_DAYS),
            ): _positive_int(min_value=1, max_value=3650, unit="d"),
            vol.Required(
                CONF_VIDEOS_PER_DAY,
                default=defaults.get(CONF_VIDEOS_PER_DAY, DEFAULT_VIDEOS_PER_DAY),
            ): _positive_int(min_value=1, max_value=24),
            vol.Required(
                CONF_OUTPUT_CODEC,
                default=defaults.get(CONF_OUTPUT_CODEC, DEFAULT_OUTPUT_CODEC),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["libx264", "libx265"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="output_codec",
                )
            ),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hassio Timelapse."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CAMERA_ENTITY_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_CAMERA_ENTITY_ID], data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema({}), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reconfiguration."""
        errors: dict[str, str] = {}

        if not (config_entry := self.hass.config_entries.async_get_entry(self.context["entry_id"])):
            return self.async_abort(reason="existing_entry_not_found")

        if user_input is not None:
            return self.async_update_reload_and_abort(config_entry, data={**config_entry.data, **user_input})

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(dict(config_entry.data)),
            errors=errors,
        )
