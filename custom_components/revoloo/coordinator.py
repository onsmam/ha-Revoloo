"""Data update coordinator for the Revoloo integration."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RevolooApiClient, RevolooApiError, RevolooAuthError
from .const import DEVICE_ID_TYPE_MAP, DEVICE_TYPE_FEEDER, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Fallback quantity for a feeder's "dispense now" button when the user hasn't
# set a manual portion count yet (there is no device-side setting for this;
# the API takes the quantity as a parameter on every one_key call).
DEFAULT_MANUAL_FEED_QTY = 1


@dataclass
class RevolooDevice:
    """A single Revoloo device: the device list entry merged with get_info."""

    user_device_id: int
    device_type: str
    info: dict = field(default_factory=dict)
    upgrade: dict = field(default_factory=dict)
    plans: list = field(default_factory=list)


@dataclass
class RevolooData:
    """Snapshot of everything the coordinator polls."""

    devices: dict[int, RevolooDevice] = field(default_factory=dict)
    pets: dict[int, dict] = field(default_factory=dict)


class RevolooCoordinator(DataUpdateCoordinator[RevolooData]):
    """Polls the Notty Cat cloud API for all devices and pets on the account."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: RevolooApiClient,
        update_interval,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client
        # Not part of RevolooData: that gets replaced on every poll, this
        # needs to survive across polls (it's restored from HA's entity
        # state storage by the number entity, not fetched from the API).
        self.manual_feed_qty: dict[int, int] = {}

    def get_manual_feed_qty(self, user_device_id: int) -> int:
        return self.manual_feed_qty.get(user_device_id, DEFAULT_MANUAL_FEED_QTY)

    async def _async_update_data(self) -> RevolooData:
        try:
            raw_devices = await self.client.get_user_devices()

            devices: dict[int, RevolooDevice] = {}
            for raw in raw_devices:
                user_device_id = raw["user_device_id"]
                device_type = DEVICE_ID_TYPE_MAP.get(raw.get("device_id"))
                if device_type is None:
                    _LOGGER.debug(
                        "Skipping unsupported device_id %s (user_device_id %s)",
                        raw.get("device_id"),
                        user_device_id,
                    )
                    continue
                devices[user_device_id] = RevolooDevice(
                    user_device_id=user_device_id,
                    device_type=device_type,
                    info=raw,
                )

            async def _fill_device(device: RevolooDevice) -> None:
                if device.device_type == DEVICE_TYPE_FEEDER:
                    info, upgrade, plans = await asyncio.gather(
                        self.client.get_info(
                            device.device_type, device.user_device_id
                        ),
                        self.client.check_upgrade(device.user_device_id),
                        self.client.feeder_get_plans(device.user_device_id),
                    )
                    device.plans = plans
                else:
                    info, upgrade = await asyncio.gather(
                        self.client.get_info(
                            device.device_type, device.user_device_id
                        ),
                        self.client.check_upgrade(device.user_device_id),
                    )
                device.info = {**device.info, **info}
                device.upgrade = upgrade

            pets_list, *_ = await asyncio.gather(
                self.client.pet_list(),
                *(_fill_device(device) for device in devices.values()),
            )

            pets = {pet["pet_id"]: pet for pet in pets_list}
        except RevolooAuthError as err:
            raise ConfigEntryAuthFailed from err
        except RevolooApiError as err:
            raise UpdateFailed(str(err)) from err

        return RevolooData(devices=devices, pets=pets)
