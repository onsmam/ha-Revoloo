"""Switch platform for the Revoloo integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_FEEDER, DEVICE_TYPE_LITTER_BOX, DEVICE_TYPE_WATER_DISPENSER
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo switches from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator
    client = coordinator.client

    entities: list[SwitchEntity] = []
    for user_device_id, device in coordinator.data.devices.items():
        if device.device_type == DEVICE_TYPE_WATER_DISPENSER:
            entities.append(RevolooUvcSwitch(coordinator, user_device_id))
            entities.append(
                RevolooLedSwitch(coordinator, user_device_id, client.water_dispenser_set_led)
            )
        elif device.device_type == DEVICE_TYPE_LITTER_BOX:
            entities.append(RevolooKeyLockSwitch(coordinator, user_device_id))
        elif device.device_type == DEVICE_TYPE_FEEDER:
            entities.append(
                RevolooLedSwitch(coordinator, user_device_id, client.feeder_set_led)
            )
    async_add_entities(entities)


class RevolooUvcSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables the water dispenser's UVC sterilization lamp."""

    _attr_translation_key = "uvc_switch"

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_uvc_switch"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("uvc_switch"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.water_dispenser_set_uvc(
            self._user_device_id, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.water_dispenser_set_uvc(
            self._user_device_id, False
        )
        await self.coordinator.async_request_refresh()


class RevolooKeyLockSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables the litter box's button lock."""

    _attr_translation_key = "key_lock"

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_key_lock"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("switch_key"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.litter_box_set_key(self._user_device_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.litter_box_set_key(self._user_device_id, False)
        await self.coordinator.async_request_refresh()


class RevolooLedSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables a device's LED.

    The set_led calls also carry the do-not-disturb schedule, so the current
    values are passed straight through to avoid clobbering them.
    """

    _attr_translation_key = "led"

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        set_led_fn: Callable[[int, bool, str, str], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self._set_led_fn = set_led_fn
        self._attr_unique_id = f"{user_device_id}_led"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("led"))

    async def _async_set_led(self, led: bool) -> None:
        await self._set_led_fn(
            self._user_device_id,
            led,
            self.device.info.get("dnd_begin_time") or "",
            self.device.info.get("dnd_end_time") or "",
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_led(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_led(False)
