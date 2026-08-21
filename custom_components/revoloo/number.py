"""Number platform for the Revoloo integration.

Litter box reminder cycles: the same API call both reconfigures the cycle
length and resets the remaining-days countdown to it, so a number entity
(rather than a separate "set" + "reset" pair) matches how the app itself
exposes this.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_LITTER_BOX
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo number entities from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator
    client = coordinator.client

    entities: list[NumberEntity] = []
    for user_device_id, device in coordinator.data.devices.items():
        if device.device_type == DEVICE_TYPE_LITTER_BOX:
            entities.append(
                RevolooReminderCycleNumber(
                    coordinator,
                    user_device_id,
                    key="litter_remind_cycle_days",
                    translation_key="litter_remind_cycle_days",
                    info_key="default_remaining_days",
                    set_fn=client.litter_box_set_litter_remind,
                )
            )
            entities.append(
                RevolooReminderCycleNumber(
                    coordinator,
                    user_device_id,
                    key="garbage_bag_remind_cycle_days",
                    translation_key="garbage_bag_remind_cycle_days",
                    info_key="garbage_bag_cycle_time",
                    set_fn=client.litter_box_set_garbage_bag_remind,
                )
            )
    async_add_entities(entities)


class RevolooReminderCycleNumber(RevolooDeviceEntity, NumberEntity):
    """Sets a reminder's cycle length in days and resets its countdown."""

    _attr_native_min_value = 1
    _attr_native_max_value = 90
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        *,
        key: str,
        translation_key: str,
        info_key: str,
        set_fn: Callable[[int, int], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self._info_key = info_key
        self._set_fn = set_fn
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{user_device_id}_{key}"

    @property
    def native_value(self) -> float | None:
        return self.device.info.get(self._info_key)

    async def async_set_native_value(self, value: float) -> None:
        await self._set_fn(self._user_device_id, int(value))
        await self.coordinator.async_request_refresh()
