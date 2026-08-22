"""Config flow for the Revoloo integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_TOKEN
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RevolooApiClient, RevolooApiError, RevolooAuthError
from .const import (
    CONF_HZUID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_TYPE_FEEDER,
    DOMAIN,
    FEEDER_SCHEDULE_ENTITY_PREFIX,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str,
        vol.Required(CONF_HZUID): str,
    }
)


async def _validate_and_get_title(hass, token: str, hzuid: str) -> str:
    """Validate credentials against the API and return a config entry title."""
    session = async_get_clientsession(hass)
    client = RevolooApiClient(session, token, hzuid, time_zone=hass.config.time_zone)
    await client.verify_token()
    user_info = await client.user_info()
    data = user_info.get("data", {})
    return data.get("nickname") or data.get("email") or "Revoloo"


class RevolooConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Revoloo."""

    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            hzuid = user_input[CONF_HZUID].strip()
            try:
                title = await _validate_and_get_title(self.hass, token, hzuid)
            except RevolooAuthError:
                errors["base"] = "invalid_auth"
            except RevolooApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(hzuid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=title,
                    data={CONF_TOKEN: token, CONF_HZUID: hzuid},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            hzuid = user_input[CONF_HZUID].strip()
            try:
                await _validate_and_get_title(self.hass, token, hzuid)
            except RevolooAuthError:
                errors["base"] = "invalid_auth"
            except RevolooApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={CONF_TOKEN: token, CONF_HZUID: hzuid},
                )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return RevolooOptionsFlow()


class RevolooOptionsFlow(OptionsFlow):
    """Options for the Revoloo integration (polling interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
        )
        schema_dict: dict = {
            vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL.total_seconds())
            ),
        }

        coordinator = self.config_entry.runtime_data.coordinator
        for user_device_id, device in coordinator.data.devices.items():
            if device.device_type != DEVICE_TYPE_FEEDER:
                continue
            key = f"{FEEDER_SCHEDULE_ENTITY_PREFIX}{user_device_id}"
            current_entity = self.config_entry.options.get(key)
            field = (
                vol.Optional(key, default=current_entity)
                if current_entity
                else vol.Optional(key)
            )
            schema_dict[field] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="schedule")
            )

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema_dict)
        )
