"""The Revoloo (Notty Cat) integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .api import RevolooApiClient
from .const import (
    CONF_HZUID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_TYPE_FEEDER,
    FEEDER_SCHEDULE_ENTITY_PREFIX,
)
from .coordinator import RevolooCoordinator
from .feeding_schedule import async_sync_feeding_schedule

# Local time of day the daily automatic feeding-schedule sync runs at.
_DAILY_SYNC_HOUR = 3

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


@dataclass
class RevolooRuntimeData:
    """Runtime data stored on the config entry."""

    coordinator: RevolooCoordinator


if TYPE_CHECKING:
    RevolooConfigEntry = ConfigEntry[RevolooRuntimeData]
else:
    # ConfigEntry only supports subscripting on recent HA versions; keep the
    # generic parameter type-checker-only so this still imports on older ones.
    RevolooConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: RevolooConfigEntry) -> bool:
    """Set up Revoloo from a config entry."""
    session = async_get_clientsession(hass)
    client = RevolooApiClient(
        session,
        entry.data[CONF_TOKEN],
        entry.data[CONF_HZUID],
        time_zone=hass.config.time_zone,
    )

    scan_interval = timedelta(
        seconds=entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
        )
    )
    coordinator = RevolooCoordinator(hass, entry, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = RevolooRuntimeData(coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    for user_device_id, device in coordinator.data.devices.items():
        if device.device_type != DEVICE_TYPE_FEEDER:
            continue
        schedule_entity_id = entry.options.get(
            f"{FEEDER_SCHEDULE_ENTITY_PREFIX}{user_device_id}"
        )
        if not schedule_entity_id:
            continue

        async def _daily_sync(
            _now, _uid: int = user_device_id, _sid: str = schedule_entity_id
        ) -> None:
            await async_sync_feeding_schedule(hass, client, _uid, _sid)
            await coordinator.async_request_refresh()

        entry.async_on_unload(
            async_track_time_change(
                hass, _daily_sync, hour=_DAILY_SYNC_HOUR, minute=0, second=0
            )
        )

    return True


async def _async_update_listener(hass: HomeAssistant, entry: RevolooConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: RevolooConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
