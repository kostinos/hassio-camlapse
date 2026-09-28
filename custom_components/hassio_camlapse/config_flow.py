"""Config flow for Hassio CamLapse."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_CAMERA_ENTITY_ID,
    CONF_SNAPSHOT_PATH,
    CONF_VIDEO_PATH,
    CONF_OUTPUT_CODEC,
    DEFAULT_SNAPSHOT_PATH,
    DEFAULT_VIDEO_PATH,
    DEFAULT_OUTPUT_CODEC,
)
from .validation import NUMERIC_FIELDS, validate_numeric_config


def _schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Keep selectors directly in the schema so HA can serialize the form."""
    fields: dict[Any, Any] = {
        vol.Required(
            CONF_CAMERA_ENTITY_ID, default=defaults.get(CONF_CAMERA_ENTITY_ID, vol.UNDEFINED)
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="camera")),
        vol.Required(CONF_SNAPSHOT_PATH, default=defaults.get(CONF_SNAPSHOT_PATH, DEFAULT_SNAPSHOT_PATH)): cv.string,
        vol.Required(CONF_VIDEO_PATH, default=defaults.get(CONF_VIDEO_PATH, DEFAULT_VIDEO_PATH)): cv.string,
    }
    for key, (minimum, maximum, default, unit) in NUMERIC_FIELDS.items():
        number_config = selector.NumberSelectorConfig(
            min=minimum, max=maximum, step=1, mode=selector.NumberSelectorMode.BOX
        )
        if unit is not None:
            number_config["unit_of_measurement"] = unit
        fields[vol.Required(key, default=defaults.get(key, default))] = selector.NumberSelector(number_config)
    fields[vol.Required(CONF_OUTPUT_CODEC, default=defaults.get(CONF_OUTPUT_CODEC, DEFAULT_OUTPUT_CODEC))] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["libx264", "libx265"],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="output_codec",
            )
        )
    )
    return vol.Schema(fields)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure one timelapse entry per camera, including legacy entries."""

    VERSION = 1

    def _camera_configured(self, camera: str, *, exclude_entry_id: str | None = None) -> bool:
        return any(
            entry.entry_id != exclude_entry_id
            and (entry.data.get(CONF_CAMERA_ENTITY_ID) == camera or entry.unique_id == camera)
            for entry in self._async_current_entries()
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data = validate_numeric_config(user_input)
            except vol.Invalid as err:
                errors[str(err.path[0])] = "invalid_number"
            else:
                camera = data[CONF_CAMERA_ENTITY_ID]
                if self._camera_configured(camera):
                    return self.async_abort(reason="already_configured")
                await self.async_set_unique_id(camera)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=camera, data=data)

        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Validate changes before updating the camera identity and data together."""
        errors: dict[str, str] = {}
        if not (entry := self.hass.config_entries.async_get_entry(self.context["entry_id"])):
            return self.async_abort(reason="existing_entry_not_found")

        if user_input is not None:
            try:
                data = validate_numeric_config({**entry.data, **user_input})
            except vol.Invalid as err:
                errors[str(err.path[0])] = "invalid_number"
            else:
                camera = data[CONF_CAMERA_ENTITY_ID]
                if self._camera_configured(camera, exclude_entry_id=entry.entry_id):
                    errors[CONF_CAMERA_ENTITY_ID] = "already_configured"
                else:
                    return self.async_update_reload_and_abort(entry, data=data, unique_id=camera, title=camera)

        return self.async_show_form(
            step_id="reconfigure", data_schema=_schema({**entry.data, **(user_input or {})}), errors=errors
        )
