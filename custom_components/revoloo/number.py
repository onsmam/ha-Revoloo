"""Number platform for the Revoloo integration.

Litter box reminder cycles: the same API call both reconfigures the cycle
length and resets the remaining-days countdown to it, so a number entity
(rather than a separate "set" + "reset" pair) matches how the app itself
exposes this.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.number import (
    NumberEntity,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_FEEDER, DEVICE_TYPE_LITTER_BOX
from .coordinator import DEFAULT_MANUAL_FEED_QTY, RevolooCoordinator
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
        elif device.device_type == DEVICE_TYPE_FEEDER:
            entities.append(RevolooManualFeedQtyNumber(coordinator, user_device_id))
    async_add_entities(entities)


class RevolooReminderCycleNumber(RevolooDeviceEntity, NumberEntity):
    """Sets a reminder's cycle length in days and resets its countdown."""

    _attr_entity_category = EntityCategory.CONFIG
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


class RevolooManualFeedQtyNumber(RevolooDeviceEntity, RestoreNumber):
    """How many portions the feeder's "dispense now" button gives.

    The device has no persisted setting for this — the one_key API call
    takes a quantity every time it's pressed — so this is a HA-local value,
    restored across restarts, that the dispense button reads at press time.
    """

    _attr_translation_key = "manual_feed_qty"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_manual_feed_qty"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        restored = await self.async_get_last_number_data()
        value = restored.native_value if restored is not None else None
        self._attr_native_value = (
            value if value is not None else DEFAULT_MANUAL_FEED_QTY
        )
        self.coordinator.manual_feed_qty[self._user_device_id] = int(
            self._attr_native_value
        )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.coordinator.manual_feed_qty[self._user_device_id] = int(value)
        self.async_write_ha_state()
